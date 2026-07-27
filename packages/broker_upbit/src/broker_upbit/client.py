"""업비트 REST 클라이언트 — JWT 인증 + 엔드포인트 그룹별 레이트리밋.

인증(docs.upbit.com/kr/reference/auth):
  payload = {access_key, nonce(UUID)} (+파라미터 있으면 query_hash, query_hash_alg)
  query_hash = SHA512(인코딩 안 한 쿼리스트링)   ※ POST는 body를 쿼리스트링 형태로 변환해 해시
  Authorization: Bearer <HS512로 서명한 JWT>

레이트리밋(docs.upbit.com/kr/reference/rate-limits) — 그룹별로 따로 관리:
  시세(ticker/candle/orderbook/trade/market): 각 10/초 (IP 기준)
  거래 default(잔고·주문조회 등): 30/초 | order(주문): 8/초 | order-cancel-all: 1/2초
  초과 시 429, 반복 위반 시 418(일시 차단) → 백오프 재시도
"""

from __future__ import annotations

import hashlib
import time
import uuid
from urllib.parse import urlencode

import jwt
import requests

from .config import UpbitSettings

# 그룹별 최소 호출 간격(초) — 공식 한도에 안전마진 20% 적용
GROUP_INTERVALS = {
    "quotation": 1 / 8,    # 공식 10/초
    "default": 1 / 24,     # 공식 30/초
    "order": 1 / 6,        # 공식 8/초
    "cancel-all": 2.0,     # 공식 1회/2초
}


class UpbitApiError(Exception):
    def __init__(self, message: str, code: str = "", http_status: int = 0):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class UpbitClient:
    def __init__(self, settings: UpbitSettings | None = None):
        self.settings = settings or UpbitSettings.load()
        self._session = requests.Session()
        self._last_call: dict[str, float] = {}

    # ------------------------------------------------------------------ 인증
    def _auth_header(self, params: dict | None = None) -> dict:
        payload = {
            "access_key": self.settings.access_key,
            "nonce": str(uuid.uuid4()),
        }
        if params:
            # 배열 파라미터는 states[]=wait&states[]=watch 형태여야 하므로 doseq 사용
            query = urlencode(params, doseq=True)
            payload["query_hash"] = hashlib.sha512(query.encode()).hexdigest()
            payload["query_hash_alg"] = "SHA512"
        token = jwt.encode(payload, self.settings.secret_key, algorithm="HS512")
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------ 호출
    def _throttle(self, group: str) -> None:
        interval = GROUP_INTERVALS.get(group, 1 / 8)
        elapsed = time.monotonic() - self._last_call.get(group, 0.0)
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_call[group] = time.monotonic()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        group: str = "quotation",
        auth: bool = False,
        retries: int = 3,
    ):
        url = f"{self.settings.base_url}{path}"
        for attempt in range(retries + 1):
            self._throttle(group)
            headers = {"Accept": "application/json"}
            if auth:
                headers.update(self._auth_header(params))

            if method == "GET":
                res = self._session.get(url, headers=headers, params=params, timeout=10)
            elif method == "DELETE":
                res = self._session.delete(url, headers=headers, params=params, timeout=10)
            else:
                headers["Content-Type"] = "application/json"
                res = self._session.post(url, headers=headers, json=params, timeout=10)

            if res.status_code in (429, 418):  # 레이트리밋 / 일시차단
                if attempt >= retries:
                    raise UpbitApiError(
                        f"레이트리밋 초과({res.status_code}) {path} — 재시도 소진",
                        http_status=res.status_code,
                    )
                time.sleep(1.0 * (attempt + 1))
                continue

            if res.status_code >= 400:
                try:
                    err = res.json().get("error", {})
                    msg, code = err.get("message", res.text[:200]), err.get("name", "")
                except ValueError:
                    msg, code = res.text[:200], ""
                raise UpbitApiError(
                    f"HTTP {res.status_code} {path}: {msg}", code=code, http_status=res.status_code
                )
            return res.json()
        raise UpbitApiError(f"요청 실패: {path}")

    def get(self, path: str, params: dict | None = None, *, group: str = "quotation", auth: bool = False):
        return self.request("GET", path, params=params, group=group, auth=auth)

    def post(self, path: str, params: dict, *, group: str = "order"):
        return self.request("POST", path, params=params, group=group, auth=True)

    def delete(self, path: str, params: dict, *, group: str = "default"):
        return self.request("DELETE", path, params=params, group=group, auth=True)
