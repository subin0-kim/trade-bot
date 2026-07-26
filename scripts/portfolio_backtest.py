"""포트폴리오 백테스트 — 전략별로 유니버스 전체를 공유 자본으로 운용.

universe_backtest.py가 만든 캐시(data/cache/daily/)를 사용한다 (API 호출 없음).

  uv run python scripts/portfolio_backtest.py
  uv run python scripts/portfolio_backtest.py --max-positions 5
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from strategy_kit import PRESETS, build_preset, preset_meta
from universe_backtest import UNIVERSE, WARMUP, fetch_daily


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-positions", type=int, default=8)
    args = parser.parse_args()

    data = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
        except Exception:
            continue
    if not data:
        raise SystemExit("캐시 없음 — 먼저 universe_backtest.py를 실행하세요")

    print(f"포트폴리오 백테스트: {len(data)}종목, 동시 보유 최대 {args.max_positions}\n")
    header = (f"{'전략':<18}{'거래':>5}{'승률%':>7}{'수익%':>8}{'벤치%':>8}"
              f"{'MDD%':>7}{'벤치MDD%':>9}{'노출%':>7}{'PF':>6}")
    print(header)
    print("-" * len(header))
    bench = None
    for name in PRESETS:
        meta = preset_meta(name)
        pbt = PortfolioBacktester(
            build_preset(name),
            primary_tf=meta["primary_tf"],
            higher_tfs=meta["higher_tfs"],
            max_positions=args.max_positions,
            warmup=WARMUP,
        )
        s = pbt.run(data).summary()
        bench = (s["bench_return_pct"], s["bench_mdd_pct"])
        pf = s["profit_factor"] if s["profit_factor"] is not None else "-"
        print(
            f"{s['strategy']:<18}{s['trades']:>5}{s['win_rate']:>7.1f}"
            f"{s['total_return_pct']:>8.2f}{s['bench_return_pct']:>8.2f}"
            f"{s['max_drawdown_pct']:>7.2f}{s['bench_mdd_pct']:>9.2f}"
            f"{s['exposure_pct']:>7.1f}{pf!s:>6}"
        )
    if bench:
        print(f"\n벤치마크 = 유니버스 동일가중 바이앤홀드: {bench[0]:.1f}% (MDD {bench[1]:.1f}%)")
    print("노출% = 자산 대비 주식 비중의 기간 평균")


if __name__ == "__main__":
    main()
