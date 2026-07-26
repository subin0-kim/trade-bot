"""전략 인터페이스.

전략은 순수 함수형에 가깝게: 캔들을 받아 시그널을 반환할 뿐,
주문 실행·리스크 체크는 봇 런타임(botkit)이 담당한다.
백테스트와 실거래에서 동일한 전략 코드를 쓰기 위한 경계다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Candle, OrderSide


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: OrderSide | None  # None = HOLD
    strength: float = 0.0     # 0.0 ~ 1.0
    reason: str = ""

    @property
    def is_actionable(self) -> bool:
        return self.action is not None and self.strength >= 0.5


class Strategy(Protocol):
    name: str

    def decide(self, symbol: str, candles: list[Candle]) -> Signal: ...
