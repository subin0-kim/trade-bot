"""레짐을 4시간(240m)마다 재판단하면? — 판단 주기 실험.

현행: BTC 일봉 앙상블 2/3, 매일 09시 1회 갱신 (챔피언 +238.3%, 전일 플래그 기준).
변형 (둘 다 직전 완성봉 플래그 적용 = 라이브 이식 가능한 형태):
  A. 240m 지표 그대로  — ROC30봉·ST(10,3)·MA10>30을 240m 봉으로 (시계 6배 빨라짐: ROC 5일 등)
  B. 240m 기간 환산    — ROC180봉(=30일)·ST(60,3)·MA60>180 (시계 동일, 갱신만 4시간마다)

판정 기준: 누적이 아니라 분할(전/후반) + 스위치 횟수(깜빡임 비용).
bull_age 필터는 모든 안에서 미적용 (챔피언 백테스트와 동일 조건 비교).

  uv run python scripts/regime_240m_test.py
"""

from __future__ import annotations

import bisect
import sys
from datetime import timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from bot_coin.main import TOP_MCAP_ALTS
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from indicators import closes, roc, sma, supertrend
from strategy_kit import Decision
from volume_filter_sweep import daily_returns, make_strategy, stats


def flags_from_bars(bars, roc_n, st_n, st_mult, ma_f, ma_s):
    xs = closes(bars)
    r = roc(xs, roc_n)
    st, _ = supertrend(bars, st_n, st_mult)
    f, s = sma(xs, ma_f), sma(xs, ma_s)
    out = {}
    for i, b in enumerate(bars):
        votes = sum([
            1 if (r[i] is not None and r[i] > 0) else 0,
            1 if st[i] == 1 else 0,
            1 if (f[i] is not None and s[i] is not None and f[i] > s[i]) else 0,
        ])
        out[b.ts] = votes >= 2
    return out


class TsRegimeMapped:
    """봉 타임스탬프 단위 레짐 시리즈용 RegimeMapped (직전 완성봉 플래그 적용)."""

    def __init__(self, name, series_ts: dict, strategy):
        self.name = name
        self._keys = sorted(series_ts)
        self._series = series_ts
        self._strategy = strategy

    def evaluate(self, view, position, equity):
        # 현재 봉 ts보다 '엄격히 이전'의 마지막 플래그 = 직전 완성봉 판정 (선견 없음)
        idx = bisect.bisect_left(self._keys, view.now) - 1
        bull = self._series[self._keys[idx]] if idx >= 0 else False
        if not bull:
            if position is not None:
                return Decision(action="exit", side=None, quantity=position.quantity,
                                reasons=("[regime:off] 현금 레짐 — 전량 청산",))
            return Decision.hold("[regime:off] 현금 레짐")
        return self._strategy.evaluate(view, position, equity)


def run_portfolio(strategy, data):
    pbt = PortfolioBacktester(
        strategy, max_positions=8, warmup=300, view_window=400,
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
    both = "✓" if a > 0 and b > 0 else "✗"
    return f"누적 {t:>+7.1f}% | MDD {mdd:>4.1f} | 전반 {a:>+6.1f}/후반 {b:>+6.1f} {both} | " \
           f"거래 {s['trades']:>3} | 승률 {s['win_rate']}% | PF {s['profit_factor']}"


def switches(series: dict) -> int:
    vals = [series[k] for k in sorted(series)]
    return sum(1 for x, y in zip(vals, vals[1:]) if x != y)


def main():
    btc5 = load_5m("KRW-BTC")
    btc240 = to_timeframe(btc5, "240m")
    btc_daily = to_daily(btc5)

    raw5 = {s: load_5m(s) for s in TOP_MCAP_ALTS}
    data = {s: to_timeframe(b, "240m") for s, b in raw5.items() if b}
    data = {s: b for s, b in data.items() if len(b) > 600}

    # 현행 (일봉, 전일 플래그) — volume_filter_sweep와 동일 경로
    ens_d = ensemble_flags(btc_daily)
    states = {d + timedelta(days=1): ("bull" if f else "off") for d, f in ens_d.items()}
    print(f"[현행] 일봉 앙상블, 매일 갱신     | 스위치 {switches(ens_d)}회")
    print("  " + run_portfolio(make_strategy(states, 1.5), data), flush=True)

    from strategy_kit import build_preset
    for label, params in (
        ("A. 240m 지표 그대로 (시계 6배 빠름)", (30, 10, 3.0, 10, 30)),
        ("B. 240m 기간 환산 (시계 동일)", (180, 60, 3.0, 60, 180)),
    ):
        flags = flags_from_bars(btc240, *params)
        preset = build_preset("breakout_momo")  # vol 1.5 기본 내장
        strat = TsRegimeMapped(f"ens240_{label[:1]}", flags, preset)
        print(f"[{label}] | 스위치 {switches(flags)}회")
        print("  " + run_portfolio(strat, data), flush=True)


if __name__ == "__main__":
    main()
