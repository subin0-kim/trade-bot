"""MarketView — 전략 모듈이 보는 시장 스냅샷.

멀티타임프레임 지원: candles는 타임프레임별 '완성된 봉'만 담는다.
(진행 중인 상위 TF 봉을 넣으면 백테스트에서 미래참조가 되므로 금지 —
데이터를 채우는 쪽(백테스터/봇 런타임)이 이 계약을 보장한다)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from trading_core.models import Candle, OrderSide


@dataclass
class MarketView:
    symbol: str
    primary_tf: str                       # 전략의 기준 타임프레임 (예: "D", "5m")
    candles: dict[str, list[Candle]]      # tf → 완성봉 리스트 (오름차순)

    @property
    def primary(self) -> list[Candle]:
        return self.candles[self.primary_tf]

    @property
    def now(self) -> datetime:
        return self.primary[-1].ts

    @property
    def close(self) -> Decimal:
        return self.primary[-1].close


@dataclass
class OpenPosition:
    """전략 판단용 보유 상태 (청산 모듈이 사용)."""
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    entry_ts: datetime
    bars_held: int = 0
    highest_close: Decimal = Decimal(0)   # 진입 후 최고 종가 (트레일링용)

    def update_on_bar(self, candle: Candle) -> None:
        self.bars_held += 1
        if candle.close > self.highest_close:
            self.highest_close = candle.close


@dataclass(frozen=True)
class EntryEvent:
    side: OrderSide
    strength: float
    reason: str


@dataclass(frozen=True)
class ExitEvent:
    reason: str


@dataclass(frozen=True)
class Decision:
    """CompositeStrategy의 최종 판단."""
    action: str                     # "enter" | "exit" | "hold"
    side: OrderSide | None = None
    quantity: Decimal = Decimal(0)
    reasons: tuple[str, ...] = ()

    @classmethod
    def hold(cls, *reasons: str) -> "Decision":
        return cls(action="hold", reasons=reasons)
