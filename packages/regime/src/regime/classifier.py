"""레짐 판별기 v1 — 규칙 기반 + 히스테리시스.

원칙:
- i번째 봉의 레짐은 i번째 봉 '종가까지의' 데이터만 사용 (look-ahead 없음)
- 히스테리시스: 새 레짐이 confirm_days 연속 관측될 때만 전환 (플래핑 방지)
- 규칙은 단순하게 시작 — 정교화는 사후 라벨 일치율·스위칭 성과로 검증하며 진행

v1 규칙 (지수 일봉):
  BULL     : 종가 > MA(long) 그리고 MA(short) > MA(mid)
  BEAR     : 종가 < MA(long) 그리고 MA(short) < MA(mid)
  SIDEWAYS : 그 외
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from indicators import closes, sma
from trading_core.models import Candle


class Regime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


@dataclass
class RegimeClassifier:
    short_ma: int = 20
    mid_ma: int = 60
    long_ma: int = 120
    confirm_days: int = 5   # 전환 확정에 필요한 연속 관측 일수

    def raw_signal(self, xs: list[float], short, mid, long, i: int) -> Regime:
        s, m, l = short[i], mid[i], long[i]
        if l is None or s is None or m is None:
            return Regime.SIDEWAYS
        if xs[i] > l and s > m:
            return Regime.BULL
        if xs[i] < l and s < m:
            return Regime.BEAR
        return Regime.SIDEWAYS

    def classify_series(self, candles: list[Candle]) -> dict[date, Regime]:
        """일자 → 확정 레짐. 각 일자의 값은 그날 종가까지의 정보만 사용."""
        xs = closes(candles)
        short = sma(xs, self.short_ma)
        mid = sma(xs, self.mid_ma)
        long = sma(xs, self.long_ma)

        series: dict[date, Regime] = {}
        current = Regime.SIDEWAYS
        candidate: Regime | None = None
        streak = 0

        for i, c in enumerate(candles):
            raw = self.raw_signal(xs, short, mid, long, i)
            if raw == current:
                candidate, streak = None, 0
            elif raw == candidate:
                streak += 1
                if streak >= self.confirm_days:
                    current = raw
                    candidate, streak = None, 0
            else:
                candidate, streak = raw, 1
            series[c.ts.date()] = current
        return series
