"""CompositeStrategy — 진입/필터/청산/사이징 모듈을 조립한 전략.

판단 순서:
  포지션 있음 → 청산 모듈들을 순서대로 검사 (첫 발동 채택)
  포지션 없음 → 진입 신호 → 모든 필터 통과 → 사이징 → 진입 결정
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from .view import Decision, EntryEvent, ExitEvent, MarketView, OpenPosition


class EntryModule(Protocol):
    name: str
    def check(self, view: MarketView) -> EntryEvent | None: ...


class FilterModule(Protocol):
    name: str
    def allow(self, view: MarketView, event: EntryEvent) -> tuple[bool, str]: ...


class ExitModule(Protocol):
    name: str
    def check(self, view: MarketView, position: OpenPosition) -> ExitEvent | None: ...


class SizerModule(Protocol):
    name: str
    def size(self, view: MarketView, event: EntryEvent, equity: Decimal) -> Decimal: ...


class CompositeStrategy:
    def __init__(
        self,
        name: str,
        entry: EntryModule,
        exits: list[ExitModule],
        sizer: SizerModule,
        filters: list[FilterModule] | None = None,
    ):
        self.name = name
        self.entry = entry
        self.filters = filters or []
        self.exits = exits
        self.sizer = sizer

    def describe(self) -> dict:
        return {
            "name": self.name,
            "entry": self.entry.name,
            "filters": [f.name for f in self.filters],
            "exits": [e.name for e in self.exits],
            "sizer": self.sizer.name,
        }

    def evaluate(
        self, view: MarketView, position: OpenPosition | None, equity: Decimal
    ) -> Decision:
        # --- 보유 중: 청산 판단 ---
        if position is not None:
            for exit_module in self.exits:
                event = exit_module.check(view, position)
                if event is not None:
                    return Decision(
                        action="exit",
                        side=None,
                        quantity=position.quantity,
                        reasons=(f"[{exit_module.name}] {event.reason}",),
                    )
            return Decision.hold("보유 유지")

        # --- 미보유: 진입 판단 ---
        event = self.entry.check(view)
        if event is None:
            return Decision.hold("진입 신호 없음")

        reasons = [f"[{self.entry.name}] {event.reason}"]
        for f in self.filters:
            ok, why = f.allow(view, event)
            reasons.append(f"[{f.name}] {why}")
            if not ok:
                return Decision.hold(*reasons)

        quantity = self.sizer.size(view, event, equity)
        # 최소 단위는 시장별로 다르다 (주식 1주 / 코인 1e-8) — 0 이하만 거른다.
        # 단위 정렬·최소주문금액 검사는 사이저가 이미 수행한다.
        if quantity <= 0:
            return Decision.hold(*reasons, "사이징 결과 수량 0")

        return Decision(
            action="enter", side=event.side, quantity=quantity,
            reasons=tuple(reasons), score=event.score,
        )
