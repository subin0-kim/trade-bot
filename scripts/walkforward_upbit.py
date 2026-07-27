"""코인 워크포워드 검증 — 메이저(BTC/ETH) vs 알트 분리.

전 구간에서 최고 전략을 고르는 방식은 선택 편향에 오염된다.
여기서는 IS에서만 전략을 고르고 OOS에서 측정한다 (backtest.walk_forward).

가설 검증: "알트가 구조적으로 불리하고 메이저는 다를 수 있다"
  - 메이저 그룹: BTC, ETH (+선택적으로 XRP, SOL 등 시총 상위)
  - 알트 그룹: 나머지

  uv run python scripts/walkforward_upbit.py --tf 240m
  uv run python scripts/walkforward_upbit.py --tf 240m --majors KRW-BTC,KRW-ETH,KRW-XRP,KRW-SOL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import walk_forward, wf_aggregate
from backtest_upbit import DEFAULT_PRESETS, load_5m, run_one, to_timeframe

CACHE_5M = Path("data/cache/upbit/5m")
DEFAULT_MAJORS = ["KRW-BTC", "KRW-ETH"]

CANDIDATES = DEFAULT_PRESETS + ["turtle_20_10", "vol_breakout_ma", "double_rsi"]


def run_group(label: str, symbols: list[str], tf: str, is_bars: int, oos_bars: int) -> None:
    results = []
    for symbol in symbols:
        bars = to_timeframe(load_5m(symbol), tf)
        if len(bars) < is_bars + oos_bars:
            continue
        r = walk_forward(
            symbol, bars, CANDIDATES,
            run_fn=lambda s, b, p: run_one(s, b, p, tf),
            is_bars=is_bars, oos_bars=oos_bars,
        )
        if r.folds:
            results.append(r)

    agg = wf_aggregate(results)
    print(f"\n━━━ {label} ({len(symbols)}종목 중 {agg.get('symbols', 0)}개 검증) ━━━")
    if not agg:
        print("  데이터 부족 — 폴드 생성 불가")
        return
    print(f"  IS 중앙수익      {agg['is_median']:>8.2f}%   ← 전략 선택에 사용 (편향 있음)")
    print(f"  OOS 중앙수익     {agg['oos_median']:>8.2f}%   ← 정직한 추정치")
    print(f"  과적합 격차      {agg['degradation']:>8.2f}%p  (IS - OOS, 클수록 허상)")
    print(f"  OOS 수익 종목    {agg['oos_positive']}/{agg['symbols']}")
    print(f"  선택 안정성      {agg['pick_stability']:>7.0f}%   (같은 전략이 뽑히는 비율)")
    print(f"  OOS 거래         {agg['oos_trades']:>8,}")
    print(f"  선택 분포        {agg['pick_distribution']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="240m")
    parser.add_argument("--majors", default=",".join(DEFAULT_MAJORS))
    parser.add_argument("--is-bars", type=int, default=1200)
    parser.add_argument("--oos-bars", type=int, default=400)
    args = parser.parse_args()

    majors = [s.strip() for s in args.majors.split(",")]
    all_symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    alts = [s for s in all_symbols if s not in majors]

    print(f"워크포워드 검증 ({args.tf}) — IS {args.is_bars}봉 / OOS {args.oos_bars}봉 롤링")
    print(f"후보 전략 {len(CANDIDATES)}종: {', '.join(CANDIDATES)}")
    print(f"메이저: {', '.join(majors)} | 알트: {len(alts)}종목")

    run_group("메이저", majors, args.tf, args.is_bars, args.oos_bars)
    run_group("알트", alts, args.tf, args.is_bars, args.oos_bars)


if __name__ == "__main__":
    main()
