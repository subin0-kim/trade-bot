"""청산 모듈 — "언제 나갈 것인가".

모든 청산 모듈은 check(view, position) -> ExitEvent | None 을 구현한다.
CompositeStrategy는 등록된 순서대로 검사해 첫 번째 발동을 채택한다
(손절류를 앞에, 익절/시간청산을 뒤에 두는 관례).
"""

from __future__ import annotations

from decimal import Decimal

from indicators import atr, closes, sma

from .view import ExitEvent, MarketView, OpenPosition


class FixedStopTakeExit:
    """고정 손절/익절 (%). 손절 우선 판정."""

    def __init__(self, stop_pct: float = 3.0, take_pct: float = 6.0):
        self.name = f"stop_take({stop_pct}%,{take_pct}%)"
        self.stop_pct = stop_pct
        self.take_pct = take_pct

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        change = float(
            (view.close - position.entry_price) / position.entry_price * 100
        )
        if change <= -self.stop_pct:
            return ExitEvent(f"손절 {change:.2f}% ≤ -{self.stop_pct}%")
        if change >= self.take_pct:
            return ExitEvent(f"익절 {change:.2f}% ≥ +{self.take_pct}%")
        return None


class ATRTrailingExit:
    """ATR 트레일링 스탑 — 진입 후 최고 종가에서 ATR×mult 하락 시 청산."""

    def __init__(self, period: int = 14, mult: float = 3.0):
        self.name = f"atr_trail({period},x{mult})"
        self.period = period
        self.mult = mult

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        a = atr(view.primary, self.period)
        if not a or a[-1] is None:
            return None
        trail_level = float(position.highest_close) - a[-1] * self.mult
        close = float(view.close)
        if close < trail_level:
            return ExitEvent(
                f"ATR 트레일링: 종가 {close:.0f} < 최고 {float(position.highest_close):.0f} - {self.mult}×ATR({a[-1]:.0f})"
            )
        return None


class TimeStopExit:
    """시간 청산 — 최대 보유 봉 수 초과 시 무조건 청산 (회귀 실패 대비)."""

    def __init__(self, max_bars: int = 20):
        self.name = f"time_stop({max_bars})"
        self.max_bars = max_bars

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        if position.bars_held >= self.max_bars:
            return ExitEvent(f"시간청산: {position.bars_held}봉 ≥ {self.max_bars}봉")
        return None


class MACrossExit:
    """데드크로스 청산 — 추세추종 진입의 짝."""

    def __init__(self, fast: int = 5, slow: int = 20):
        self.name = f"ma_cross_exit({fast},{slow})"
        self.fast = fast
        self.slow = slow

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        xs = closes(view.primary)
        f, s = sma(xs, self.fast), sma(xs, self.slow)
        if len(xs) < self.slow + 2 or None in (f[-2], f[-1], s[-2], s[-1]):
            return None
        if f[-2] >= s[-2] and f[-1] < s[-1]:
            return ExitEvent(f"데드크로스 MA{self.fast} < MA{self.slow}")
        return None


class DonchianExit:
    """돈치안 청산 — 종가가 직전 N봉 최저가 아래로 이탈 (터틀 트레이딩의 청산).

    출처: Richard Dennis 터틀 규칙 (System 1: 20일 돌파 진입 / 10일 저점 청산).
    """

    def __init__(self, lookback: int = 10):
        self.name = f"donchian_exit({lookback})"
        self.lookback = lookback

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        candles = view.primary
        if len(candles) < self.lookback + 1:
            return None
        low_level = min(float(c.low) for c in candles[-self.lookback - 1 : -1])
        close = float(view.close)
        if close < low_level:
            return ExitEvent(f"돈치안 이탈: 종가 {close:.0f} < {self.lookback}봉 저점 {low_level:.0f}")
        return None


class PriceAboveMAExit:
    """종가 > MA(n)이면 청산 — Connors식 평균회귀 이익실현 (되돌림 완료 판정)."""

    def __init__(self, period: int = 5):
        self.name = f"above_ma_exit({period})"
        self.period = period

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        xs = closes(view.primary)
        ma = sma(xs, self.period)
        if ma[-1] is None:
            return None
        if xs[-1] > ma[-1]:
            return ExitEvent(f"MA{self.period} 상회 복귀: {xs[-1]:.0f} > {ma[-1]:.0f}")
        return None


class BBBandExit:
    """종가가 +kσ 밴드 아래로 내려오면 청산 — 더블 볼린저 매수존 이탈 (Kathy Lien)."""

    def __init__(self, period: int = 20, k: float = 1.0):
        self.name = f"bb_band_exit({period},+{k}σ)"
        self.period = period
        self.k = k

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import bollinger

        xs = closes(view.primary)
        _, upper, _ = bollinger(xs, self.period, self.k)
        if upper[-1] is None:
            return None
        if xs[-1] < upper[-1]:
            return ExitEvent(f"매수존 이탈: 종가 {xs[-1]:.0f} < +{self.k}σ({upper[-1]:.0f})")
        return None


