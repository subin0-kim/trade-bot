"""ScheduledStrategy — 기간별로 하위 전략을 스위칭하는 메타 전략.

백테스트에서는 사후 라벨 스케줄로 레짐 스위칭의 상한 성능을 측정하고,
라이브에서는 Commander가 정책으로 같은 역할을 한다 (구조 동일).

스케줄에 해당 전략이 없는 기간(None) = 현금 레짐:
신규 진입 금지 + 보유 포지션은 즉시 청산.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .composite import CompositeStrategy
from .view import Decision, MarketView, OpenPosition


class RegimeMappedStrategy:
    """일자별 레짐 시리즈 + (레짐 → 전략) 매핑으로 스위칭하는 메타 전략.

    ScheduledStrategy와 달리 구간을 미리 알 필요가 없다 —
    레짐 판별기가 만든 시리즈(각 일자는 그날까지의 정보만 사용)를 그대로 소비하므로
    실시간 운용과 동일한 조건의 백테스트가 된다.
    regime 값은 문자열 키 (regime 패키지의 Regime enum 값과 호환).
    """

    def __init__(
        self,
        name: str,
        regime_series: dict[date, str],
        mapping: dict[str, CompositeStrategy | None],
    ):
        self.name = name
        self.mapping = mapping
        self._dates = sorted(regime_series)
        self._series = regime_series

    def _regime_at(self, d: date) -> str | None:
        """해당 일자의 레짐. 지수 휴장 등으로 없으면 직전 값."""
        import bisect

        idx = bisect.bisect_right(self._dates, d) - 1
        if idx < 0:
            return None
        return str(self._series[self._dates[idx]])

    def evaluate(
        self, view: MarketView, position: OpenPosition | None, equity: Decimal
    ) -> Decision:
        regime = self._regime_at(view.now.date())
        strategy = self.mapping.get(regime) if regime is not None else None
        if strategy is None:
            if position is not None:
                return Decision(
                    action="exit", side=None, quantity=position.quantity,
                    reasons=(f"[regime:{regime}] 현금 레짐 — 전량 청산",),
                )
            return Decision.hold(f"[regime:{regime}] 현금 레짐")
        return strategy.evaluate(view, position, equity)


class ScheduledStrategy:
    def __init__(
        self,
        name: str,
        schedule: list[tuple[date, date, CompositeStrategy | None]],
    ):
        self.name = name
        self.schedule = schedule

    def _active(self, d: date) -> CompositeStrategy | None:
        for start, end, strategy in self.schedule:
            if start <= d <= end:
                return strategy
        return None

    def evaluate(
        self, view: MarketView, position: OpenPosition | None, equity: Decimal
    ) -> Decision:
        strategy = self._active(view.now.date())
        if strategy is None:
            if position is not None:
                return Decision(
                    action="exit", side=None, quantity=position.quantity,
                    reasons=("[schedule] 현금 레짐 — 전량 청산",),
                )
            return Decision.hold("[schedule] 현금 레짐")
        return strategy.evaluate(view, position, equity)
