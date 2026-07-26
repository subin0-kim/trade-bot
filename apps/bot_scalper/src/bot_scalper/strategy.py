"""단타봇 전략.

MACrossStrategy는 배관 검증용 샘플 전략이다 — 실전 투입용이 아니다.
실제 전략은 백테스트 검증 후 교체한다.
"""

from __future__ import annotations

from decimal import Decimal

from trading_core import Candle, OrderSide, Signal


def sma(candles: list[Candle], period: int) -> Decimal | None:
    if len(candles) < period:
        return None
    closes = [c.close for c in candles[-period:]]
    return sum(closes, Decimal(0)) / period


class MACrossStrategy:
    """단기/장기 이동평균 골든/데드 크로스 (분봉)."""

    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.name = f"ma_cross_{short_period}_{long_period}"
        self.short_period = short_period
        self.long_period = long_period

    def decide(self, symbol: str, candles: list[Candle]) -> Signal:
        # 직전 캔들 기준 크로스 감지를 위해 +1개 필요
        if len(candles) < self.long_period + 1:
            return Signal(symbol, None, reason="캔들 수 부족")

        short_now = sma(candles, self.short_period)
        long_now = sma(candles, self.long_period)
        short_prev = sma(candles[:-1], self.short_period)
        long_prev = sma(candles[:-1], self.long_period)

        if short_prev <= long_prev and short_now > long_now:
            return Signal(
                symbol, OrderSide.BUY, strength=0.7,
                reason=f"골든크로스 MA{self.short_period}({short_now:.0f}) > MA{self.long_period}({long_now:.0f})",
            )
        if short_prev >= long_prev and short_now < long_now:
            return Signal(
                symbol, OrderSide.SELL, strength=0.7,
                reason=f"데드크로스 MA{self.short_period}({short_now:.0f}) < MA{self.long_period}({long_now:.0f})",
            )
        return Signal(symbol, None, reason="크로스 없음")
