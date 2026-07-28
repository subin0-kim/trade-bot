"""휴장일 가드 — 주말은 로컬 판정, 공휴일은 KIS API + 일 단위 캐시.

휴장일에 사이클이 돌면 전 거래일의 낡은 시세로 dry-run 가짜 체결이 기록되어
전방 검증 데이터가 오염된다 (live면 주문 거부로 그나마 무해하지만 무의미).

CTCA0903R은 공식 가이드가 '1일 1회 호출'을 권고하는 원장 연동 API라
결과를 data/cache/kis_holiday.json 에 캐시한다 — 모니터가 30분마다 불러도 API는 하루 1번.

판정 실패(API 장애 등) 시 fail-open: 개장일로 간주하고 경고만 남긴다.
휴장일 오판으로 하루를 통째로 건너뛰는 것보다, 돌았다가 주문 거부되는 쪽이 덜 해롭다.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger("bot_swing.holiday")


def is_trading_day(today: date, cache_dir: Path) -> bool:
    """개장일 여부. CTCA0903R은 모의서버 미지원('없는 서비스 코드')이라
    캐시 미스 시 실전 서버로 조회한다 — 시세성 read-only라 주문과 무관."""
    if today.weekday() >= 5:  # 토/일은 API 없이 확정
        return False
    cache_path = cache_dir / "kis_holiday.json"
    key = today.strftime("%Y%m%d")
    cache: dict[str, bool] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    if key in cache:
        return cache[key]

    try:
        from broker_kis import KISBroker

        open_day = KISBroker(env="real").is_open_day(today)
    except Exception:
        open_day = None
    if open_day is None:
        logger.warning("휴장일 조회 실패 — 개장일로 간주하고 진행 (fail-open)")
        return True
    cache[key] = open_day
    # 캐시는 최근 30일만 유지
    cache = {k: v for k, v in sorted(cache.items())[-30:]}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return open_day
