"""오프라인 테스트용 가짜 브로커.

API 키 없이 봇 루프 전체(시세→시그널→리스크→주문)를 검증할 때 사용.
시드 고정 랜덤워크로 분봉을 생성한다.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from .models import (
    Balance,
    Candle,
    MarketRules,
    Order,
    OrderRequest,
    OrderStatus,
    Position,
    Quote,
)


class FakeBroker:
    """랜덤워크 시세를 생성하는 데이터 전용 브로커 (DryRunBroker와 조합해 사용)."""

    def __init__(self, base_price: int = 70_000, seed: int = 42, drift: float = 0.0):
        self._rng = random.Random(seed)
        self._base_price = base_price
        self._drift = drift
        self._series: dict[str, list[Candle]] = {}

    def _ensure_series(self, symbol: str, n: int = 200) -> list[Candle]:
        if symbol not in self._series:
            candles = []
            price = float(self._base_price)
            ts = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=n)
            for i in range(n):
                change = self._rng.gauss(self._drift, 0.002)
                o = price
                price = max(price * (1 + change), 1.0)
                c = price
                hi = max(o, c) * (1 + abs(self._rng.gauss(0, 0.0005)))
                lo = min(o, c) * (1 - abs(self._rng.gauss(0, 0.0005)))
                candles.append(
                    Candle(
                        ts=ts + timedelta(minutes=i),
                        open=Decimal(str(round(o))),
                        high=Decimal(str(round(hi))),
                        low=Decimal(str(round(lo))),
                        close=Decimal(str(round(c))),
                        volume=Decimal(self._rng.randint(1_000, 50_000)),
                    )
                )
            self._series[symbol] = candles
        return self._series[symbol]

    def advance(self, symbol: str) -> None:
        """다음 분봉 1개 생성 (봇 루프 반복 시뮬레이션용)."""
        series = self._ensure_series(symbol)
        last = series[-1]
        change = self._rng.gauss(self._drift, 0.002)
        o = float(last.close)
        c = max(o * (1 + change), 1.0)
        series.append(
            Candle(
                ts=last.ts + timedelta(minutes=1),
                open=Decimal(str(round(o))),
                high=Decimal(str(round(max(o, c)))),
                low=Decimal(str(round(min(o, c)))),
                close=Decimal(str(round(c))),
                volume=Decimal(self._rng.randint(1_000, 50_000)),
            )
        )

    # --- Broker protocol ---
    def get_quote(self, symbol: str) -> Quote:
        last = self._ensure_series(symbol)[-1]
        return Quote(symbol=symbol, price=last.close, ts=datetime.now())

    def get_minute_candles(self, symbol: str, to_time: str | None = None) -> list[Candle]:
        return list(self._ensure_series(symbol))

    def get_daily_candles(self, symbol: str, start: date, end: date, period: str = "D") -> list[Candle]:
        return list(self._ensure_series(symbol))

    def get_market_rules(self, symbol: str) -> MarketRules:
        return MarketRules(
            symbol=symbol,
            min_order_value=Decimal(0),
            quantity_step=Decimal(1),
            open_time=time(9, 0),
            close_time=time(15, 30),
            fee_rate=Decimal("0.00015"),
            sell_tax_rate=Decimal("0.0018"),
        )

    def get_balance(self) -> Balance:
        raise NotImplementedError("FakeBroker는 데이터 전용 — DryRunBroker로 감싸서 사용하세요")

    def get_positions(self) -> list[Position]:
        raise NotImplementedError("FakeBroker는 데이터 전용 — DryRunBroker로 감싸서 사용하세요")

    def get_open_orders(self) -> list[Order]:
        raise NotImplementedError("FakeBroker는 데이터 전용 — DryRunBroker로 감싸서 사용하세요")

    def place_order(self, request: OrderRequest) -> Order:
        raise NotImplementedError("FakeBroker는 데이터 전용 — DryRunBroker로 감싸서 사용하세요")

    def cancel_order(self, order: Order) -> None:
        raise NotImplementedError("FakeBroker는 데이터 전용 — DryRunBroker로 감싸서 사용하세요")
