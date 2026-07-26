"""필터 모듈 — "진입 신호를 받아들일 시장 조건인가".

모든 필터는 allow(view, event) -> (bool, 사유) 를 구현한다.
멀티타임프레임 필터(HigherTFTrendFilter)도 여기 속한다.
"""

from __future__ import annotations

from indicators import adx, closes, roc, sma, volumes

from .view import EntryEvent, MarketView


class ADXFilter:
    """추세 강도 필터. min_adx 이상(추세장 전용) 또는 max_adx 이하(횡보장 전용)."""

    def __init__(self, period: int = 14, min_adx: float | None = None, max_adx: float | None = None):
        self.name = f"adx({period},min={min_adx},max={max_adx})"
        self.period = period
        self.min_adx = min_adx
        self.max_adx = max_adx

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        a = adx(view.primary, self.period)
        if not a or a[-1] is None:
            return False, "ADX 워밍업 부족"
        val = a[-1]
        if self.min_adx is not None and val < self.min_adx:
            return False, f"ADX {val:.1f} < {self.min_adx} (추세 없음)"
        if self.max_adx is not None and val > self.max_adx:
            return False, f"ADX {val:.1f} > {self.max_adx} (추세장 — 역추세 부적합)"
        return True, f"ADX {val:.1f} 통과"


class HigherTFTrendFilter:
    """멀티타임프레임 방향 필터 — 상위 TF 종가가 MA 위일 때만 매수 허용.

    view.candles[tf]는 '완성봉만' 들어있다는 계약을 전제한다.
    """

    def __init__(self, tf: str = "W", ma_period: int = 20):
        self.name = f"htf_trend({tf},ma{ma_period})"
        self.tf = tf
        self.ma_period = ma_period

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        candles = view.candles.get(self.tf)
        if not candles:
            return False, f"상위TF({self.tf}) 데이터 없음"
        xs = closes(candles)
        ma = sma(xs, self.ma_period)
        if ma[-1] is None:
            return False, f"상위TF({self.tf}) MA{self.ma_period} 워밍업 부족"
        if xs[-1] > ma[-1]:
            return True, f"상위TF({self.tf}) 상승국면 ({xs[-1]:.0f} > MA {ma[-1]:.0f})"
        return False, f"상위TF({self.tf}) 하락국면 ({xs[-1]:.0f} ≤ MA {ma[-1]:.0f})"


class VolumeFilter:
    """유동성/관심도 필터 — 당일 거래량이 평균의 min_ratio 이상."""

    def __init__(self, period: int = 20, min_ratio: float = 1.0):
        self.name = f"volume({period},x{min_ratio})"
        self.period = period
        self.min_ratio = min_ratio

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        vols = volumes(view.primary)
        v_ma = sma(vols, self.period)
        if v_ma[-1] is None:
            return False, "거래량 MA 워밍업 부족"
        ratio = vols[-1] / v_ma[-1] if v_ma[-1] else 0.0
        if ratio >= self.min_ratio:
            return True, f"거래량 {ratio:.1f}배 통과"
        return False, f"거래량 부족 ({ratio:.1f}배 < {self.min_ratio}배)"


class ROCFilter:
    """수익률 모멘텀 필터 — N봉 수익률(%)이 임계 이상일 때만 허용.

    출처: Gary Antonacci 'Dual Momentum'의 절대 모멘텀(absolute momentum)을
    일봉·롱온리로 근사 (원전은 12개월 초과수익 > 0 → 보유).
    """

    def __init__(self, period: int = 126, min_roc: float = 0.0):
        self.name = f"roc({period},≥{min_roc}%)"
        self.period = period
        self.min_roc = min_roc

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        r = roc(closes(view.primary), self.period)
        if not r or r[-1] is None:
            return False, f"ROC({self.period}) 워밍업 부족"
        if r[-1] >= self.min_roc:
            return True, f"모멘텀 {r[-1]:+.1f}% ≥ {self.min_roc}%"
        return False, f"모멘텀 부족 ({r[-1]:+.1f}% < {self.min_roc}%)"


class MACompareFilter:
    """이동평균 배열 필터 — MA(fast) > MA(slow)일 때만 허용 (골든크로스 상태).

    출처: 유튜브 '세력 거래량 보는법' (2fndu2K7Tv0)의 '시간차 돌파'
    (60일선>120일선 + 전고점 돌파 + 거래량) 구성 요소.
    """

    def __init__(self, fast: int = 60, slow: int = 120):
        self.name = f"ma_compare({fast}>{slow})"
        self.fast = fast
        self.slow = slow

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        xs = closes(view.primary)
        f, s = sma(xs, self.fast), sma(xs, self.slow)
        if f[-1] is None or s[-1] is None:
            return False, f"MA{self.fast}/{self.slow} 워밍업 부족"
        if f[-1] > s[-1]:
            return True, f"정배열 MA{self.fast}({f[-1]:.0f}) > MA{self.slow}({s[-1]:.0f})"
        return False, f"역배열 (MA{self.fast} ≤ MA{self.slow})"


class PriceAboveMAFilter:
    """기준 TF 자체의 장기 추세 필터 — 종가 > MA(period)."""

    def __init__(self, period: int = 60):
        self.name = f"above_ma({period})"
        self.period = period

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        xs = closes(view.primary)
        ma = sma(xs, self.period)
        if ma[-1] is None:
            return False, f"MA{self.period} 워밍업 부족"
        if xs[-1] > ma[-1]:
            return True, f"MA{self.period} 위 ({xs[-1]:.0f} > {ma[-1]:.0f})"
        return False, f"MA{self.period} 아래"
