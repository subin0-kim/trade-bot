"""UpbitBroker — trading_core.Broker 구현 (KRW 마켓 현물).

KIS와의 구조적 차이 (아키텍처 원칙 7: 시장 차이는 MarketRules로 노출):
  - **24시간 거래** → open_time/close_time = None
  - **거래세 없음** → sell_tax_rate = 0 (주식 0.18% 대비 왕복비용 1/3 수준)
  - **소수점 수량** → quantity_step = 1e-8 (주식은 1주 단위)
  - **최소 주문 5,000원** → min_order_value
  - **모의투자 환경 없음** → DryRunBroker 필수
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import requests

from trading_core.models import (
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

from .client import UpbitApiError, UpbitClient
from .config import UpbitSettings

# KRW 마켓 호가단위 (가격 구간별) — 지정가 주문 시 이 단위로 맞춰야 한다
TICK_TIERS = [
    (Decimal("2000000"), Decimal("1000")),
    (Decimal("1000000"), Decimal("500")),
    (Decimal("500000"), Decimal("100")),
    (Decimal("100000"), Decimal("50")),
    (Decimal("10000"), Decimal("10")),
    (Decimal("1000"), Decimal("1")),
    (Decimal("100"), Decimal("0.1")),
    (Decimal("10"), Decimal("0.01")),
    (Decimal("1"), Decimal("0.001")),
    (Decimal("0"), Decimal("0.0001")),
]


def tick_size(price: Decimal) -> Decimal:
    for threshold, tick in TICK_TIERS:
        if price >= threshold:
            return tick
    return Decimal("0.0001")


def align_price(price: Decimal) -> Decimal:
    """호가단위에 맞춰 내림 정렬."""
    tick = tick_size(price)
    return (price // tick) * tick


def _parse_ts(value: str) -> datetime:
    """업비트 KST 시각 문자열(2026-07-27T10:00:00) → naive datetime."""
    return datetime.fromisoformat(value.replace("Z", ""))


class UpbitBroker:
    """업비트 KRW 마켓 브로커. symbol 형식은 'KRW-BTC'."""

    def __init__(self, settings: UpbitSettings | None = None):
        self.settings = settings or UpbitSettings.load()
        self.client = UpbitClient(self.settings)

    # ------------------------------------------------------------------ 시세
    def get_quote(self, symbol: str) -> Quote:
        data = self.client.get("/v1/ticker", {"markets": symbol})
        row = data[0]
        return Quote(
            symbol=symbol,
            price=Decimal(str(row["trade_price"])),
            ts=datetime.now(),
        )

    def _candles(self, path: str, symbol: str, count: int, to: str | None = None) -> list[Candle]:
        params = {"market": symbol, "count": min(count, 200)}
        if to:
            params["to"] = to
        rows = self.client.get(path, params)
        candles = [
            Candle(
                ts=_parse_ts(r["candle_date_time_kst"]),
                open=Decimal(str(r["opening_price"])),
                high=Decimal(str(r["high_price"])),
                low=Decimal(str(r["low_price"])),
                close=Decimal(str(r["trade_price"])),
                volume=Decimal(str(r["candle_acc_trade_volume"])),
            )
            for r in rows
        ]
        return sorted(candles, key=lambda c: c.ts)  # 업비트는 최신순 → 오름차순 정렬

    def get_daily_candles(
        self, symbol: str, start: date, end: date, period: str = "D"
    ) -> list[Candle]:
        """일봉. 1콜 최대 200건이라 필요 시 to 파라미터로 이어붙인다."""
        path = {"D": "/v1/candles/days", "W": "/v1/candles/weeks", "M": "/v1/candles/months"}[period]
        wanted = (end - start).days + 1
        collected: dict[datetime, Candle] = {}
        cursor = f"{end.isoformat()}T23:59:59"
        while len(collected) < wanted:
            batch = self._candles(path, symbol, 200, cursor)
            if not batch:
                break
            for c in batch:
                collected[c.ts] = c
            oldest = batch[0].ts
            if oldest.date() <= start:
                break
            cursor = oldest.strftime("%Y-%m-%dT%H:%M:%S")
        return [c for ts, c in sorted(collected.items()) if start <= c.ts.date() <= end]

    def get_minute_candles(
        self, symbol: str, to_time: str | None = None, unit: int = 1, count: int = 200
    ) -> list[Candle]:
        """분봉. unit: 1/3/5/10/15/30/60/240 지원."""
        return self._candles(f"/v1/candles/minutes/{unit}", symbol, count, to_time)

    def get_market_rules(self, symbol: str) -> MarketRules:
        return MarketRules(
            symbol=symbol,
            min_order_value=Decimal(5000),      # 업비트 KRW 마켓 최소 주문
            quantity_step=Decimal("0.00000001"),  # 소수점 8자리
            open_time=None,                      # 24시간 거래
            close_time=None,
            fee_rate=Decimal("0.0005"),          # 0.05% (KRW 마켓 기본)
            sell_tax_rate=Decimal(0),            # 거래세 없음 ★
        )

    # ------------------------------------------------------------------ 계좌
    def _accounts(self) -> list[dict]:
        return self.client.get("/v1/accounts", group="default", auth=True)

    def get_balance(self) -> Balance:
        accounts = self._accounts()
        cash = available = Decimal(0)
        total = Decimal(0)
        for a in accounts:
            balance = Decimal(a["balance"])
            locked = Decimal(a["locked"])
            if a["currency"] == "KRW":
                cash = balance + locked
                available = balance
                total += cash
            else:
                avg = Decimal(a.get("avg_buy_price") or 0)
                total += (balance + locked) * avg  # 평가액은 아래 get_positions에서 현재가로 갱신
        return Balance(cash=cash, available_cash=available, total_value=total)

    def get_positions(self) -> list[Position]:
        accounts = [a for a in self._accounts() if a["currency"] != "KRW"]
        if not accounts:
            return []
        # KRW 마켓이 없는 보유 자산(상장폐지·BTC마켓 전용 코인 등)이 섞이면
        # /v1/ticker가 404를 던지므로, 유효한 마켓만 조회한다.
        valid = set(self.list_krw_markets())
        markets = [m for m in (f"KRW-{a['currency']}" for a in accounts) if m in valid]
        tickers = (
            {t["market"]: Decimal(str(t["trade_price"]))
             for t in self.client.get("/v1/ticker", {"markets": ",".join(markets)})}
            if markets else {}
        )
        positions = []
        for a in accounts:
            qty = Decimal(a["balance"]) + Decimal(a["locked"])
            if qty <= 0:
                continue
            market = f"KRW-{a['currency']}"
            avg = Decimal(a.get("avg_buy_price") or 0)
            positions.append(Position(
                symbol=market,
                name=a["currency"],
                quantity=qty,
                avg_price=avg,
                # 시세 조회 불가 자산은 평단으로 대체 (평가액 0원 표기 방지)
                current_price=tickers.get(market, avg),
            ))
        return positions

    def get_open_orders(self) -> list[Order]:
        rows = self.client.get(
            "/v1/orders/open", {"states[]": ["wait", "watch"]}, group="default", auth=True
        )
        orders = []
        for r in rows:
            executed = Decimal(r.get("executed_volume") or 0)
            orders.append(Order(
                order_id=r["uuid"],
                symbol=r["market"],
                side=OrderSide.BUY if r["side"] == "bid" else OrderSide.SELL,
                quantity=Decimal(r["volume"]) if r.get("volume") else Decimal(0),
                filled_quantity=executed,
                price=Decimal(r["price"]) if r.get("price") else None,
                status=OrderStatus.PARTIALLY_FILLED if executed > 0 else OrderStatus.OPEN,
                ts=_parse_ts(r["created_at"][:19]),
                meta={"ord_type": r.get("ord_type", "")},
            ))
        return orders

    # ------------------------------------------------------------------ 주문
    def place_order(self, request: OrderRequest) -> Order:
        side = "bid" if request.side == OrderSide.BUY else "ask"
        params: dict = {"market": request.symbol, "side": side}

        if request.order_type == OrderType.LIMIT:
            params["ord_type"] = "limit"
            params["price"] = str(align_price(request.price))
            params["volume"] = str(request.quantity)
        elif request.side == OrderSide.BUY:
            # 시장가 매수는 '금액' 지정 (price에 원화 총액, volume 없음)
            quote = self.get_quote(request.symbol)
            params["ord_type"] = "price"
            params["price"] = str((quote.price * request.quantity).quantize(Decimal("1")))
        else:
            # 시장가 매도는 '수량' 지정
            params["ord_type"] = "market"
            params["volume"] = str(request.quantity)

        data = self.client.post("/v1/orders", params)
        return Order(
            order_id=data["uuid"],
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            filled_quantity=Decimal(data.get("executed_volume") or 0),
            price=request.price,
            status=OrderStatus.OPEN,
            ts=datetime.now(),
            meta={"ord_type": params["ord_type"]},
        )

    def get_order_fill(self, uuid: str) -> tuple[str, Decimal, Decimal | None, Decimal]:
        """(상태, 체결수량, 평균체결가, 실납부수수료). trades의 체결금액/수량 가중평균.

        paid_fee는 업비트가 실제로 차감한 KRW 수수료 — 상수 가정 대신 이 값으로
        원장 현금을 계산해야 정확하다 (수수료 이벤트·등급 변동에도 안전).
        """
        data = self.client.get("/v1/order", {"uuid": uuid}, group="default", auth=True)
        vol = Decimal(data.get("executed_volume") or "0")
        fee = Decimal(data.get("paid_fee") or "0")
        avg = None
        trades = data.get("trades") or []
        if trades:
            funds = sum(Decimal(t["funds"]) for t in trades)
            tvol = sum(Decimal(t["volume"]) for t in trades)
            avg = funds / tvol if tvol > 0 else None
        return data.get("state", ""), vol, avg, fee

    def cancel_order(self, order: Order) -> None:
        """미체결 주문 취소 (DELETE /v1/order). 이미 체결/취소면 에러 — 호출부가 무시."""
        self.client.delete("/v1/order", {"uuid": order.order_id})

    def settle_order(self, order: Order, timeout: float = 15.0
                     ) -> tuple[Decimal, Decimal | None, Decimal | None]:
        """주문 확정: 체결 대기 → 미체결이면 취소 → 최종 (수량, 평균가, 실수수료) 반환.

        취소 요청과 체결이 경합할 수 있으므로 취소 후 반드시 재조회 —
        반환값이 원장에 기록할 최종 진실이다. 미체결 잔량은 취소되므로
        다음 사이클이 새 주문으로 재시도하면 된다 (잔고 잠김 없음).
        """
        filled, avg, fee = self.wait_fill(order.order_id, timeout=timeout)
        if filled > 0 and avg is not None:
            return filled, avg, fee
        try:
            self.cancel_order(order)
        except (UpbitApiError, requests.RequestException):
            pass  # 이미 done/cancel이거나 네트워크 실패 — 아래 재조회가 진실
        try:
            _, filled, avg, fee = self.get_order_fill(order.order_id)
        except (UpbitApiError, requests.RequestException):
            pass
        return filled, avg, fee

    def wait_fill(self, uuid: str, timeout: float = 15.0, interval: float = 1.0
                  ) -> tuple[Decimal, Decimal | None, Decimal]:
        """체결 확인 폴링 — (체결수량, 평균체결가, 실수수료). 시장가는 보통 즉시 done."""
        from time import monotonic, sleep

        deadline = monotonic() + timeout
        vol, avg, fee = Decimal(0), None, Decimal(0)
        while True:
            try:
                state, vol, avg, fee = self.get_order_fill(uuid)
                if state in ("done", "cancel"):
                    return vol, avg, fee
            except Exception:
                pass
            if monotonic() > deadline:
                return vol, avg, fee
            sleep(interval)

    # ------------------------------------------------------------------ 확장
    def list_krw_markets(self) -> list[str]:
        """KRW 마켓 전체 심볼 (유니버스 구성용)."""
        rows = self.client.get("/v1/market/all", {"is_details": "false"})
        return [r["market"] for r in rows if r["market"].startswith("KRW-")]
