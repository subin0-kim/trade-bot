"""Commander가 발행하는 거래 정책.

봇은 정책 스토어(초기엔 JSON 파일, 이후 DB)에서 정책을 주기적으로 읽는다.
정책이 없거나 만료됐으면 보수 모드가 기본값이다 —
Commander가 죽어도 봇이 폭주하지 않게 하는 안전장치.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Policy:
    trading_enabled: bool = True
    aggressiveness: float = 0.5           # 0.0 관망 ~ 1.0 공격
    max_trades_today: int | None = None   # None이면 리스크 엔진 한도만 적용
    preferred_strategies: list[str] = field(default_factory=list)
    valid_until: datetime | None = None   # None이면 무기한
    reason: str = ""
    issued_at: datetime | None = None

    @classmethod
    def conservative(cls, reason: str) -> "Policy":
        return cls(trading_enabled=False, aggressiveness=0.0, reason=reason)

    def is_valid(self, now: datetime | None = None) -> bool:
        if self.valid_until is None:
            return True
        return (now or datetime.now()) < self.valid_until

    def to_dict(self) -> dict:
        return {
            "trading_enabled": self.trading_enabled,
            "aggressiveness": self.aggressiveness,
            "max_trades_today": self.max_trades_today,
            "preferred_strategies": self.preferred_strategies,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "reason": self.reason,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        return cls(
            trading_enabled=d.get("trading_enabled", True),
            aggressiveness=d.get("aggressiveness", 0.5),
            max_trades_today=d.get("max_trades_today"),
            preferred_strategies=d.get("preferred_strategies", []),
            valid_until=datetime.fromisoformat(d["valid_until"]) if d.get("valid_until") else None,
            reason=d.get("reason", ""),
            issued_at=datetime.fromisoformat(d["issued_at"]) if d.get("issued_at") else None,
        )


def load_policy(path: Path | str, default: Policy | None = None) -> Policy:
    """정책 파일 로드. 만료·파손이면 보수 모드 반환.

    파일이 없으면 default 반환 (미지정 시 보수 모드) —
    Commander 미가동 단계에서는 default=Policy()로 기본 정책 운용,
    Commander 가동 후에는 default 없이 호출해 fail-safe로 전환한다.
    """
    path = Path(path)
    if not path.exists():
        return default or Policy.conservative(f"정책 파일 없음: {path}")
    try:
        policy = Policy.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return Policy.conservative(f"정책 파일 파손: {e}")
    if not policy.is_valid():
        return Policy.conservative(f"정책 만료됨 (valid_until={policy.valid_until})")
    return policy


def save_policy(policy: Policy, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(policy.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
