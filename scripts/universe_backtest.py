"""유니버스 × 구간별 백테스트.

코스피 대형주 ~37종목(승자·패자 혼합) × 3개 구간(하락/횡보·회복/상승)에서
프리셋 전략을 검증한다. 일봉은 data/cache/에 캐시된다 (재실행 시 API 호출 없음).

  uv run python scripts/universe_backtest.py            # 전체 (첫 실행 시 수집 수분)
  uv run python scripts/universe_backtest.py --refresh  # 캐시 무시 재수집
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from backtest import Backtester
from strategy_kit import PRESETS, build_preset, preset_meta
from trading_core.models import Candle

CACHE_DIR = Path("data/cache/daily")
REPORT_DIR = Path("data/reports")
FETCH_START = date(2021, 1, 1)

# 승자(반도체·방산·조선)와 패자(플랫폼·화장품·유통·게임)를 섞은 유니버스
UNIVERSE: dict[str, str] = {
    "005930": "삼성전자", "000660": "SK하이닉스", "005380": "현대차", "000270": "기아",
    "068270": "셀트리온", "005490": "POSCO홀딩스", "035420": "NAVER", "035720": "카카오",
    "051910": "LG화학", "006400": "삼성SDI", "012330": "현대모비스", "105560": "KB금융",
    "055550": "신한지주", "086790": "하나금융지주", "032830": "삼성생명", "015760": "한국전력",
    "017670": "SK텔레콤", "030200": "KT", "066570": "LG전자", "009150": "삼성전기",
    "010950": "S-Oil", "011170": "롯데케미칼", "090430": "아모레퍼시픽", "051900": "LG생활건강",
    "097950": "CJ제일제당", "139480": "이마트", "004370": "농심", "021240": "코웨이",
    "036570": "엔씨소프트", "251270": "넷마블", "352820": "하이브", "323410": "카카오뱅크",
    "018260": "삼성SDS", "012450": "한화에어로스페이스", "329180": "HD현대중공업",
    "011200": "HMM", "010130": "고려아연",
}

# 구간 정의 (사후 라벨 — 레짐 판별 모듈이 생기면 자동화)
SEGMENTS = [
    ("하락장", date(2021, 8, 1), date(2022, 12, 31)),
    ("횡보·회복", date(2023, 1, 1), date(2024, 12, 31)),
    ("상승장", date(2025, 1, 1), date(2026, 7, 24)),
]

WARMUP = 130


def fetch_daily(symbol: str, refresh: bool = False) -> list[Candle]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{symbol}.jsonl"
    if cache.exists() and not refresh:
        candles = []
        for line in cache.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            candles.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        return candles

    from broker_kis import KISBroker
    broker = KISBroker(env="real")
    end = date.today()
    candles = []
    cursor = FETCH_START
    while cursor <= end:
        window_end = min(cursor + timedelta(days=140), end)
        candles.extend(broker.get_daily_candles(symbol, cursor, window_end))
        cursor = window_end + timedelta(days=1)
    unique = {c.ts: c for c in candles}
    ordered = [unique[ts] for ts in sorted(unique)]
    with cache.open("w", encoding="utf-8") as f:
        for c in ordered:
            f.write(json.dumps({
                "ts": c.ts.isoformat(), "o": str(c.open), "h": str(c.high),
                "l": str(c.low), "c": str(c.close), "v": str(c.volume),
            }) + "\n")
    return ordered


def slice_window(candles: list[Candle], start: date, end: date) -> list[Candle] | None:
    """워밍업 130봉을 앞에 붙인 구간 슬라이스. 데이터 부족 시 None."""
    idx_start = next((i for i, c in enumerate(candles) if c.ts.date() >= start), None)
    if idx_start is None or idx_start < WARMUP:
        return None
    idx_end = max(i for i, c in enumerate(candles) if c.ts.date() <= end)
    if idx_end - idx_start < 60:  # 구간이 너무 짧으면 제외
        return None
    return candles[idx_start - WARMUP : idx_end + 1]


def run_universe(data: dict[str, list[Candle]], presets: list[str] | None = None) -> dict:
    """구간 × 전략 × 종목 전체 실행 → 집계."""
    report: dict = {"segments": {}}
    target_presets = presets or list(PRESETS)

    for seg_name, seg_start, seg_end in SEGMENTS:
        seg_result: dict = {}
        for preset_name in target_presets:
            meta = preset_meta(preset_name)
            rows = []
            for symbol, candles in data.items():
                window = slice_window(candles, seg_start, seg_end)
                if window is None:
                    continue
                bt = Backtester(
                    build_preset(preset_name),
                    primary_tf=meta["primary_tf"],
                    higher_tfs=meta["higher_tfs"],
                    warmup=WARMUP,
                )
                s = bt.run(symbol, window).summary()
                rows.append(s)
            if not rows:
                continue
            rets = [r["total_return_pct"] for r in rows]
            bhs = [r["buy_hold_return_pct"] for r in rows]
            seg_result[preset_name] = {
                "symbols": len(rows),
                "median_return": round(statistics.median(rets), 2),
                "median_bh": round(statistics.median(bhs), 2),
                "beat_bh": sum(1 for r in rows if r["total_return_pct"] > r["buy_hold_return_pct"]),
                "positive": sum(1 for r in rows if r["total_return_pct"] > 0),
                "median_mdd": round(statistics.median(r["max_drawdown_pct"] for r in rows), 2),
                "median_bh_mdd": round(statistics.median(r["buy_hold_mdd_pct"] for r in rows), 2),
                "total_trades": sum(r["trades"] for r in rows),
                "tags": meta["tags"],
            }
        report["segments"][seg_name] = seg_result
    return report


def print_report(report: dict) -> None:
    for seg_name, strategies in report["segments"].items():
        print(f"\n{'='*74}\n### {seg_name}\n{'='*74}")
        header = (f"{'전략':<18}{'종목':>4}{'중앙수익%':>9}{'중앙B&H%':>9}{'B&H승':>6}"
                  f"{'수익종목':>7}{'MDD%':>7}{'B&H MDD%':>9}{'거래':>5}")
        print(header)
        print("-" * 74)
        for name, s in strategies.items():
            print(
                f"{name:<18}{s['symbols']:>4}{s['median_return']:>9.2f}{s['median_bh']:>9.2f}"
                f"{s['beat_bh']:>4}/{s['symbols']:<2}{s['positive']:>5}/{s['symbols']:<2}"
                f"{s['median_mdd']:>6.1f}{s['median_bh_mdd']:>9.1f}{s['total_trades']:>5}"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--presets", default=None, help="쉼표 구분 프리셋 이름 (기본: 전체)")
    args = parser.parse_args()
    target_presets = [p.strip() for p in args.presets.split(",")] if args.presets else None

    print(f"유니버스 {len(UNIVERSE)}종목 일봉 수집 (캐시: {CACHE_DIR})")
    data: dict[str, list[Candle]] = {}
    for symbol, name in UNIVERSE.items():
        try:
            candles = fetch_daily(symbol, refresh=args.refresh)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
                print(f"  {symbol} {name}: {len(candles)}봉 ({candles[0].ts.date()}~{candles[-1].ts.date()})")
            else:
                print(f"  {symbol} {name}: 데이터 부족({len(candles)}봉) — 제외")
        except Exception as e:
            print(f"  {symbol} {name}: 수집 실패 — {e}")

    n_presets = len(target_presets) if target_presets else len(PRESETS)
    print(f"\n{len(data)}종목 × {n_presets}전략 × {len(SEGMENTS)}구간 백테스트 실행...")
    report = run_universe(data, target_presets)
    print_report(report)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_partial" if target_presets else ""
    out = REPORT_DIR / f"universe_backtest{suffix}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n리포트 저장: {out}")


if __name__ == "__main__":
    main()
