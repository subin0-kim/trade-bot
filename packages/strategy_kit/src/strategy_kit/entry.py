"""진입 신호 모듈 — "지금 방향성 신호가 있는가".

모든 진입 모듈은 check(view) -> EntryEvent | None 을 구현한다.
현물 계좌 기준이므로 현재는 매수 신호만 낸다 (숏 확장 대비 side는 명시).
"""

from __future__ import annotations

from indicators import bollinger, closes, macd, rolling_max, rsi, sma, volumes
from trading_core.models import OrderSide

from .view import EntryEvent, MarketView


class BollingerTouchEntry:
    """볼린저 하단 터치 후 반등 진입 (평균회귀).

    직전 봉이 하단 밴드 아래(또는 터치)로 마감 → 이번 봉이 하단 위로 복귀.
    """

    def __init__(self, period: int = 20, k: float = 2.0):
        self.name = f"bb_touch({period},{k})"
        self.period = period
        self.k = k

    def check(self, view: MarketView) -> EntryEvent | None:
        xs = closes(view.primary)
        if len(xs) < self.period + 2:
            return None
        _, _, lower = bollinger(xs, self.period, self.k)
        if lower[-2] is None or lower[-1] is None:
            return None
        if xs[-2] <= lower[-2] and xs[-1] > lower[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"볼린저({self.period},{self.k}) 하단 반등: {xs[-2]:.0f}→{xs[-1]:.0f}",
            )
        return None


class RSIReboundEntry:
    """RSI 과매도 탈출 진입 — RSI가 임계값 아래에서 위로 교차."""

    def __init__(self, period: int = 14, threshold: float = 30.0):
        self.name = f"rsi_rebound({period},{threshold})"
        self.period = period
        self.threshold = threshold

    def check(self, view: MarketView) -> EntryEvent | None:
        r = rsi(closes(view.primary), self.period)
        if len(r) < 2 or r[-2] is None or r[-1] is None:
            return None
        if r[-2] < self.threshold <= r[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"RSI({self.period}) 과매도 탈출: {r[-2]:.1f}→{r[-1]:.1f}",
            )
        return None


class MACrossEntry:
    """이동평균 골든크로스 진입 (추세추종)."""

    def __init__(self, fast: int = 5, slow: int = 20):
        self.name = f"ma_cross({fast},{slow})"
        self.fast = fast
        self.slow = slow

    def check(self, view: MarketView) -> EntryEvent | None:
        xs = closes(view.primary)
        f, s = sma(xs, self.fast), sma(xs, self.slow)
        if len(xs) < self.slow + 2 or None in (f[-2], f[-1], s[-2], s[-1]):
            return None
        if f[-2] <= s[-2] and f[-1] > s[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"골든크로스 MA{self.fast}({f[-1]:.0f}) > MA{self.slow}({s[-1]:.0f})",
            )
        return None


class BreakoutEntry:
    """N봉 신고가 돌파 진입 (모멘텀). 종가가 직전 N봉 고가 최대값을 상회."""

    def __init__(self, lookback: int = 20):
        self.name = f"breakout({lookback})"
        self.lookback = lookback

    def check(self, view: MarketView) -> EntryEvent | None:
        candles = view.primary
        if len(candles) < self.lookback + 1:
            return None
        prev_highs = [float(c.high) for c in candles[-self.lookback - 1 : -1]]
        level = max(prev_highs)
        close = float(candles[-1].close)
        if close > level:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"{self.lookback}봉 신고가 돌파: 종가 {close:.0f} > 전고 {level:.0f}",
            )
        return None


