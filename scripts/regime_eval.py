"""레짐 판별기 평가 + 실시간 레짐 기반 스위칭 백테스트.

1) KOSPI 지수 일봉으로 레짐 판별 (look-ahead 없음, 히스테리시스 적용)
2) 사후 라벨(universe_backtest.SEGMENTS)과 일치율 비교
3) 판별 결과로 RegimeMappedStrategy 포트폴리오 백테스트
   → 사후 라벨 상한선(+82.5%)이 실시간 판별에서 얼마나 보존되는지 측정

  uv run python scripts/regime_eval.py
  uv run python scripts/regime_eval.py --confirm-days 3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from regime import Regime, RegimeClassifier
from strategy_kit import RegimeMappedStrategy, build_preset, preset_meta
from trading_core.models import Candle
from universe_backtest import SEGMENTS, UNIVERSE, WARMUP, fetch_daily

INDEX_CACHE = Path("data/cache/index/0001.jsonl")
FETCH_START = date(2021, 1, 1)

# 사후 구간 라벨 → Regime 값
SEGMENT_TO_REGIME = {"하락장": Regime.BEAR, "횡보·회복": Regime.SIDEWAYS, "상승장": Regime.BULL}

# 레짐 → 전략 매핑 기본값 (--bull/--sideways/--bear로 변경 가능)
REGIME_MAPPING = {
    Regime.BEAR.value: None,             # 현금
    Regime.SIDEWAYS.value: "bb_meanrev",
    Regime.BULL.value: "macd_trend_mtf",
}


def fetch_index_daily(refresh: bool = False) -> list[Candle]:
    if INDEX_CACHE.exists() and not refresh:
        candles = []
        for line in INDEX_CACHE.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            candles.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        return candles

    from broker_kis import KISBroker
    broker = KISBroker(env="real")
    candles = []
    cursor = FETCH_START
    end = date.today()
    while cursor <= end:
        # 지수 API는 1콜 최대 50건(구간 내 최신 50개)만 반환 → 65일 윈도로 분할
        window_end = min(cursor + timedelta(days=65), end)
        candles.extend(broker.get_index_daily_candles("0001", cursor, window_end))
        cursor = window_end + timedelta(days=1)
    unique = {c.ts: c for c in candles}
    ordered = [unique[ts] for ts in sorted(unique)]
    INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_CACHE.open("w", encoding="utf-8") as f:
        for c in ordered:
            f.write(json.dumps({
                "ts": c.ts.isoformat(), "o": str(c.open), "h": str(c.high),
                "l": str(c.low), "c": str(c.close), "v": str(c.volume),
            }) + "\n")
    return ordered


def hindsight_label(d: date) -> Regime | None:
    for seg_name, start, end in SEGMENTS:
        if start <= d <= end:
            return SEGMENT_TO_REGIME[seg_name]
    return None


def print_transitions(series: dict[date, Regime]) -> None:
    print("\n레짐 전환 타임라인:")
    prev = None
    for d in sorted(series):
        if series[d] != prev:
            print(f"  {d}  {prev.value if prev else '(시작)'} → {series[d].value}")
            prev = series[d]


def evaluate_agreement(series: dict[date, Regime]) -> None:
    total, agree = 0, 0
    confusion: dict[tuple[str, str], int] = {}
    for d, predicted in series.items():
        label = hindsight_label(d)
        if label is None:
            continue
        total += 1
        if predicted == label:
            agree += 1
        confusion[(label.value, predicted.value)] = confusion.get((label.value, predicted.value), 0) + 1

    print(f"\n사후 라벨 일치율: {agree}/{total} = {agree/total*100:.1f}%")
    print(f"{'사후라벨↓ / 판별→':<16}{'bull':>8}{'bear':>8}{'sideways':>10}")
    for label in ("bear", "sideways", "bull"):
        row = [confusion.get((label, p), 0) for p in ("bull", "bear", "sideways")]
        print(f"{label:<16}{row[0]:>8}{row[1]:>8}{row[2]:>10}")


def run_live_switch(series: dict[date, Regime]) -> None:
    data = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
        except Exception:
            continue

    mapping = {
        regime: (build_preset(preset) if preset else None)
        for regime, preset in REGIME_MAPPING.items()
    }
    higher_tfs: set[str] = set()
    for preset in REGIME_MAPPING.values():
        if preset:
            higher_tfs.update(preset_meta(preset)["higher_tfs"])

    strategy = RegimeMappedStrategy(
        "regime_live_switch",
        {d: r.value for d, r in series.items()},
        mapping,
    )
    pbt = PortfolioBacktester(
        strategy, higher_tfs=sorted(higher_tfs), max_positions=8, warmup=WARMUP,
    )
    s = pbt.run(data).summary()
    print("\n실시간 레짐 스위칭 포트폴리오 백테스트:")
    print(f"  수익 {s['total_return_pct']}% | MDD {s['max_drawdown_pct']}% | "
          f"거래 {s['trades']} | 승률 {s['win_rate']}% | PF {s['profit_factor']} | 노출 {s['exposure_pct']}%")
    print(f"  (비교) 사후 라벨 상한선: +82.5% / MDD 16.2% | 벤치 B&H: {s['bench_return_pct']}% / MDD {s['bench_mdd_pct']}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-days", type=int, default=5)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-backtest", action="store_true")
    parser.add_argument("--bull", default=None, help="상승 레짐 전략 프리셋")
    parser.add_argument("--sideways", default=None, help="횡보 레짐 전략 프리셋")
    parser.add_argument("--bear", default=None, help="하락 레짐 전략 프리셋 (기본 현금)")
    args = parser.parse_args()

    if args.bull:
        REGIME_MAPPING[Regime.BULL.value] = args.bull
    if args.sideways:
        REGIME_MAPPING[Regime.SIDEWAYS.value] = args.sideways
    if args.bear:
        REGIME_MAPPING[Regime.BEAR.value] = args.bear
    print(f"레짐 매핑: {REGIME_MAPPING}")

    index_candles = fetch_index_daily(refresh=args.refresh)
    print(f"KOSPI 지수 일봉 {len(index_candles)}개 "
          f"({index_candles[0].ts.date()} ~ {index_candles[-1].ts.date()})")

    classifier = RegimeClassifier(confirm_days=args.confirm_days)
    series = classifier.classify_series(index_candles)

    print_transitions(series)
    evaluate_agreement(series)
    if not args.no_backtest:
        run_live_switch(series)


if __name__ == "__main__":
    main()
