---
name: kis-api-notes
scope: shared
updated: 2026-07-23
sources:
  - ../open-trading-api (공식 샘플 분석, 2026-07-23)
---

# KIS Open API 주의사항

`broker_kis` 구현 시 확인된 사실. 새 API 추가 시 여기에 누적한다.

## 인증

- 접근토큰: 유효 24h, **발급 1분당 1회 제한**, 6시간 내 재요청 시 동일 토큰 반환. 발급 시마다 알림톡 발송됨 → 파일 캐시 필수 (`TokenManager`)
- 웹소켓은 별도 approval_key 발급 (`/oauth2/Approval`) — 아직 미구현

## tr_id 규칙

- 실전 tr_id 첫 글자가 `T`/`J`/`C`면 모의투자에서는 `V`로 치환 (예: TTTC0012U → VTTC0012U)
- 시세 조회 계열(FHK...)은 실전/모의 동일
- 주요 tr_id: 현재가 FHKST01010100 / 일봉 FHKST03010100 / 분봉 FHKST03010200 / 매수 TTTC0012U / 매도 TTTC0011U / 정정취소 TTTC0013U / 잔고 TTTC8434R / 미체결조회 TTTC0084R

## 제약·함정

- **POST body 키는 대문자** (`"CANO"`, `"ORD_QTY"` …), 수량·단가는 **문자열**로 전달
- 모의투자 레이트리밋이 실전보다 낮음 (초당 2건 수준) → 클라이언트 0.6s 스로틀 + EGW00201 백오프 재시도 구현됨.
  **주의: 레이트리밋 초과가 HTTP 500으로 반환됨** (body에 EGW00201) — HTTP 에러도 재시도 대상에 포함해야 함
- **미체결 조회(TTTC0084R)는 모의투자 미지원** — 모의에서 get_open_orders 호출 시 에러 예상
- 분봉 조회는 1회 최대 30건 (FID_INPUT_HOUR_1 기준 직전 30개), 당일만 가능
- 일봉 조회는 1회 최대 100건, `FID_ORG_ADJ_PRC=0`이 수정주가
- **지수 일봉(FHKUP03500100)은 1회 최대 50건** (종목의 100건과 다름) — 구간 내 최신 50개만 반환하므로 65일 윈도로 분할 조회할 것
- 취소 주문에는 원주문의 `KRX_FWDG_ORD_ORGNO`(주문채번지점번호) 필요 → 주문 시 meta에 보관
- 잔고 조회 output2: `dnca_tot_amt` 예수금, `prvs_rcdl_excc_amt` D+2 예수금(주문가능 기준), `tot_evlu_amt` 총평가
- NXT(대체거래소) 지원으로 시장분류코드가 J(KRX)/NX(NXT)/UN(통합)으로 나뉨 — 현재 J만 사용

## 휴장일 조회 (CTCA0903R) — 모의서버 미지원 (2026-07-28)

- `chk-holiday`(국내휴장일조회)는 **모의투자 서버에서 "없는 서비스 코드"(OPSQ0002)** —
  원장 연동 API라 실전 전용. 봇이 paper 환경이어도 휴장일 확인은 실전 서버로 해야 한다
  (시세성 read-only라 주문과 무관).
- 공식 가이드가 **1일 1회 호출 권고** (원장 부하) → `bot_swing.holiday`가
  `data/cache/kis_holiday.json`에 일 단위 캐시. 주말은 API 없이 로컬 판정.
- 실패 시 fail-open(개장일 간주): 휴장일 오판으로 하루를 건너뛰는 것보다
  돌았다가 주문 거부되는 쪽이 덜 해롭다.
