"""1분봉 전략 백테스트 — breakout_momo를 1분봉에서 돌리면 살아남는가.

배경: 1차 백테스트(2026-07)에서 60분봉조차 과다거래(4,462건)로 잡음이 수익을 삼켰고
240분봉만 플러스였다. 1분봉은 그 극단 — 왕복 비용 0.20%가 1분봉 평균 진폭보다 크다.
거래량 조건(현재 1.5배)의 강도별로도 비교한다 ("거래량을 더 세게 걸면 1분봉도 되는가").

레짐 게이트는 프로덕션과 동일 (BTC 일봉 앙상블 2/3 초록불에서만 진입).

  uv run python scripts/minute1_backtest.py --days 90 --ratios none,1.5,2.5
  uv run python scripts/minute1_backtest.py --tf 5m           # 1분봉→리샘플 비교용
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester, resample
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m
from bot_coin.main import TOP_MCAP_ALTS
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from strategy_kit import RegimeMappedStrategy, build_preset
from volume_filter_sweep import daily_returns, make_strategy, stats

CACHE_1M = Path("data/cache/upbit/1m")


def load_1m(symbol: str):
    import json
    from datetime import datetime

    from trading_core.models import Candle
    path = CACHE_1M / f"{symbol}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            out.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90, help="최근 N일만 사용 (1분봉은 봉 수가 커서 제한)")
    parser.add_argument("--ratios", default="none,1.5,2.5", help="거래량 필터 강도 (none=제거)")
    parser.add_argument("--tf", default="1m", help="1m 또는 리샘플 대상 (3m/5m/15m)")
    args = parser.parse_args()
    ratios = [None if r.strip() == "none" else float(r) for r in args.ratios.split(",")]

    # 레짐은 프로덕션과 동일하게 BTC 일봉 앙상블. 5분봉 캐시(긴 이력, ~2026-07-27)에
    # 1분봉 캐시(최근 180일, 오늘까지)를 병합해 최근 날짜의 상태 공백을 메운다.
    daily_5m = {c.ts.date(): c for c in to_daily(load_5m("KRW-BTC"))}
    daily_1m = {c.ts.date(): c for c in to_daily(load_1m("KRW-BTC"))}
    merged = {**daily_5m, **daily_1m}  # 겹치는 날은 1분봉 유래가 이김 (동일해야 정상)
    btc_daily = [merged[d] for d in sorted(merged)]
    ens = ensemble_flags(btc_daily)
    states = {d: ("bull" if f else "off") for d, f in ens.items()}

    data = {}
    for s in TOP_MCAP_ALTS:
        bars = load_1m(s)
        if not bars:
            continue
        cutoff = bars[-1].ts - timedelta(days=args.days)
        bars = [b for b in bars if b.ts >= cutoff]
        if args.tf != "1m":
            bars = resample(bars, args.tf)
        if len(bars) > 600:
            data[s] = bars
    n_bars = sum(len(b) for b in data.values())
    span = min(b[0].ts for b in data.values()), max(b[-1].ts for b in data.values())
    print(f"유니버스 {len(data)}종목 | {args.tf} 총 {n_bars:,}봉 | {span[0]:%Y-%m-%d} ~ {span[1]:%Y-%m-%d}\n",
          flush=True)

    for ratio in ratios:
        strat = make_strategy(states, ratio)
        pbt = PortfolioBacktester(
            strat, max_positions=8, warmup=300, view_window=400,
            fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
            initial_cash=Decimal(50_000_000), quantity_step=Decimal("0.00000001"),
        )
        t0 = time.monotonic()
        result = pbt.run(data)
        s = result.summary()
        daily = daily_returns(result)
        days = sorted(daily)
        h = len(days) // 2
        total, mdd = stats(daily, days)
        front, _ = stats(daily, days[:h])
        back, _ = stats(daily, days[h:])
        both = "✓" if front > 0 and back > 0 else "✗"
        label = "없음" if ratio is None else f"{ratio}배"
        print(f"[{args.tf}] 거래량 {label:<6} 누적 {total:>+7.2f}% | MDD {mdd:>4.1f} | "
              f"전반 {front:>+6.2f} / 후반 {back:>+6.2f} {both} | "
              f"거래 {s['trades']:>4} | 승률 {s['win_rate']:>4.1f}% | PF {s['profit_factor']} "
              f"({time.monotonic()-t0:.0f}초)", flush=True)


if __name__ == "__main__":
    main()
