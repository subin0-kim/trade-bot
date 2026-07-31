"""거래량 필터 강도 스윕 — breakout_momo(240m)의 거래량 조건 민감도.

배경: breakout_momo에는 이미 거래량 확인이 들어 있다 (돌파봉 거래량 ≥ 20봉 평균 × 1.5).
"거래량을 전략에 포함하면?"의 정확한 질문은 → **이 조건의 강도가 최적인가?**
없음(0) / 1.2 / 1.5(현재) / 2.0 / 2.5 / 3.0을 프로덕션 유니버스(시총15 알트)로 비교한다.

판정 기준 (레짐 기준 대전과 동일):
  - 누적수익 최대가 아니라 전/후반 분할 모두 플러스(✓) + 이웃 강도도 준수한지(강건성)
  - 현재값(1.5)이 '깨지기 쉬운 봉우리'인지 '평탄한 고원'인지 확인

  uv run python scripts/volume_filter_sweep.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from bot_coin.main import TOP_MCAP_ALTS
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from strategy_kit import RegimeMappedStrategy, build_preset

RATIOS = [None, 1.2, 1.5, 2.0, 2.5, 3.0]  # None = 거래량 필터 제거


def make_strategy(states, ratio: float | None):
    preset = build_preset("breakout_momo")
    if ratio is None:
        preset.filters = [f for f in preset.filters if not hasattr(f, "min_ratio")]
    else:
        for f in preset.filters:
            if hasattr(f, "min_ratio"):
                f.min_ratio = ratio
                f.name = f"volume({f.period},x{ratio})"
    return RegimeMappedStrategy("ens", states, {"bull": preset, "off": None})


def daily_returns(result) -> dict[date, float]:
    by_day: dict[date, float] = {}
    prev_eq = None
    for ts, eq in result.equity_curve:
        d = ts.date()
        if prev_eq is not None and prev_eq > 0:
            by_day[d] = by_day.get(d, 0.0) + (float(eq) / float(prev_eq) - 1) * 100
        prev_eq = float(eq)
    return by_day


def stats(daily: dict[date, float], ds) -> tuple[float, float]:
    cum, peak, mdd = 1.0, 1.0, 0.0
    for d in ds:
        cum *= 1 + daily[d] / 100
        peak = max(peak, cum)
        mdd = max(mdd, (peak - cum) / peak * 100)
    return (cum - 1) * 100, mdd


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    # 전일 완성 일봉의 플래그를 오늘 적용 — 라이브 봇(main.py asset_regime)과 동일.
    # 당일 플래그를 쓰면 장중 봉이 그날 자정 종가 정보를 미리 보는 미래참조 (+40%p 낙관, 2026-07-31 실측)
    states = {d + timedelta(days=1): ("bull" if f else "off") for d, f in ens.items()}

    raw5 = {s: load_5m(s) for s in TOP_MCAP_ALTS}
    data = {s: to_timeframe(b, "240m") for s, b in raw5.items() if b}
    data = {s: b for s, b in data.items() if len(b) > 600}
    print(f"유니버스: 시총15 중 캐시 보유 {len(data)}종목 | 레짐: BTC 앙상블 2/3\n")

    for ratio in RATIOS:
        strat = make_strategy(states, ratio)
        pbt = PortfolioBacktester(
            strat, max_positions=8, warmup=300, view_window=400,
            fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
            initial_cash=Decimal(50_000_000), quantity_step=Decimal("0.00000001"),
        )
        result = pbt.run(data)
        s = result.summary()
        daily = daily_returns(result)
        days = sorted(daily)
        h = len(days) // 2
        total, mdd = stats(daily, days)
        front, _ = stats(daily, days[:h])
        back, _ = stats(daily, days[h:])
        both = "✓" if front > 0 and back > 0 else "✗"
        label = "없음" if ratio is None else (f"{ratio}배" + (" ★현재" if ratio == 1.5 else ""))
        print(f"거래량 {label:<10} 누적 {total:>+7.1f}% | MDD {mdd:>4.1f} | "
              f"전반 {front:>+6.1f} / 후반 {back:>+6.1f} {both} | "
              f"거래 {s['trades']:>3} | 승률 {s['win_rate']:>4.1f}% | PF {s['profit_factor']}",
              flush=True)


if __name__ == "__main__":
    main()
