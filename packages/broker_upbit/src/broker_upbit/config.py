"""업비트 설정 로드.

기본 경로: D:/upbit/config/upbit.yaml (환경변수 UPBIT_CONFIG_PATH로 변경 가능)
— KIS와 마찬가지로 비밀정보는 repo 밖에 둔다.

⚠️ 업비트는 모의투자 환경이 없다. 실계좌 키 하나뿐이므로
   DryRunBroker 없이는 안전한 검증이 불가능하다 (--live 게이트가 KIS보다 더 중요).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path("D:/upbit/config/upbit.yaml")
API_BASE = "https://api.upbit.com"


@dataclass(frozen=True)
class UpbitSettings:
    access_key: str
    secret_key: str
    base_url: str = API_BASE

    @classmethod
    def load(cls, path: Path | str | None = None) -> "UpbitSettings":
        config_path = Path(path or os.environ.get("UPBIT_CONFIG_PATH") or DEFAULT_CONFIG_PATH)
        if not config_path.exists():
            raise FileNotFoundError(
                f"업비트 설정 파일 없음: {config_path}\n"
                f"업비트 > 마이페이지 > Open API 관리에서 키를 발급해 아래 형식으로 저장하세요:\n"
                f"  access_key: \"...\"\n  secret_key: \"...\""
            )
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        access = (cfg.get("access_key") or "").strip()
        secret = (cfg.get("secret_key") or "").strip()
        if not access or not secret or access.startswith("여기에"):
            raise ValueError(f"{config_path}에 access_key / secret_key를 입력하세요")
        return cls(
            access_key=access,
            secret_key=secret,
            base_url=cfg.get("base_url", API_BASE),
        )