class RSIBBExit:
    """RSI가 자신의 볼린저 상단 아래로 데드크로스하면 청산 (RSI-BB 기법의 짝)."""

    def __init__(self, rsi_period: int = 14, bb_period: int = 30, bb_k: float = 2.0):
        self.name = f"rsi_bb_exit({rsi_period},{bb_period})"
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_k = bb_k

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import bollinger, rsi

        r = rsi(closes(view.primary), self.rsi_period)
        valid = [v for v in r if v is not None]
        if len(valid) < self.bb_period + 2:
            return None
        _, upper, _ = bollinger(valid, self.bb_period, self.bb_k)
        if upper[-2] is None or upper[-1] is None:
            return None
        if valid[-2] >= upper[-2] and valid[-1] < upper[-1]:
            return ExitEvent(f"RSI({valid[-1]:.0f})가 RSI-BB 상단 하향 이탈")
        return None


class RSILevelExit:
    """RSI가 기준선을 하향 이탈하면 청산.

    출처: 유튜브 '고수들만 몰래 쓰는 MACD+RSI 돈복사 매매법' (TWO4NeDg6O4) —
    과열권(70) 진입 시 팔지 않고 70 하향 이탈에 매도 / 50선 추세 기준 이탈 매도.
    """

    def __init__(self, rsi_period: int = 14, level: float = 70.0):
        self.name = f"rsi_level_exit({rsi_period},{level})"
        self.rsi_period = rsi_period
        self.level = level

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import rsi

        r = rsi(closes(view.primary), self.rsi_period)
        if len(r) < 2 or r[-2] is None or r[-1] is None:
            return None
        if r[-2] >= self.level > r[-1]:
            return ExitEvent(f"RSI {self.level}선 하향 이탈 ({r[-2]:.0f}→{r[-1]:.0f})")
        return None


class RSIAboveExit:
    """RSI가 목표 수준 이상이면 청산 (과매도 진입의 이익실현 목표)."""

    def __init__(self, rsi_period: int = 14, level: float = 60.0):
        self.name = f"rsi_above_exit({rsi_period},{level})"
        self.rsi_period = rsi_period
        self.level = level

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import rsi

        r = rsi(closes(view.primary), self.rsi_period)
        if not r or r[-1] is None:
            return None
        if r[-1] >= self.level:
            return ExitEvent(f"RSI {r[-1]:.0f} ≥ 목표 {self.level}")
        return None


class IchimokuCloudExit:
    """종가가 구름 하단 아래로 이탈하면 청산 (구름 지지 붕괴 = 추세 훼손)."""

    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou: int = 52):
        self.name = f"ichimoku_exit({tenkan},{kijun},{senkou})"
        self.tenkan, self.kijun, self.senkou = tenkan, kijun, senkou

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import ichimoku

        candles = view.primary
        _, _, span_a, span_b = ichimoku(candles, self.tenkan, self.kijun, self.senkou)
        if span_a[-1] is None or span_b[-1] is None:
            return None
        cloud_bottom = min(span_a[-1], span_b[-1])
        close = float(view.close)
        if close < cloud_bottom:
            return ExitEvent(f"구름 하단 이탈: 종가 {close:.0f} < {cloud_bottom:.0f}")
        return None


class NDayHighExit:
    """종가가 N일 최고치이면 청산 (Connors 'Double Seven'의 청산)."""

    def __init__(self, lookback: int = 7):
        self.name = f"n_day_high_exit({lookback})"
        self.lookback = lookback

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        xs = closes(view.primary)
        if len(xs) < self.lookback:
            return None
        if xs[-1] >= max(xs[-self.lookback :]):
            return ExitEvent(f"{self.lookback}일 최고 종가 {xs[-1]:.0f}")
        return None


class IBSExit:
    """IBS가 임계 초과이면 청산 — 고가 부근 마감 = 단기 과열."""

    def __init__(self, threshold: float = 0.8):
        self.name = f"ibs_above_exit({threshold})"
        self.threshold = threshold

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        from indicators import ibs

        vals = ibs(view.primary)
        if not vals:
            return None
        if vals[-1] > self.threshold:
            return ExitEvent(f"IBS {vals[-1]:.2f} > {self.threshold} (고가권 마감)")
        return None


class BollingerMidExit:
    """볼린저 중심선 복귀 청산 — 평균회귀 진입의 짝 (목표 = 평균)."""

    def __init__(self, period: int = 20):
        self.name = f"bb_mid_exit({period})"
        self.period = period

    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None:
        xs = closes(view.primary)
        mid = sma(xs, self.period)
        if mid[-1] is None:
            return None
        if xs[-1] >= mid[-1]:
            return ExitEvent(f"중심선 복귀: {xs[-1]:.0f} ≥ MA{self.period}({mid[-1]:.0f})")
        return None
