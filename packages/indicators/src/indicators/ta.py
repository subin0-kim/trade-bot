"""기술적 지표 라이브러리.

설계 규칙:
- 입력은 float 리스트 또는 Candle 리스트, 출력은 입력과 같은 길이의 리스트
  (워밍업 구간은 None) — 인덱스 정렬이 유지되어 백테스트에서 안전하다.
- 금액 연산이 아니라 통계 연산이므로 float 사용 (주문 금액은 Decimal 유지).
- Wilder 평활(RSI/ATR/ADX)은 표준 정의를 따른다.
"""

from __future__ import annotations

from trading_core.models import Candle

Series = list[float | None]


# ---------------------------------------------------------------- 변환 헬퍼
def closes(candles: list[Candle]) -> list[float]:
    return [float(c.close) for c in candles]


def highs(candles: list[Candle]) -> list[float]:
    return [float(c.high) for c in candles]


def lows(candles: list[Candle]) -> list[float]:
    return [float(c.low) for c in candles]


def volumes(candles: list[Candle]) -> list[float]:
    return [float(c.volume) for c in candles]


# ---------------------------------------------------------------- 이동평균
def sma(xs: list[float], period: int) -> Series:
    out: Series = [None] * len(xs)
    if period <= 0 or len(xs) < period:
        return out
    window_sum = sum(xs[:period])
    out[period - 1] = window_sum / period
    for i in range(period, len(xs)):
        window_sum += xs[i] - xs[i - period]
        out[i] = window_sum / period
    return out


