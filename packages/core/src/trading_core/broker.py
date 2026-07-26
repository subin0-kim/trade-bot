"""브로커 공통 인터페이스.

KIS/Upbit 어댑터가 이 Protocol을 구현한다.
여기에 없는 브로커 고유 기능(조건부지정가, 시간외단일가 등)은
어댑터의 확장 메서드로 제공하고 공통 인터페이스에 넣지 않는다.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from .models import Balance, Candle, MarketRules, Order, OrderRequest, Position, Quote


@runtime_checkable
class Broker(Protocol):
    # --- 시세 ---
    def get_quote(self, symbol: str) -> Quote: ...

    def get_daily_candles(
        self, symbol: str, start: date, end: date, period: str = "D"
    ) -> list[Candle]:
        """period: D(일) / W(주) / M(월). 오름차순 반환."""
        ...

    def get_minute_candles(self, symbol: str, to_time: str | None = None) -> list[Candle]:
        """to_time: HHMMSS (None이면 현재 시각 기준). 오름차순 반환."""
        ...

    def get_market_rules(self, symbol: str) -> MarketRules: ...

    # --- 계좌 ---
    def get_balance(self) -> Balance: ...
    def get_positions(self) -> list[Position]: ...
    def get_open_orders(self) -> list[Order]: ...

    # --- 주문 ---
    def place_order(self, request: OrderRequest) -> Order: ...
    def cancel_order(self, order: Order) -> None: ...
