"""KIS 접근토큰 관리.

- 토큰 유효기간 24시간, 발급은 1분당 1회 제한 (6시간 내 재요청 시 동일 토큰 반환)
- 파일 캐시로 프로세스 재시작 간 토큰 재사용 (봇 여러 개가 같은 캐시 공유)
- 공식 샘플 kis_auth.py의 전역 상태 방식 대신 인스턴스 기반으로 재구성
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

from .config import KISSettings

def _default_cache_dir(settings: KISSettings) -> Path:
    """토큰 캐시 기본 경로 — OS 무관하게 동작하도록 우선순위 결정:
    ① KIS_TOKEN_CACHE_DIR 환경변수 ② 설정 yaml 옆의 tokens/ ③ ~/.kis/tokens
    (과거 하드코딩 D:/kis/config/tokens는 ②로 자연 대체 — yaml이 D:/kis/config에 있으므로)"""
    env_dir = os.environ.get("KIS_TOKEN_CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    if settings.config_path is not None:
        return settings.config_path.parent / "tokens"
    return Path.home() / ".kis" / "tokens"


class KISAuthError(Exception):
    pass


class TokenManager:
    def __init__(self, settings: KISSettings, cache_dir: Path | None = None):
        self.settings = settings
        self._cache_dir = cache_dir or _default_cache_dir(settings)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        # 환경+앱키별 캐시 분리 (실전/모의 토큰이 섞이지 않게)
        self._cache_file = self._cache_dir / f"token_{settings.env}_{settings.app_key[:8]}.json"
        self._token: str | None = None
        self._expires_at: datetime | None = None

    def get_token(self) -> str:
        if self._token and self._expires_at and datetime.now() < self._expires_at:
            return self._token
        if self._load_cache():
            return self._token
        return self._issue()

    def _load_cache(self) -> bool:
        try:
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(data["expires_at"])
            # 만료 5분 전부터는 재발급
            if datetime.now() < expires_at - timedelta(minutes=5):
                self._token = data["token"]
                self._expires_at = expires_at
                return True
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
            pass
        return False

    def _issue(self) -> str:
        res = requests.post(
            f"{self.settings.base_url}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.settings.app_key,
                "appsecret": self.settings.app_secret,
            },
            headers={"Content-Type": "application/json", "User-Agent": self.settings.user_agent},
            timeout=10,
        )
        if res.status_code != 200:
            raise KISAuthError(f"토큰 발급 실패 ({res.status_code}): {res.text}")

        body = res.json()
        self._token = body["access_token"]
        self._expires_at = datetime.strptime(
            body["access_token_token_expired"], "%Y-%m-%d %H:%M:%S"
        )
        self._cache_file.write_text(
            json.dumps({"token": self._token, "expires_at": self._expires_at.isoformat()}),
            encoding="utf-8",
        )
        return self._token
