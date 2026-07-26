"""거래 도메인 모델.

브로커(KIS/Upbit)에 비종속적인 공통 타입만 정의한다.
금액/수량은 부동소수점 오차를 피하기 위해 Decimal을 사용한다
(국내주식은 정수 원화지만, 코인은 소수점 수량·가격이 필요하다).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: Decimal
    ts: datetime


@dataclass(frozen=True)
class Balance:
    cash: Decimal            # 예수금 총액
    available_cash: Decimal  # 주문가능현금 (주식은 D+2 정산 반영, 코인은 즉시)
    total_value: Decimal     # 총평가금액 (현금 + 보유자산)


@dataclass(frozen=True)
class Position:
    symbol: str
    name: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.current_price

    @property
    def pnl(self) -> Decimal:
        return (self.current_price - self.avg_price) * self.quantity


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType = OrderType.LIMIT
    price: Decimal | None = None  # LIMIT이면 필수, MARKET이면 None

    def __post_init__(self):
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("LIMIT 주문에는 price가 필요합니다")


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    filled_quantity: Decimal
    price: Decimal | None
    status: OrderStatus
    ts: datetime
    # 브로커별 부가정보 (예: KIS의 KRX_FWDG_ORD_ORGNO) — 취소/정정 시 필요
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MarketRules:
    """시장별 제약. 추상화로 통일하지 않고 메타데이터로 노출한다."""
    symbol: str
    min_order_value: Decimal      # 최소 주문 금액
    quantity_step: Decimal        # 수량 단위 (주식=1, 코인=소수점)
    open_time: time | None        # None이면 24시간 (코인)
    close_time: time | None
    fee_rate: Decimal             # 매매 수수료율
    sell_tax_rate: Decimal        # 매도 세율 (주식 거래세, 코인=0)
