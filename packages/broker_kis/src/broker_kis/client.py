"""KIS REST 저수준 클라이언트.

- tr_id 자동 변환: 모의투자에서 실전 tr_id(T/J/C 시작)를 V로 치환 (공식 샘플과 동일)
- 레이트리밋: 실전 초당 20건 → 0.05s, 모의 초당 2건 → 0.5s 간격 유지
- rt_cd != "0" 이면 KISApiError raise (호출부에서 빈 DataFrame 대신 예외로 처리)
"""

from __future__ import annotations

import time as time_module

import requests

from .auth import TokenManager
from .config import KISSettings


class KISApiError(Exception):
    def __init__(self, message: str, code: str = "", http_status: int = 0):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


RATE_LIMIT_CODE = "EGW00201"  # 초당 거래건수 초과


class KISClient:
    def __init__(self, settings: KISSettings, token_manager: TokenManager | None = None):
        self.settings = settings
        self.tokens = token_manager or TokenManager(settings)
        self._session = requests.Session()
        self._min_interval = 0.6 if settings.is_paper else 0.05
        self._last_request_at = 0.0

    def request(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: dict | None = None,
        body: dict | None = None,
        tr_cont: str = "",
        _retries: int = 3,
    ) -> dict:
        """레이트리밋(EGW00201) 시 백오프 후 최대 _retries회 재시도."""
        for attempt in range(_retries + 1):
            try:
                return self._request_once(method, path, tr_id, params, body, tr_cont)
            except KISApiError as e:
                is_rate_limit = e.code == RATE_LIMIT_CODE or RATE_LIMIT_CODE in str(e)
                if not is_rate_limit or attempt >= _retries:
                    raise
                time_module.sleep(1.0 * (attempt + 1))

    def _request_once(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: dict | None = None,
        body: dict | None = None,
        tr_cont: str = "",
    ) -> dict:
        self._throttle()

        # 모의투자 tr_id 치환 (실전 전용 TR은 그대로 → 서버가 에러 반환)
        if self.settings.is_paper and tr_id[0] in ("T", "J", "C"):
            tr_id = "V" + tr_id[1:]

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.settings.user_agent,
            "authorization": f"Bearer {self.tokens.get_token()}",
            "appkey": self.settings.app_key,
            "appsecret": self.settings.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "tr_cont": tr_cont,
        }

        url = f"{self.settings.base_url}{path}"
        if method == "GET":
            res = self._session.get(url, headers=headers, params=params, timeout=10)
        else:
            res = self._session.post(url, headers=headers, json=body, timeout=10)

        if res.status_code != 200:
            raise KISApiError(
                f"HTTP {res.status_code} {path} [{tr_id}]: {res.text[:300]}",
                http_status=res.status_code,
            )

        data = res.json()
        if data.get("rt_cd") != "0":
            raise KISApiError(
                f"{path} [{tr_id}] {data.get('msg_cd', '')}: {data.get('msg1', '')}",
                code=data.get("msg_cd", ""),
            )
        return data

    def get(self, path: str, tr_id: str, params: dict, tr_cont: str = "") -> dict:
        return self.request("GET", path, tr_id, params=params, tr_cont=tr_cont)

    def post(self, path: str, tr_id: str, body: dict) -> dict:
        return self.request("POST", path, tr_id, body=body)

    def _throttle(self) -> None:
        elapsed = time_module.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time_module.sleep(self._min_interval - elapsed)
        self._last_request_at = time_module.monotonic()
