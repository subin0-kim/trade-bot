"""이벤트 로그 — 모든 봇이 시그널/주문/체결/정책 변경을 append한다.

초기엔 JSONL 파일, 이후 중앙 DB로 교체 (인터페이스 유지).
이 로그는 대시보드의 데이터 소스이자 llm-wiki의 raw source가 된다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class JsonlEventLog:
    def __init__(self, path: Path | str, source: str):
        self.path = Path(path)
        self.source = source
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, payload: dict) -> None:
        record = {
            "ts": datetime.now().isoformat(),
            "source": self.source,
            "type": event_type,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
