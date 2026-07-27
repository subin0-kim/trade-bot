"""60분봉 백테스트 — 일봉과 동일 기간·동일 종목으로 비교.

분봉 캐시(data/cache/minute/)를 60분봉으로 리샘플해 전략을 돌리고,
같은 기간의 일봉 결과와 나란히 출력한다.

주의: 60분봉은 하루 7봉(09,10,...,15시)이므로 일봉 대비 신호 빈도가 ~7배.
비용(왕복 ~0.31%)이 동일하게 붙으므로 이 비교의 본질은 '빈도 증가가 비용을 이기는가'.

  uv run python scripts/backtest_60m.py
  uv run python scripts/backtest_60m.py --presets connors_rsi2,ma_trend
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import Backtester, resample
from strategy_kit import PRESETS, build_preset, build_strategy, preset_meta
from trading_core.models import Candle
from universe_backtest import UNIVERSE, fetch_daily

MINUTE_DIR = Path("data/cache/minute")

# 60분봉에서 의미 있는 전략들 (일봉 게이트 통과분 + 비교군)
DEFAULT_PRESETS = ["connors_rsi2", "macd_trend_mtf", "turtle_20_10", "ma_trend", "bb_meanrev"]


def load_minutes(symbol: str) -> list[Candle]:
    path = MINUTE_DIR / f"{symbol}.jsonl"
    if not path.exists():
        return []
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            ts = datetime.strptime(d["ts"], "%Y%m%dT%H%M%S")
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
        rows[ts] = Candle(
            ts=ts, open=Decimal(d["o"]), high=Decimal(d["h"]),
            low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
        )
    return [rows[k] for k in sorted(rows)]


def run_60m(symbol: str, minutes: list[Candle], preset: str) -> dict | None:
    bars_60 = resample(minutes, "60m")
    if len(bars_60) < 400:
        return None
    # 60분봉 진입 + 일봉 방향: 상위TF 필터의 tf 파라미터도 함께 W→D로 치환해야 한다
    # (설정만 바꾸고 필터를 그대로 두면 필터가 "W" 데이터를 못 찾아 전량 차단됨)
    config = json.loads(json.dumps(PRESETS[preset]))  # 깊은 복사
    higher: list[str] = []
    for f in config.get("filters", []):
        if f.get("type") == "higher_tf_trend":
            f["tf"] = "D"
            higher = ["D"]
    strategy = build_strategy(preset, config)
    bt = Backtester(
        strategy, primary_tf="60m", higher_tfs=higher,
        warmup=250, view_window=400,  # 250봉 ≈ 36거래일
    )
    return bt.run(symbol, bars_60).summary()


def run_daily_same_period(symbol: str, start: date, end: date, preset: str) -> dict | None:
    """동일 기간 일봉 (워밍업은 기간 이전 데이터에서 확보)."""
    candles = fetch_daily(symbol)
    idx_start = next((i for i, c in enumerate(candles) if c.ts.date() >= start), None)
    if idx_start is None or idx_start < 130:
        return None
    idx_end = max(i for i, c in enumerate(candles) if c.ts.date() <= end)
    window = candles[idx_start - 130 : idx_end + 1]
    strategy = build_preset(preset)
    meta = preset_meta(preset)
    bt = Backtester(strategy, primary_tf="D", higher_tfs=meta["higher_tfs"], warmup=130)
    return bt.run(symbol, window).summary()


def aggregate(rows: list[dict]) -> dict:
    import statistics

    if not rows:
        return {}
    return {
        "symbols": len(rows),
        "median_return": round(statistics.median(r["total_return_pct"] for r in rows), 2),
        "median_bh": round(statistics.median(r["buy_hold_return_pct"] for r in rows), 2),
        "positive": sum(1 for r in rows if r["total_return_pct"] > 0),
        "beat_bh": sum(1 for r in rows if r["total_return_pct"] > r["buy_hold_return_pct"]),
        "total_trades": sum(r["trades"] for r in rows),
        "median_mdd": round(statistics.median(r["max_drawdown_pct"] for r in rows), 2),
        "median_win": round(statistics.median(r["win_rate"] for r in rows), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--presets", default=None)
    args = parser.parse_args()
    presets = ([p.strip() for p in args.presets.split(",")] if args.presets
               else DEFAULT_PRESETS)

    # 분봉이 충분한 종목만
    data = {}
    for symbol in UNIVERSE:
        minutes = load_minutes(symbol)
        if len(minutes) > 60_000:  # ~160거래일 이상
            data[symbol] = minutes
    if not data:
        raise SystemExit("분봉 캐시 부족 — collect_minutes.py 수집 대기 필요")

    sample = next(iter(data.values()))
    period_start, period_end = sample[0].ts.date(), sample[-1].ts.date()
    print(f"60분봉 백테스트: {len(data)}종목, {period_start} ~ {period_end}")
    print(f"(60분봉 {len(resample(sample, '60m')):,}개 ≈ 하루 7봉)\n")

    header = (f"{'전략':<18}{'TF':>5}{'종목':>5}{'중앙수익%':>9}{'중앙B&H%':>9}"
              f"{'수익종목':>7}{'승률%':>7}{'MDD%':>7}{'총거래':>7}")
    print(header)
    print("-" * len(header))

    for preset in presets:
        rows_60, rows_d = [], []
        for symbol, minutes in data.items():
            r60 = run_60m(symbol, minutes, preset)
            if r60:
                rows_60.append(r60)
            rd = run_daily_same_period(symbol, period_start, period_end, preset)
            if rd:
                rows_d.append(rd)
        for label, rows in (("60m", rows_60), ("D", rows_d)):
            a = aggregate(rows)
            if not a:
                continue
            print(f"{preset:<18}{label:>5}{a['symbols']:>5}{a['median_return']:>9.2f}"
                  f"{a['median_bh']:>9.2f}{a['positive']:>5}/{a['symbols']:<2}"
                  f"{a['median_win']:>7.1f}{a['median_mdd']:>7.2f}{a['total_trades']:>7}")
        print()


if __name__ == "__main__":
    main()
