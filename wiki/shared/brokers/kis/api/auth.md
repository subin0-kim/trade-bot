---
name: kis-api-auth
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/auth/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 인증 (2개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/auth/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기타

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `auth_token(grant_type, appkey, appsecret, env_dv)` | OAuth 접근토큰 발급 API를 호출하여 DataFrame으로 반환합니다. | - | `/oauth2/tokenP` |
| `auth_ws_token(grant_type, appkey, appsecret, env_dv[, +1 opt])` | WebSocket 웹소켓 접속키 발급 API를 호출하여 DataFrame으로 반환합니다. | - | `/oauth2/Approval` |
