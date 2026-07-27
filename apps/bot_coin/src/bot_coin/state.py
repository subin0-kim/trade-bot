"""코인봇 포지션 원장 — 안전의 핵심.

⚠️ 업비트는 모의투자가 없고 계좌에 사용자의 기존 자산(BTC·XRP 등)이 있다.
봇은 **이 원장에 기록된 포지션만** 관리한다:
  - 청산 대상 = 원장에 있는 것만. 계좌의 다른 보유분은 절대 건드리지 않는다
  - 매수 예산 = 봇에 할당된 budget 내 현금만. 계좌 전체 잔고를 쓰지 않는다
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass
class CoinPosition:
    symbol: str
    quantity: str            # Decimal 문자열 (소수점 8자리)
    entry_price: str
    entry_ts: str            # ISO
    strategy: str            # "bull_breakout" | "shock_follow"
    highest_close: str = "0"
    exit_due: str = ""       # shock 포지션의 청산 예정 시각 (ISO)


@dataclass
class CoinBotState:
    cash: str                             # 봇 할당 예산 중 현금
    positions: dict[str, CoinPosition] = field(default_factory=dict)
    last_shock_date: str = ""             # 쇼크 이벤트 중복 진입 방지 (YYYY-MM-DD)

    @classmethod
    def load(cls, path: Path, budget: Decimal) -> "CoinBotState":
        if not path.exists():
            return cls(cash=str(budget))
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            cash=raw["cash"],
            positions={s: CoinPosition(**p) for s, p in raw.get("positions", {}).items()},
            last_shock_date=raw.get("last_shock_date", ""),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"cash": self.cash,
                 "positions": {s: asdict(p) for s, p in self.positions.items()},
                 "last_shock_date": self.last_shock_date},
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
