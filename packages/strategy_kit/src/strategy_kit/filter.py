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


class MinerviniTrendFilter:
    """Minervini 트렌드 템플릿 — Stage 2 상승 추세 판정 (7개 조건 동시 충족).

    출처: Mark Minervini, 'Trade Like a Stock Market Wizard' (2013).
    원전 8개 조건 중 8번(IBD RS 랭킹 ≥70)은 외부 데이터가 필요해 제외 — 7개만 검증한다.
      1) 종가 > MA150, MA200   2) MA150 > MA200   3) MA200이 최근 1개월 상승
      4) MA50 > MA150, MA200   5) 종가 > MA50
      6) 종가 ≥ 52주 최저 × 1.25   7) 종가 ≥ 52주 최고 × 0.75
    """

    def __init__(self, low_margin: float = 1.25, high_margin: float = 0.75):
        self.name = f"minervini(low×{low_margin},high×{high_margin})"
        self.low_margin = low_margin
        self.high_margin = high_margin

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        candles = view.primary
        xs = closes(candles)
        if len(xs) < 252:
            return False, "52주 데이터 부족"
        ma50, ma150, ma200 = sma(xs, 50), sma(xs, 150), sma(xs, 200)
        if ma200[-1] is None or ma150[-1] is None or ma50[-1] is None:
            return False, "MA200 워밍업 부족"
        if ma200[-22] is None:
            return False, "MA200 추세 판정 데이터 부족"

        close = xs[-1]
        w52 = xs[-252:]
        low52, high52 = min(w52), max(w52)
        checks = [
            (close > ma150[-1] and close > ma200[-1], "종가>MA150,200"),
            (ma150[-1] > ma200[-1], "MA150>MA200"),
            (ma200[-1] > ma200[-22], "MA200 1개월 상승"),
            (ma50[-1] > ma150[-1] and ma50[-1] > ma200[-1], "MA50>MA150,200"),
            (close > ma50[-1], "종가>MA50"),
            (close >= low52 * self.low_margin, f"52주저점 대비 +{(close/low52-1)*100:.0f}%"),
            (close >= high52 * self.high_margin, f"52주고점 대비 {(close/high52-1)*100:.0f}%"),
        ]
        failed = [label for ok, label in checks if not ok]
        if failed:
            return False, f"트렌드템플릿 미충족: {failed[0]}"
        return True, "트렌드템플릿 7조건 충족"


class ClenowMomentumFilter:
    """Clenow 모멘텀 점수(연율 지수회귀 기울기 × R²)가 임계 이상일 때만 허용.

    출처: Andreas Clenow, 'Stocks on the Move' (2015).
    원전은 유니버스 순위 기반 선별이나, 종목별 엔진에 맞춰 절대 임계값으로 근사.
    원전의 보조 조건(100일선 위, 최근 15% 이상 갭 제외)도 포함.
    """

    def __init__(self, period: int = 90, min_score: float = 40.0,
                 ma_period: int = 100, max_gap_pct: float = 15.0):
        self.name = f"clenow({period},≥{min_score})"
        self.period = period
        self.min_score = min_score
        self.ma_period = ma_period
        self.max_gap_pct = max_gap_pct

    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]:
        from indicators import clenow_momentum

        candles = view.primary
        xs = closes(candles)
        scores = clenow_momentum(xs, self.period)
        if not scores or scores[-1] is None:
            return False, f"Clenow({self.period}) 워밍업 부족"
        if scores[-1] < self.min_score:
            return False, f"모멘텀 점수 {scores[-1]:.0f} < {self.min_score}"

        ma = sma(xs, self.ma_period)
        if ma[-1] is None or xs[-1] < ma[-1]:
            return False, f"MA{self.ma_period} 아래 (원전 제외 조건)"

        # 최근 90일 내 15% 초과 갭 제외
        for i in range(max(1, len(candles) - self.period), len(candles)):
            prev_close = float(candles[i - 1].close)
            if prev_close > 0:
                gap = abs(float(candles[i].open) / prev_close - 1) * 100
                if gap > self.max_gap_pct:
                    return False, f"최근 {gap:.0f}% 갭 발생 (원전 제외 조건)"
        return True, f"Clenow 모멘텀 {scores[-1]:.0f} 통과"


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