class MACDCrossEntry:
    """MACD선이 시그널선을 상향 돌파."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.name = f"macd_cross({fast},{slow},{signal})"
        self.fast, self.slow, self.signal = fast, slow, signal

    def check(self, view: MarketView) -> EntryEvent | None:
        m, s, _ = macd(closes(view.primary), self.fast, self.slow, self.signal)
        if len(m) < 2 or None in (m[-2], m[-1], s[-2], s[-1]):
            return None
        if m[-2] <= s[-2] and m[-1] > s[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"MACD 상향돌파: {m[-1]:.1f} > signal {s[-1]:.1f}",
            )
        return None


class RSIBelowEntry:
    """RSI 임계값 미만 상태에서 진입 (Connors RSI(2)류 — 크로스가 아니라 상태).

    출처: Larry Connors & Cesar Alvarez, "Short Term Trading Strategies That Work"
    (RSI(2) < 10, 단 200일선 위에서만 — 필터는 별도 모듈로 조합)
    """

    def __init__(self, period: int = 2, threshold: float = 10.0):
        self.name = f"rsi_below({period},{threshold})"
        self.period = period
        self.threshold = threshold

    def check(self, view: MarketView) -> EntryEvent | None:
        r = rsi(closes(view.primary), self.period)
        if not r or r[-1] is None:
            return None
        if r[-1] < self.threshold:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"RSI({self.period})={r[-1]:.1f} < {self.threshold} 과매도",
            )
        return None


class BBZoneEntry:
    """더블 볼린저 밴드 매수존 진입 — 종가가 +kσ 밴드를 상향 돌파.

    출처: Kathy Lien의 Double Bollinger Band (BB(20,±1σ)와 ±2σ의 4개 존).
    가격이 +1σ 위 '매수 우위 존'에 들어오면 추세 시작으로 본다.
    (유튜브 골드핑거 채널 소개 영상에서 규칙 확인)
    """

    def __init__(self, period: int = 20, k: float = 1.0):
        self.name = f"bb_zone({period},+{k}σ)"
        self.period = period
        self.k = k

    def check(self, view: MarketView) -> EntryEvent | None:
        xs = closes(view.primary)
        _, upper, _ = bollinger(xs, self.period, self.k)
        if len(xs) < self.period + 2 or upper[-2] is None or upper[-1] is None:
            return None
        if xs[-2] <= upper[-2] and xs[-1] > upper[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"매수존 진입: 종가 {xs[-1]:.0f} > +{self.k}σ({upper[-1]:.0f})",
            )
        return None


class RSIBBBreakoutEntry:
    """RSI 위에 볼린저 밴드를 씌워, RSI가 자신의 BB 상단을 상향 돌파하면 진입.

    출처: Kathy Lien 계열 RSI-BB 기법 (유튜브 골드핑거 영상: RSI(14) + BB(30,2σ) on RSI,
    50일선 완전 돌파 필터와 조합).
    """

    def __init__(self, rsi_period: int = 14, bb_period: int = 30, bb_k: float = 2.0):
        self.name = f"rsi_bb_breakout({rsi_period},{bb_period})"
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_k = bb_k

    def check(self, view: MarketView) -> EntryEvent | None:
        r = rsi(closes(view.primary), self.rsi_period)
        valid = [v for v in r if v is not None]
        if len(valid) < self.bb_period + 2:
            return None
        _, upper, _ = bollinger(valid, self.bb_period, self.bb_k)
        if upper[-2] is None or upper[-1] is None:
            return None
        if valid[-2] <= upper[-2] and valid[-1] > upper[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"RSI({valid[-1]:.0f})가 RSI-BB 상단({upper[-1]:.0f}) 상향 돌파",
            )
        return None


class RSISignalCrossEntry:
    """RSI가 자신의 시그널선(RSI의 SMA)을 과매도권에서 골든크로스하면 진입.

    출처: 유튜브 'RSI 지표를 활용한 핵심 매매법' (WlUSq19j1Rk) — 원전은 크립토
    15분봉·시그널선 40 이하 조건. 일봉 근사 버전.
    """

    def __init__(self, rsi_period: int = 14, signal_period: int = 14, max_signal: float = 40.0):
        self.name = f"rsi_sig_cross({rsi_period},{signal_period},≤{max_signal})"
        self.rsi_period = rsi_period
        self.signal_period = signal_period
        self.max_signal = max_signal

    def check(self, view: MarketView) -> EntryEvent | None:
        r = rsi(closes(view.primary), self.rsi_period)
        valid = [v for v in r if v is not None]
        if len(valid) < self.signal_period + 2:
            return None
        sig = sma(valid, self.signal_period)
        if sig[-2] is None or sig[-1] is None:
            return None
        if sig[-1] > self.max_signal:
            return None
        if valid[-2] <= sig[-2] and valid[-1] > sig[-1]:
            return EntryEvent(
                OrderSide.BUY, 0.6,
                f"RSI({valid[-1]:.0f})가 시그널({sig[-1]:.0f}≤{self.max_signal})을 골든크로스",
            )
        return None


class IchimokuCloudBounceEntry:
    """일목균형표 양운 지지 반등 진입.

    출처: 유튜브 '일목균형표 단타매매법' (jE54FTenWsw) — 트레이더 마르코의 구름 반응 매매.
    원전 규칙: 양운(선행1>선행2) + 캔들이 구름 터치 + 구름 지지받는 장대 양봉 → 매수.
    '장대'의 정량 기준은 영상 미언급 → 몸통 > 최근 20봉 평균 몸통 × body_mult로 자체 정의.
    (원전은 1시간봉 — 일봉 적용은 근사)
    """

    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou: int = 52, body_mult: float = 1.5):
        self.name = f"ichimoku_bounce({tenkan},{kijun},{senkou})"
        self.tenkan, self.kijun, self.senkou = tenkan, kijun, senkou
        self.body_mult = body_mult

    def check(self, view: MarketView) -> EntryEvent | None:
        from indicators import ichimoku

        candles = view.primary
        if len(candles) < self.senkou + self.kijun + 21:
            return None
        _, _, span_a, span_b = ichimoku(candles, self.tenkan, self.kijun, self.senkou)
        if span_a[-1] is None or span_b[-1] is None:
            return None
        if span_a[-1] <= span_b[-1]:  # 음운이면 매수 금지
            return None

        cloud_top = max(span_a[-1], span_b[-1])
        cloud_bottom = min(span_a[-1], span_b[-1])
        last = candles[-1]
        touched = float(last.low) <= cloud_top and float(last.close) > cloud_bottom
        bullish = last.close > last.open
        bodies = [abs(float(c.close - c.open)) for c in candles[-21:-1]]
        avg_body = sum(bodies) / len(bodies) if bodies else 0.0
        is_long_candle = float(last.close - last.open) > avg_body * self.body_mult

        if touched and bullish and is_long_candle:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"양운 지지 장대양봉: 저가 {float(last.low):.0f} ≤ 구름상단 {cloud_top:.0f}",
            )
        return None


class BoxBreakoutEntry:
    """매집 박스권 돌파 진입 — 저변동 횡보 + 거래량 위축 후 대량 거래 장대양봉 돌파.

    출처: 유튜브 '세력 거래량 보는법' (2fndu2K7Tv0)의 매집 패턴 서술.
    영상은 파라미터 미제시 → 박스 폭/기간/거래량 배수는 자체 정의 (명시적으로 우리 해석임).
    """

    def __init__(
        self,
        box_period: int = 40,
        max_box_range_pct: float = 15.0,
        vol_mult: float = 2.5,
        vol_period: int = 20,
    ):
        self.name = f"box_breakout({box_period},{max_box_range_pct}%,vol×{vol_mult})"
        self.box_period = box_period
        self.max_box_range_pct = max_box_range_pct
        self.vol_mult = vol_mult
        self.vol_period = vol_period

    def check(self, view: MarketView) -> EntryEvent | None:
        candles = view.primary
        if len(candles) < self.box_period + self.vol_period + 2:
            return None
        box = candles[-self.box_period - 1 : -1]
        box_high = max(float(c.high) for c in box)
        box_low = min(float(c.low) for c in box)
        if box_low <= 0:
            return None
        range_pct = (box_high - box_low) / box_low * 100
        if range_pct > self.max_box_range_pct:
            return None  # 횡보(매집) 조건 불충족

        last = candles[-1]
        vols = volumes(candles)
        v_ma = sma(vols, self.vol_period)
        if v_ma[-2] is None or v_ma[-2] <= 0:  # 거래정지 구간 등 거래량 0 방어
            return None
        breakout = float(last.close) > box_high and last.close > last.open
        volume_surge = vols[-1] >= v_ma[-2] * self.vol_mult
        if breakout and volume_surge:
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"박스({range_pct:.1f}%폭) 돌파 장대양봉 + 거래량 {vols[-1]/v_ma[-2]:.1f}배",
            )
        return None


class NDayLowEntry:
    """종가가 N일 최저치이면 진입 (Connors 'Double Seven'의 진입).

    출처: Connors & Alvarez, 'Short Term Trading Strategies That Work' —
    200일선 위 + 7일 최저 종가 매수 / 7일 최고 종가 매도. 200일선 필터는 별도 모듈.
    """

    def __init__(self, lookback: int = 7):
        self.name = f"n_day_low({lookback})"
        self.lookback = lookback

    def check(self, view: MarketView) -> EntryEvent | None:
        xs = closes(view.primary)
        if len(xs) < self.lookback:
            return None
        window = xs[-self.lookback :]
        if xs[-1] <= min(window):
            return EntryEvent(
                OrderSide.BUY, 0.7,
                f"{self.lookback}일 최저 종가 {xs[-1]:.0f}",
            )
        return None


class IBSEntry:
    """IBS(종가의 봉내 위치)가 임계 미만이면 진입 — 저가 부근 마감 = 단기 과매도.

    출처: Internal Bar Strength 평균회귀 (QuantifiedStrategies / Alvarez Quant Trading).
    """

    def __init__(self, threshold: float = 0.2):
        self.name = f"ibs_below({threshold})"
        self.threshold = threshold

    def check(self, view: MarketView) -> EntryEvent | None:
        from indicators import ibs

        vals = ibs(view.primary)
        if not vals:
            return None
        if vals[-1] < self.threshold:
            return EntryEvent(
                OrderSide.BUY, 0.7, f"IBS {vals[-1]:.2f} < {self.threshold} (저가권 마감)"
            )
        return None


class ConsecutiveDownEntry:
    """N일 연속 저점·고점 하락(lower lows & lower highs) 후 진입.

    출처: Connors & Alvarez, 'High Probability ETF Trading' (2009) 3-Day 평균회귀.
    """

    def __init__(self, days: int = 3):
        self.name = f"consecutive_down({days})"
        self.days = days

    def check(self, view: MarketView) -> EntryEvent | None:
        candles = view.primary
        if len(candles) < self.days + 1:
            return None
        for i in range(self.days):
            cur, prev = candles[-1 - i], candles[-2 - i]
            if not (cur.high < prev.high and cur.low < prev.low):
                return None
        return EntryEvent(
            OrderSide.BUY, 0.7, f"{self.days}일 연속 고점·저점 하락 후 진입"
        )


class VolumeSpikeReversalEntry:
    """거래량 급증 + 양봉 반전 진입 — 거래량이 평균의 배수 이상 + 종가>시가."""

    def __init__(self, vol_period: int = 20, vol_mult: float = 2.0):
        self.name = f"vol_spike({vol_period},{vol_mult})"
        self.vol_period = vol_period
        self.vol_mult = vol_mult

    def check(self, view: MarketView) -> EntryEvent | None:
        candles = view.primary
        vols = volumes(candles)
        v_ma = sma(vols, self.vol_period)
        if len(vols) < self.vol_period + 1 or v_ma[-2] is None:
            return None
        last = candles[-1]
        if vols[-1] >= v_ma[-2] * self.vol_mult and last.close > last.open:
            return EntryEvent(
                OrderSide.BUY, 0.6,
                f"거래량 급증 양봉: vol {vols[-1]:.0f} ≥ {self.vol_mult}×MA({v_ma[-2]:.0f})",
            )
        return None
