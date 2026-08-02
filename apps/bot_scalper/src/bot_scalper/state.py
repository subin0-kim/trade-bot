"""단타봇 원장 — 봇이 만든 포지션만 관리 (기존 보유 자산 불가침, 코인봇과 동일 원칙)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass
class Position:
    symbol: str          # "KRW-XRP"
    tier: float          # 3.0 | 5.0
    quantity: str
    entry_price: str
    entry_ts: str
    target_price: str    # 매물대 목표 (지정가 매도)
    timeout_at: str      # 적응형 타임아웃 도달 시각 (ISO)
    order_id: str = ""   # live 매도 주문 id


@dataclass
class ScalperState:
    cash: str
    mode: str            # "dry-run" | "live"
    positions: dict[str, Position] = field(default_factory=dict)  # key = f"{symbol}#{tier}"

    @classmethod
    def load(cls, path: Path, seed: Decimal, mode: str) -> "ScalperState":
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            st = cls(cash=d["cash"], mode=d.get("mode", "dry-run"),
                     positions={k: Position(**v) for k, v in d.get("positions", {}).items()})
            if st.mode != mode:
                raise SystemExit(f"원장 모드({st.mode}) ≠ 실행 모드({mode}) — 기동 거부. "
                                 f"모드 전환은 state 파일 처리 후에.")
            return st
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(cash=str(seed), mode=mode)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "cash": self.cash, "mode": self.mode,
            "positions": {k: vars(p) for k, p in self.positions.items()},
        }, ensure_ascii=False, indent=1), encoding="utf-8")
