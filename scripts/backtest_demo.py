"""전략 프리셋 전체를 백테스트하는 데모.

  uv run python scripts/backtest_demo.py --offline            # 합성 데이터 (API 불필요)
  uv run python scripts/backtest_demo.py --symbol 005930      # KIS 일봉 (기본 3년)
  uv run python scripts/backtest_demo.py --symbol 005930,000660 --years 2
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from decimal import Decimal

from backtest import Backtester
from strategy_kit import PRESETS, build_preset, preset_meta
from trading_core.models import Candle


def fetch_kis_daily(symbol: str, years: int) -> list[Candle]:
    """일봉을 100건 제한에 맞춰 구간 분할 조회."""
    from broker_kis import KISBroker

    broker = KISBroker(env="real")
    end = date.today()
    start = end - timedelta(days=int(years * 365.25))
    candles: list[Candle] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=140), end)  # 거래일 ~100건
        chunk = broker.get_daily_candles(symbol, cursor, window_end)
        candles.extend(chunk)
        cursor = window_end + timedelta(days=1)
    # 중복 제거 + 정렬
    unique = {c.ts: c for c in candles}
    return [unique[ts] for ts in sorted(unique)]


def synthetic_candles(n: int = 800, seed: int = 42) -> list[Candle]:
    """레짐이 섞인 합성 일봉: 상승 → 횡보 → 하락 → 상승."""
    import random
    from datetime import datetime

    rng = random.Random(seed)
    regimes = [(0.0015, 0.015), (0.0, 0.008), (-0.0012, 0.02), (0.001, 0.012)]
    candles = []
    price = 50_000.0
    ts = datetime(2024, 1, 1)
    for i in range(n):
        drift, vol = regimes[(i * len(regimes)) // n]
        o = price
        price = max(price * (1 + rng.gauss(drift, vol)), 1000)
        c = price
        hi = max(o, c) * (1 + abs(rng.gauss(0, vol / 3)))
        lo = min(o, c) * (1 - abs(rng.gauss(0, vol / 3)))
        candles.append(
            Candle(
                ts=ts + timedelta(days=i),
                open=Decimal(str(round(o))), high=Decimal(str(round(hi))),
                low=Decimal(str(round(lo))), close=Decimal(str(round(c))),
                volume=Decimal(rng.randint(100_000, 3_000_000)),
            )
        )
    return candles


def run_all(symbol: str, candles: list[Candle]) -> None:
    print(f"\n### {symbol} — 캔들 {len(candles)}개 "
          f"({candles[0].ts.date()} ~ {candles[-1].ts.date()})\n")
    header = (f"{'전략':<18}{'거래':>5}{'승률%':>7}{'수익%':>8}{'노출%':>7}{'비중%':>7}"
              f"{'PF':>6}{'MDD%':>7}")
    print(header)
    print("-" * len(header))
    bh_line = None
    for name in PRESETS:
        meta = preset_meta(name)
        bt = Backtester(
            build_preset(name),
            primary_tf=meta["primary_tf"],
            higher_tfs=meta["higher_tfs"],
        )
        s = bt.run(symbol, candles).summary()
        bh_line = (s["buy_hold_return_pct"], s["buy_hold_mdd_pct"])
        pf = s["profit_factor"] if s["profit_factor"] is not None else "-"
        open_mark = "*" if s["open_position"] else ""
        print(
            f"{s['strategy']:<18}{s['trades']:>5}{s['win_rate']:>7.1f}"
            f"{s['total_return_pct']:>8.2f}{s['exposure_pct']:>7.1f}{s['avg_weight_pct']:>7.1f}"
            f"{pf!s:>6}{s['max_drawdown_pct']:>7.2f}{open_mark}"
        )
    if bh_line:
        print("-" * len(header))
        print(f"{'[벤치마크] 바이앤홀드':<24}{bh_line[0]:>10.2f}%   (MDD {bh_line[1]:.1f}%)")
    print("\n(노출% = 포지션 보유 기간 비율, 비중% = 보유 시 평균 자산 대비 포지션 크기)")
    print("(* = 미청산 포지션 보유 상태로 종료)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--symbol", default="005930", help="쉼표 구분")
    parser.add_argument("--years", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.offline:
        run_all("SYNTH", synthetic_candles(seed=args.seed))
        return

    for symbol in [s.strip() for s in args.symbol.split(",") if s.strip()]:
        run_all(symbol, fetch_kis_daily(symbol, args.years))


if __name__ == "__main__":
    main()
