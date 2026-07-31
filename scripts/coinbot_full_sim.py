"""코인봇 전체(코어 50% + 위성 50%) 2년 가상 운용 — "2년 전 1,000만원이면 지금 얼마?"

현 프로덕션 구성 그대로:
  코어 50% = BTC 25% + ETH 25%, 각자 자체 앙상블 2/3 게이트 홀드 (이탈 시 현금)
  위성 50% = 시총15 알트 breakout_momo 240m (거래량 1.5배, 봉 단위 엔진, bull 게이트)
  쇼크 전략은 제외 (이벤트성 소액 — 결과에 소폭 가산 요인)

결합 방식: 슬리브별 독립 복리 후 가중 합산 (리밸런싱 없음 — 봇의 예산 칸막이와 유사).
실제 봇은 진입 금액이 고정 예산 기준이라 복리 가정보다 보수적일 수 있음.

  uv run python scripts/coinbot_full_sim.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from bot_coin.main import TOP_MCAP_ALTS
from crypto_ensemble_verify import btc_core_curve, ensemble_flags
from crypto_regime import to_daily
from volume_filter_sweep import daily_returns, make_strategy

BUDGET = 10_000_000
W_BTC, W_ETH, W_SAT = 0.25, 0.25, 0.50


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    eth_daily = to_daily(load_5m("KRW-ETH"))
    btc_flags = ensemble_flags(btc_daily)
    eth_flags = ensemble_flags(eth_daily)
    core_btc = btc_core_curve(btc_daily, btc_flags)
    core_eth = btc_core_curve(eth_daily, eth_flags)

    states = {d: ("bull" if f else "off") for d, f in btc_flags.items()}
    raw5 = {s: load_5m(s) for s in TOP_MCAP_ALTS}
    data = {s: to_timeframe(b, "240m") for s, b in raw5.items() if b}
    data = {s: b for s, b in data.items() if len(b) > 600}
    pbt = PortfolioBacktester(
        make_strategy(states, 1.5), max_positions=8, warmup=300, view_window=400,
        fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
        initial_cash=Decimal(50_000_000), quantity_step=Decimal("0.00000001"),
    )
    sat = daily_returns(pbt.run(data))

    end = max(core_btc)
    start = end - timedelta(days=730)
    days = sorted(d for d in core_btc if start <= d <= end)

    eq = {"BTC코어": 1.0, "ETH코어": 1.0, "위성": 1.0}
    curves = {k: [] for k in eq}
    total_curve = []
    for d in days:
        eq["BTC코어"] *= 1 + core_btc.get(d, 0.0) / 100
        eq["ETH코어"] *= 1 + core_eth.get(d, 0.0) / 100
        eq["위성"] *= 1 + sat.get(d, 0.0) / 100
        for k in eq:
            curves[k].append(eq[k])
        total_curve.append(W_BTC * eq["BTC코어"] + W_ETH * eq["ETH코어"] + W_SAT * eq["위성"])

    peak, mdd = 0.0, 0.0
    for v in total_curve:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak * 100)

    final = total_curve[-1]
    print(f"기간: {days[0]} ~ {days[-1]} (2년) | 시작 {BUDGET:,}원 | 구성 BTC25/ETH25/위성50\n")
    for k, w in (("BTC코어", W_BTC), ("ETH코어", W_ETH), ("위성", W_SAT)):
        sleeve_final = eq[k]
        print(f"  {k:<7} ({w*100:.0f}%) : x{sleeve_final:.3f} ({(sleeve_final-1)*100:+.1f}%) → "
              f"{BUDGET*w*sleeve_final:>12,.0f}원")
    print(f"\n  합계: {BUDGET*final:,.0f}원 ({(final-1)*100:+.1f}%) | MDD {mdd:.1f}%")

    # 참고: 같은 기간 단순 보유
    for label, daily in (("BTC", btc_daily), ("ETH", eth_daily)):
        closes = {c.ts.date(): float(c.close) for c in daily}
        c0 = next(closes[d] for d in sorted(closes) if d >= days[0])
        c1 = closes[max(d for d in closes if d <= days[-1])]
        print(f"  참고 — {label} 보유: {(c1/c0-1)*100:+.1f}%")


if __name__ == "__main__":
    main()
