"""DryRunBroker — 실시세는 위임하고 주문만 로컬에서 모의 체결한다.

KIS는 모의투자가 있지만 Upbit은 없으므로, 모든 봇은 이 래퍼로
브로커에 무관하게 안전한 검증이 가능하다. 봇은 --live 플래그가
없는 한 항상 이 래퍼를 통해 거래한다.
"""

from __future__ import annotations

import itertools
from datetime import date, datetime
from decimal import Decimal

from .broker import Broker
from .models import (
    Balance,
    Candle,
    MarketRules,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)


class DryRunBroker:
    """시세 조회는 내부 브로커에 위임, 주문/잔고/포지션은 메모리에서 시뮬레이션."""

    def __init__(
        self,
        data_broker: Broker,
        initial_cash: Decimal = Decimal(10_000_000),
        fee_rate: Decimal = Decimal("0.00015"),
        sell_tax_rate: Decimal = Decimal("0.0018"),
    ):
        self._data = data_broker
        self._cash = initial_cash
        self._initial_cash = initial_cash
        self._positions: dict[str, Position] = {}
        self._open_orders: dict[str, Order] = {}
        self._fills: list[Order] = []
        self._fee_rate = fee_rate
        self._sell_tax_rate = sell_tax_rate
        self._seq = itertools.count(1)

    # --- 시세: 위임 ---
    def get_quote(self, symbol: str) -> Quote:
        return self._data.get_quote(symbol)

    def get_daily_candles(self, symbol: str, start: date, end: date, period: str = "D") -> list[Candle]:
        return self._data.get_daily_candles(symbol, start, end, period)

    def get_minute_candles(self, symbol: str, to_time: str | None = None) -> list[Candle]:
        return self._data.get_minute_candles(symbol, to_time)

    def get_market_rules(self, symbol: str) -> MarketRules:
        return self._data.get_market_rules(symbol)

    # --- 계좌: 시뮬레이션 ---
    def get_balance(self) -> Balance:
        total = self._cash + sum(
            (p.market_value for p in self._refreshed_positions()), Decimal(0)
        )
        return Balance(cash=self._cash, available_cash=self._cash, total_value=total)

    def get_positions(self) -> list[Position]:
        return self._refreshed_positions()

    def get_open_orders(self) -> list[Order]:
        self.tick()
        return list(self._open_orders.values())

    # --- 주문: 시뮬레이션 ---
    def place_order(self, request: OrderRequest) -> Order:
        quote = self.get_quote(request.symbol)
        order = Order(
            order_id=f"DRY-{next(self._seq):06d}",
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            filled_quantity=Decimal(0),
            price=request.price,
            status=OrderStatus.OPEN,
            ts=datetime.now(),
            meta={"dry_run": True},
        )

        if request.side == OrderSide.BUY:
            reserve_price = request.price if request.order_type == OrderType.LIMIT else quote.price
            cost = reserve_price * request.quantity
            if cost > self._cash:
                return self._reject(order, f"현금 부족: 필요 {cost}, 보유 {self._cash}")
        else:
            held = self._positions.get(request.symbol)
            if held is None or held.quantity < request.quantity:
                return self._reject(order, "보유 수량 부족")

        # 시장가 또는 즉시 체결 가능한 지정가면 바로 체결
        if request.order_type == OrderType.MARKET or self._is_marketable(order, quote.price):
            return self._fill(order, quote.price)

        self._open_orders[order.order_id] = order
        return order

    def cancel_order(self, order: Order) -> None:
        self._open_orders.pop(order.order_id, None)

    def tick(self) -> list[Order]:
        """미체결 지정가 주문을 현재가와 대조해 체결 처리. 체결된 주문 목록 반환."""
        filled = []
        for order in list(self._open_orders.values()):
            quote = self.get_quote(order.symbol)
            if self._is_marketable(order, quote.price):
                del self._open_orders[order.order_id]
                filled.append(self._fill(order, order.price))
        return filled

    # --- 리포트 ---
    def summary(self) -> dict:
        balance = self.get_balance()
        return {
            "initial_cash": str(self._initial_cash),
            "cash": str(balance.cash),
            "total_value": str(balance.total_value),
            "pnl": str(balance.total_value - self._initial_cash),
            "positions": {s: str(p.quantity) for s, p in self._positions.items()},
            "fills": len(self._fills),
            "open_orders": len(self._open_orders),
        }

    # --- 내부 ---
    @staticmethod
    def _is_marketable(order: Order, market_price: Decimal) -> bool:
        if order.price is None:
            return True
        if order.side == OrderSide.BUY:
            return market_price <= order.price
        return market_price >= order.price

    def _fill(self, order: Order, fill_price: Decimal) -> Order:
        qty = order.quantity
        gross = fill_price * qty
        fee = gross * self._fee_rate
        if order.side == OrderSide.BUY:
            self._cash -= gross + fee
            held = self._positions.get(order.symbol)
            if held:
                new_qty = held.quantity + qty
                new_avg = (held.avg_price * held.quantity + gross) / new_qty
                self._positions[order.symbol] = Position(
                    order.symbol, held.name, new_qty, new_avg, fill_price
                )
            else:
                self._positions[order.symbol] = Position(
                    order.symbol, order.symbol, qty, fill_price, fill_price
                )
        else:
            tax = gross * self._sell_tax_rate
            self._cash += gross - fee - tax
            held = self._positions[order.symbol]
            remaining = held.quantity - qty
            if remaining > 0:
                self._positions[order.symbol] = Position(
                    order.symbol, held.name, remaining, held.avg_price, fill_price
                )
            else:
                del self._positions[order.symbol]

        filled = Order(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=qty,
            filled_quantity=qty,
            price=fill_price,
            status=OrderStatus.FILLED,
            ts=datetime.now(),
            meta=order.meta,
        )
        self._fills.append(filled)
        return filled

    @staticmethod
    def _reject(order: Order, reason: str) -> Order:
        return Order(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=Decimal(0),
            price=order.price,
            status=OrderStatus.REJECTED,
            ts=datetime.now(),
            meta={**order.meta, "reject_reason": reason},
        )

    def _refreshed_positions(self) -> list[Position]:
        refreshed = []
        for symbol, p in self._positions.items():
            price = self.get_quote(symbol).price
            refreshed.append(Position(symbol, p.name, p.quantity, p.avg_price, price))
        self._positions = {p.symbol: p for p in refreshed}
        return refreshed
