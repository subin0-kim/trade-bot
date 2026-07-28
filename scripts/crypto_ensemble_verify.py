"""앙상블 레짐 최종 검증 — 봇 채택 전 마지막 관문.

앙상블 = {ROC30>0, SuperTrend(10,3), MA10>MA30} 2/3 다수결 (BTC 일봉)

검증 항목 (전부 분할 포함):
  A. 앙상블 → 알트 breakout_momo 포트폴리오 (기존 매핑의 레짐만 교체)
  B. 앙상블 → BTC 코어 B&H (에피소드 → 일별 자산곡선화, MDD 포함)
  C. 코어+위성 50:50 결합 (일별 리밸런싱 근사)
  참고. 기존 기준(MA10/30/60 정배열) 매핑 재수록

  uv run python scripts/crypto_ensemble_verify.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from crypto_regime import to_daily
from indicators import closes, roc, sma, supertrend
from strategy_kit import RegimeMappedStrategy, build_preset

CACHE_5M = Path("data/cache/upbit/5m")
COST_ONEWAY = 0.10  # 편도 %


def ensemble_flags(daily) -> dict[date, bool]:
    xs = closes(daily)
    n = len(daily)
    r30 = roc(xs, 30)
    st, _ = supertrend(daily, 10, 3.0)
    ma10, ma30 = sma(xs, 10), sma(xs, 30)
    out = {}
    for i in range(n):
        votes = 0
        votes += 1 if (r30[i] is not None and r30[i] > 0) else 0
        votes += 1 if st[i] == 1 else 0
        votes += 1 if (ma10[i] is not None and ma30[i] is not None and ma10[i] > ma30[i]) else 0
        out[daily[i].ts.date()] = votes >= 2
    return out


def btc_core_curve(daily, flags) -> dict[date, float]:
    """게이트 B&H의 일별 수익률(%). 신호 다음날 시가 체결, 편도 비용 반영."""
    rets: dict[date, float] = {}
    holding = False
    for i in range(1, len(daily)):
        d = daily[i].ts.date()
        o, c = float(daily[i].open), float(daily[i].close)
        prev_c = float(daily[i - 1].close)
        was = flags.get(daily[i - 1].ts.date(), False)
        if not holding and was:
            rets[d] = (c / o - 1) * 100 - COST_ONEWAY  # 시가 매수
            holding = True
        elif holding and not was:
            rets[d] = (o / prev_c - 1) * 100 - COST_ONEWAY  # 시가 매도
            holding = False
        elif holding:
            rets[d] = (c / prev_c - 1) * 100
        else:
            rets[d] = 0.0
    return rets


def curve_stats(label, daily_rets: dict[date, float]):
    days = sorted(daily_rets)
    def stats(ds):
        cum, peak, mdd = 1.0, 1.0, 0.0
        for d in ds:
            cum *= 1 + daily_rets[d] / 100
            peak = max(peak, cum)
            mdd = max(mdd, (peak - cum) / peak * 100)
        return (cum - 1) * 100, mdd
    h = len(days) // 2
    t, mdd = stats(days)
    a, _ = stats(days[:h])
    b, _ = stats(days[h:])
    both = "✓" if a > 0 and b > 0 else "✗"
    print(f"{label:<34} 누적 {t:>+7.1f}% | MDD {mdd:>5.1f} | 전반 {a:>+7.1f} / 후반 {b:>+6.1f} {both}")
    return daily_rets


def portfolio_curve(series_states, data) -> dict[date, float]:
    """RegimeMapped 포트폴리오의 일별 수익률 곡선."""
    mapping = {"bull": build_preset("breakout_momo"), "off": None}
    strat = RegimeMappedStrategy("ens", series_states, mapping)
    pbt = PortfolioBacktester(
        strat, max_positions=8, warmup=300, view_window=400,
        fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
        initial_cash=Decimal(50_000_000), quantity_step=Decimal("0.00000001"),
    )
    result = pbt.run(data)
    s = result.summary()
    print(f"  (포트폴리오 상세: 거래 {s['trades']}, 승률 {s['win_rate']}%, PF {s['profit_factor']}, "
          f"노출 {s['exposure_pct']}%)")
    # equity_curve(240m 간격) → 일별 수익률
    by_day: dict[date, float] = {}
    prev_eq = None
    prev_day = None
    for ts, eq in result.equity_curve:
        d = ts.date()
        if prev_day is not None and d != prev_day and prev_eq:
            by_day[d] = 0.0
        if prev_eq is not None and prev_eq > 0:
            by_day[d] = by_day.get(d, 0.0) + (float(eq) / float(prev_eq) - 1) * 100
        prev_eq, prev_day = float(eq), d
    return by_day


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    print(f"앙상블 초록불: {sum(ens.values())}/{len(ens)}일 ({sum(ens.values())/len(ens)*100:.0f}%)\n")

    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    data = {s: to_timeframe(load_5m(s), "240m") for s in symbols}
    data = {s: b for s, b in data.items() if len(b) > 600}

    # A. 앙상블 → 알트 돌파
    states = {d: ("bull" if f else "off") for d, f in ens.items()}
    print("A. 앙상블 → 알트 breakout_momo 포트폴리오")
    alt_rets = portfolio_curve(states, data)
    curve_stats("A. 앙상블+알트돌파", alt_rets)

    # B. 앙상블 → BTC 코어
    print("\nB. 앙상블 → BTC 코어 B&H")
    btc_rets = btc_core_curve(btc_daily, ens)
    curve_stats("B. 앙상블+BTC코어", btc_rets)

    # C. 50:50 결합
    print("\nC. 코어+위성 50:50 (일별 리밸런싱 근사)")
    common = sorted(set(alt_rets) & set(btc_rets))
    combo = {d: 0.5 * alt_rets[d] + 0.5 * btc_rets[d] for d in common}
    curve_stats("C. BTC코어50 + 알트돌파50", combo)

    # 참고: 기존 기준
    print("\n참고. 기존 기준(MA10/30/60 정배열) → 알트 돌파")
    xs = closes(btc_daily)
    ma10, ma30, ma60 = sma(xs, 10), sma(xs, 30), sma(xs, 60)
    old = {}
    for i, c in enumerate(btc_daily):
        ok = (ma60[i] is not None and xs[i] > ma60[i]
              and ma10[i] is not None and ma30[i] is not None and ma10[i] > ma30[i])
        old[c.ts.date()] = "bull" if ok else "off"
    old_rets = portfolio_curve(old, data)
    curve_stats("참고. 기존기준+알트돌파", old_rets)


if __name__ == "__main__":
    main()
