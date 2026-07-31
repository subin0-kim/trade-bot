"""단타봇 고전 전략 전면 스윕 — 등록 프리셋 전부를 분봉에서 실측.

배경: 급락 반전은 거래 빈도(하루 ~0.6건)가 단타봇 목적과 안 맞아 선반 보관.
등록된 단일TF 프리셋 26종(BB·RSI·추세·돌파·일목·IBS 등)을 시총15+ETH × 2년 ×
5m/15m 분봉에서 레짐 게이트 없이(상시 가동 = 단타봇 전제) 포트폴리오 실측.

선험 경고: 왕복 비용 0.2% vs 분봉 평균 진폭 — 1차 코인 백테스트에서 60분봉도
대부분 죽었다. 목적은 "혹시 살아남는 가족이 있는가"의 전수 확인.

  uv run python scripts/scalper_classic_sweep.py --tf 15m
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m
from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import load_1m
from strategy_kit import build_preset
from strategy_kit.registry import PRESETS, preset_meta
from volume_filter_sweep import daily_returns, stats

UNIVERSE = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="15m")
    parser.add_argument("--presets", default=None, help="쉼표 구분 (기본: 단일TF 전부)")
    args = parser.parse_args()

    from backtest import resample
    data = {}
    for s in UNIVERSE:
        bars = load_1m(s)
        if not bars:
            bars = load_5m(s)
        if args.tf != "1m":
            bars = resample(bars, args.tf)
        if len(bars) > 600:
            data[s] = bars

    names = (args.presets.split(",") if args.presets
             else [n for n in PRESETS if not preset_meta(n)["higher_tfs"]])
    n_bars = sum(len(b) for b in data.values())
    print(f"[{args.tf}] {len(data)}종목, 총 {n_bars:,}봉, 프리셋 {len(names)}개\n", flush=True)

    rows = []
    for name in names:
        t0 = time.monotonic()
        try:
            pbt = PortfolioBacktester(
                build_preset(name), max_positions=10, warmup=300, view_window=400,
                fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
                initial_cash=Decimal(50_000_000), quantity_step=Decimal("0.00000001"),
            )
            r = pbt.run(data)
            s = r.summary()
            daily = daily_returns(r)
            days = sorted(daily)
            h = len(days) // 2
            t, mdd = stats(daily, days)
            a, _ = stats(daily, days[:h])
            b, _ = stats(daily, days[h:])
            both = "V" if a > 0 and b > 0 else "X"
            rows.append((t, f"{name:<22} 누적 {t:+8.1f}% | MDD {mdd:5.1f} | "
                         f"전반 {a:+7.1f}/후반 {b:+7.1f} {both} | 거래 {s['trades']:>5} | "
                         f"PF {s['profit_factor']} ({time.monotonic()-t0:.0f}초)"))
            print(rows[-1][1], flush=True)
        except Exception as e:
            print(f"{name:<22} 실패: {str(e)[:60]}", flush=True)

    print("\n=== 누적 상위 5 ===")
    for _, line in sorted(rows, reverse=True)[:5]:
        print(line)


if __name__ == "__main__":
    main()