def ema(xs: list[float], period: int) -> Series:
    out: Series = [None] * len(xs)
    if period <= 0 or len(xs) < period:
        return out
    alpha = 2 / (period + 1)
    prev = sum(xs[:period]) / period  # SMA로 시드
    out[period - 1] = prev
    for i in range(period, len(xs)):
        prev = xs[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out


def _wilder_smooth(xs: list[float], period: int) -> Series:
    """Wilder 평활 (RSI/ATR/ADX 공통)."""
    out: Series = [None] * len(xs)
    if len(xs) < period:
        return out
    prev = sum(xs[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(xs)):
        prev = (prev * (period - 1) + xs[i]) / period
        out[i] = prev
    return out


# ---------------------------------------------------------------- 모멘텀
def rsi(xs: list[float], period: int = 14) -> Series:
    out: Series = [None] * len(xs)
    if len(xs) < period + 1:
        return out
    gains = [0.0] + [max(xs[i] - xs[i - 1], 0.0) for i in range(1, len(xs))]
    losses = [0.0] + [max(xs[i - 1] - xs[i], 0.0) for i in range(1, len(xs))]
    avg_gain = _wilder_smooth(gains[1:], period)
    avg_loss = _wilder_smooth(losses[1:], period)
    for i in range(len(xs) - 1):
        g, l = avg_gain[i], avg_loss[i]
        if g is None or l is None:
            continue
        idx = i + 1
        out[idx] = 100.0 if l == 0 else 100.0 - 100.0 / (1.0 + g / l)
    return out


def macd(
    xs: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[Series, Series, Series]:
    """(macd선, 시그널선, 히스토그램)"""
    ema_fast = ema(xs, fast)
    ema_slow = ema(xs, slow)
    macd_line: Series = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(ema_fast, ema_slow)
    ]
    # 시그널: macd 유효 구간에 대한 EMA
    valid_start = next((i for i, v in enumerate(macd_line) if v is not None), len(xs))
    valid = [v for v in macd_line if v is not None]
    sig_valid = ema(valid, signal)
    signal_line: Series = [None] * len(xs)
    for j, v in enumerate(sig_valid):
        signal_line[valid_start + j] = v
    hist: Series = [
        (m - s) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]
    return macd_line, signal_line, hist


def roc(xs: list[float], period: int = 10) -> Series:
    out: Series = [None] * len(xs)
    for i in range(period, len(xs)):
        if xs[i - period] != 0:
            out[i] = (xs[i] / xs[i - period] - 1.0) * 100.0
    return out


# ---------------------------------------------------------------- 변동성·밴드
def bollinger(
    xs: list[float], period: int = 20, k: float = 2.0
) -> tuple[Series, Series, Series]:
    """(중심선, 상단, 하단)"""
    mid = sma(xs, period)
    upper: Series = [None] * len(xs)
    lower: Series = [None] * len(xs)
    for i in range(period - 1, len(xs)):
        m = mid[i]
        if m is None:
            continue
        window = xs[i - period + 1 : i + 1]
        var = sum((x - m) ** 2 for x in window) / period
        std = var**0.5
        upper[i] = m + k * std
        lower[i] = m - k * std
    return mid, upper, lower


def _true_ranges(candles: list[Candle]) -> list[float]:
    trs = []
    for i, c in enumerate(candles):
        hi, lo = float(c.high), float(c.low)
        if i == 0:
            trs.append(hi - lo)
        else:
            prev_close = float(candles[i - 1].close)
            trs.append(max(hi - lo, abs(hi - prev_close), abs(lo - prev_close)))
    return trs


def atr(candles: list[Candle], period: int = 14) -> Series:
    return _wilder_smooth(_true_ranges(candles), period)


def adx(candles: list[Candle], period: int = 14) -> Series:
    """평균방향성지수. 25 이상이면 추세 존재로 해석하는 게 관례."""
    n = len(candles)
    out: Series = [None] * n
    if n < period * 2:
        return out

    plus_dm, minus_dm = [0.0], [0.0]
    for i in range(1, n):
        up = float(candles[i].high) - float(candles[i - 1].high)
        down = float(candles[i - 1].low) - float(candles[i].low)
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)

    trs = _true_ranges(candles)
    atr_s = _wilder_smooth(trs[1:], period)
    pdm_s = _wilder_smooth(plus_dm[1:], period)
    mdm_s = _wilder_smooth(minus_dm[1:], period)

    dx: list[float] = []
    dx_start = None
    for i in range(len(atr_s)):
        a, p, m = atr_s[i], pdm_s[i], mdm_s[i]
        if a is None or p is None or m is None or a == 0:
            continue
        if dx_start is None:
            dx_start = i + 1  # candles 인덱스 보정(+1: diff 시리즈)
        pdi = 100.0 * p / a
        mdi = 100.0 * m / a
        denom = pdi + mdi
        dx.append(100.0 * abs(pdi - mdi) / denom if denom else 0.0)

    adx_s = _wilder_smooth(dx, period)
    if dx_start is not None:
        for j, v in enumerate(adx_s):
            if v is not None and dx_start + j < n:
                out[dx_start + j] = v
    return out


# ---------------------------------------------------------------- 스토캐스틱·롤링
def stochastic(
    candles: list[Candle], k_period: int = 14, d_period: int = 3
) -> tuple[Series, Series]:
    """(%K, %D)"""
    n = len(candles)
    k: Series = [None] * n
    for i in range(k_period - 1, n):
        window = candles[i - k_period + 1 : i + 1]
        hi = max(float(c.high) for c in window)
        lo = min(float(c.low) for c in window)
        close = float(candles[i].close)
        k[i] = 50.0 if hi == lo else (close - lo) / (hi - lo) * 100.0
    valid_start = next((i for i, v in enumerate(k) if v is not None), n)
    valid = [v for v in k if v is not None]
    d_valid = sma(valid, d_period)
    d: Series = [None] * n
    for j, v in enumerate(d_valid):
        d[valid_start + j] = v
    return k, d


def ichimoku(
    candles: list[Candle],
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> tuple[Series, Series, Series, Series]:
    """일목균형표: (전환선, 기준선, 선행스팬A, 선행스팬B).

    전환선 = (9봉 최고+최저)/2, 기준선 = (26봉 최고+최저)/2.
    선행스팬은 관례상 26봉 앞에 그리지만, 여기서는 **현재 봉 기준으로 유효한
    구름대 값**(즉 26봉 전 데이터로 계산된 스팬)을 반환한다 — 백테스트에서
    "지금 가격 vs 지금 구름"을 바로 비교할 수 있고 미래참조가 없다.
    """
    n = len(candles)
    his = highs(candles)
    los = lows(candles)

    def midline(period: int) -> Series:
        out: Series = [None] * n
        for i in range(period - 1, n):
            hi = max(his[i - period + 1 : i + 1])
            lo = min(los[i - period + 1 : i + 1])
            out[i] = (hi + lo) / 2
        return out

    tenkan_line = midline(tenkan)
    kijun_line = midline(kijun)

    # 현재 시점에 유효한 스팬 = kijun 기간 전에 계산된 값
    span_a: Series = [None] * n
    span_b_line: Series = [None] * n
    raw_b = midline(senkou_b)
    for i in range(n):
        j = i - kijun
        if j < 0:
            continue
        if tenkan_line[j] is not None and kijun_line[j] is not None:
            span_a[i] = (tenkan_line[j] + kijun_line[j]) / 2
        if raw_b[j] is not None:
            span_b_line[i] = raw_b[j]
    return tenkan_line, kijun_line, span_a, span_b_line


def rolling_max(xs: list[float], period: int) -> Series:
    out: Series = [None] * len(xs)
    for i in range(period - 1, len(xs)):
        out[i] = max(xs[i - period + 1 : i + 1])
    return out


def rolling_min(xs: list[float], period: int) -> Series:
    out: Series = [None] * len(xs)
    for i in range(period - 1, len(xs)):
        out[i] = min(xs[i - period + 1 : i + 1])
    return out
