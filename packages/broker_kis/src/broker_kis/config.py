"""KIS 설정 로드.

공식 샘플(open-trading-api)과 동일한 kis_devlp.yaml 포맷을 사용한다.
기본 경로: D:/kis/config/kis_devlp.yaml (환경변수 KIS_CONFIG_PATH로 변경 가능)
→ 비밀정보가 repo 밖에 있게 된다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path("D:/kis/config/kis_devlp.yaml")


@dataclass(frozen=True)
class KISSettings:
    env: str          # "real" | "paper"
    app_key: str
    app_secret: str
    account: str      # 계좌번호 앞 8자리
    product: str      # 계좌상품코드 뒤 2자리
    base_url: str
    ws_url: str
    hts_id: str
    user_agent: str
    config_path: Path | None = None  # 로드된 yaml 위치 — 토큰 캐시 기본 경로 유도용

    @property
    def is_paper(self) -> bool:
        return self.env == "paper"

    @classmethod
    def load(cls, env: str = "paper", path: Path | str | None = None) -> "KISSettings":
        if env not in ("real", "paper"):
            raise ValueError(f"env는 'real' 또는 'paper': {env}")

        config_path = Path(path or os.environ.get("KIS_CONFIG_PATH") or DEFAULT_CONFIG_PATH)
        if not config_path.exists():
            raise FileNotFoundError(
                f"KIS 설정 파일 없음: {config_path}\n"
                f"open-trading-api의 kis_devlp.yaml을 복사해 앱키/계좌를 입력하세요."
            )
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

        if env == "real":
            return cls(
                env=env,
                app_key=cfg["my_app"],
                app_secret=cfg["my_sec"],
                account=cfg["my_acct_stock"],
                product=cfg["my_prod"],
                base_url=cfg["prod"],
                ws_url=cfg["ops"],
                hts_id=cfg["my_htsid"],
                user_agent=cfg["my_agent"],
                config_path=config_path,
            )
        return cls(
            env=env,
            app_key=cfg["paper_app"],
            app_secret=cfg["paper_sec"],
            account=cfg["my_paper_stock"],
            product=cfg["my_prod"],
            base_url=cfg["vps"],
            ws_url=cfg["vops"],
            hts_id=cfg["my_htsid"],
            user_agent=cfg["my_agent"],
            config_path=config_path,
        )
