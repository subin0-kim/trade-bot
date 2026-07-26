"""리스크 엔진 — Commander 정책과 별개의 하드 리밋.

Commander의 aggressiveness는 이 한도 '안에서만' 작동한다.
어떤 정책도 이 한도를 풀 수 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Balance, OrderRequest, OrderSide, Position, Quote


@dataclass
class RiskLimits:
    max_position_pct: float = 20.0    # 종목당 계좌 대비 최대 비중 (%)
    max_trades_per_day: int = 10
    max_daily_loss_pct: float = 3.0   # 당일 손실 한도 (계좌 대비 %)
    kill_switch: bool = False         # True면 모든 신규 주문 차단


@dataclass(frozen=True)
class RiskVerdict:
    allowed: bool
    reason: str = ""


class RiskEngine:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def check(
        self,
        request: OrderRequest,
        *,
        quote: Quote,
        balance: Balance,
        positions: list[Position],
        trades_today: int,
        daily_pnl: Decimal,
    ) -> RiskVerdict:
        if self.limits.kill_switch:
            return RiskVerdict(False, "kill switch 활성화됨")

        if trades_today >= self.limits.max_trades_per_day:
            return RiskVerdict(
                False, f"일일 거래 한도 초과 ({trades_today}/{self.limits.max_trades_per_day})"
            )

        if balance.total_value > 0:
            loss_pct = float(-daily_pnl / balance.total_value * 100)
            if loss_pct >= self.limits.max_daily_loss_pct:
                return RiskVerdict(
                    False, f"당일 손실 한도 도달 ({loss_pct:.2f}% >= {self.limits.max_daily_loss_pct}%)"
                )

        if request.side == OrderSide.BUY and balance.total_value > 0:
            price = request.price if request.price is not None else quote.price
            order_value = price * request.quantity
            held_value = next(
                (p.market_value for p in positions if p.symbol == request.symbol),
                Decimal(0),
            )
            position_pct = float((held_value + order_value) / balance.total_value * 100)
            if position_pct > self.limits.max_position_pct:
                return RiskVerdict(
                    False,
                    f"종목 비중 한도 초과 ({position_pct:.1f}% > {self.limits.max_position_pct}%)",
                )

        return RiskVerdict(True)
