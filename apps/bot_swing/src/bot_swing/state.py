"""스윙봇 포지션 상태 영속화.

봇은 하루 1회 실행되는 프로세스라 보유 상태를 파일로 유지한다.
(--live 모드에서는 브로커 잔고가 진실이지만, dry-run에서는 이 파일이 원장)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path


@dataclass
class HeldPosition:
    symbol: str
    name: str
    quantity: int
    entry_price: str        # Decimal 문자열
    entry_ts: str           # ISO
    strategy: str
    bars_held: int = 0
    highest_close: str = "0"

    def to_open_position(self):
        from trading_core.models import OrderSide
        from strategy_kit import OpenPosition
        from datetime import datetime

        return OpenPosition(
            side=OrderSide.BUY,
            quantity=Decimal(self.quantity),
            entry_price=Decimal(self.entry_price),
            entry_ts=datetime.fromisoformat(self.entry_ts),
            bars_held=self.bars_held,
            highest_close=Decimal(self.highest_close),
        )


@dataclass
class BotState:
    cash: str                                   # Decimal 문자열
    positions: dict[str, HeldPosition]

    @classmethod
    def load(cls, path: Path, initial_cash: Decimal) -> "BotState":
        if not path.exists():
            return cls(cash=str(initial_cash), positions={})
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            cash=raw["cash"],
            positions={s: HeldPosition(**p) for s, p in raw["positions"].items()},
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"cash": self.cash, "positions": {s: asdict(p) for s, p in self.positions.items()}},
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
