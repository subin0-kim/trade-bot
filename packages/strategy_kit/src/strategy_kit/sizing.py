"""포지션 사이징 모듈 — "얼마나 살 것인가".

모든 사이저는 size(view, event, equity) -> Decimal(수량) 을 구현한다.
정책(aggressiveness)에 의한 축소는 봇 런타임이 곱한다 — 여기서는 순수 계산만.
"""

from __future__ import annotations

from decimal import Decimal

from indicators import atr

from .view import EntryEvent, MarketView


class FixedFractionSizer:
    """계좌 자산의 고정 비율만큼 매수."""

    def __init__(self, fraction: float = 0.1):
        self.name = f"fixed_frac({fraction})"
        self.fraction = Decimal(str(fraction))

    def size(self, view: MarketView, event: EntryEvent, equity: Decimal) -> Decimal:
        budget = equity * self.fraction
        return Decimal(int(budget / view.close))


class ATRRiskSizer:
    """변동성 역비례 사이징 — '한 번의 손절로 계좌의 risk_pct%만 잃도록'.

    손절 폭을 ATR×stop_mult로 가정: 수량 = (equity × risk%) / (ATR × stop_mult)
    변동성이 큰 종목은 적게, 작은 종목은 많이 — 종목 간 리스크 균등화.
    """

    def __init__(self, risk_pct: float = 1.0, atr_period: int = 14, stop_mult: float = 2.0):
        self.name = f"atr_risk({risk_pct}%,{atr_period},x{stop_mult})"
        self.risk_pct = risk_pct
        self.atr_period = atr_period
        self.stop_mult = stop_mult

    def size(self, view: MarketView, event: EntryEvent, equity: Decimal) -> Decimal:
        a = atr(view.primary, self.atr_period)
        if not a or a[-1] is None or a[-1] <= 0:
            return Decimal(0)
        risk_amount = float(equity) * self.risk_pct / 100.0
        qty = int(risk_amount / (a[-1] * self.stop_mult))
        # 예산 한도: 계좌의 30%를 넘지 않게 안전벨트
        max_qty = int(equity * Decimal("0.3") / view.close)
        return Decimal(min(qty, max_qty))
