---
name: upbit-api-notes
scope: shared
updated: 2026-07-27
sources:
  - https://docs.upbit.com/kr/reference/auth
  - https://docs.upbit.com/kr/reference/rate-limits
  - packages/broker_upbit (구현·검증)
---

# 업비트 Open API 주의사항

## 인증 (KIS와 완전히 다름)

KIS는 토큰 발급 후 재사용이지만, 업비트는 **요청마다 JWT를 새로 만든다**.

```
payload = {access_key, nonce(매 요청 새 UUID)}
파라미터가 있으면: + query_hash = SHA512(인코딩 안 한 쿼리스트링), query_hash_alg="SHA512"
서명: HS512 (secret_key)
헤더: Authorization: Bearer <JWT>
```

- **POST도 body를 쿼리스트링 형태로 변환해 해시**한다 (JSON 그대로가 아님)
- 배열 파라미터는 `states[]=wait&states[]=watch` 형태 유지 (urlencode `doseq=True`)
- 토큰 캐시 개념이 없으므로 KIS의 TokenManager 같은 장치가 불필요

## 레이트리밋 (그룹별로 따로 관리)

| 그룹 | 한도 | 대상 |
|---|---|---|
| 시세(quotation) | **10/초** (IP 기준) | ticker, candle, orderbook, trade, market |
| default | **30/초** (계정 기준) | 잔고·주문조회 등 |
| order | **8/초** | 주문 생성 |
| order-cancel-all | 1회/2초 | 일괄 취소 |
| websocket-connect | 5/초 | 연결 |
| websocket-message | 5/초 + 100/분 | 연결당 |

- 초과 시 **429**, 반복 위반 시 **418(일시 차단)** → 클라이언트에 백오프 재시도 구현됨
- 그룹이 분리돼 있으므로 시세 폴링과 주문이 서로의 한도를 잡아먹지 않는다 (KIS는 단일 20/초 공유)

## 시장 규칙 (주식과의 결정적 차이)

| 항목 | 업비트 | KIS(국내주식) |
|---|---|---|
| 거래시간 | **24시간 365일** | 09:00~15:30 |
| **거래세** | **0%** | 매도 시 0.18% |
| 수수료 | 0.05% (KRW 마켓) | ~0.015% |
| **왕복 총비용** | **~0.1%** | **~0.31%** |
| 수량 단위 | 소수점 8자리 | 1주 |
| 최소 주문 | 5,000원 | 없음 |
| 모의투자 | **없음** ★ | 있음 |

**단타 관점의 함의**: 왕복비용이 주식의 **1/3**이다. 주식에서 과다거래(연 800~1,100회)로
전멸했던 전략들이 코인에서는 성립할 여지가 있다 → [[timeframe-comparison]]의 비용 잠식 결론을
코인에 그대로 적용하면 안 된다.

**안전 관점의 함의**: 모의투자 환경이 없어 **실계좌 키 하나뿐**이다.
DryRunBroker(로컬 모의체결)가 KIS보다 훨씬 중요하며, `--live` 게이트가 유일한 방어선이다.

## 구현 시 함정

- **캔들 응답이 최신순**이다 → 오름차순 정렬 필수 (구현에 반영됨)
- 캔들 1콜 최대 **200건**, 과거는 `to` 파라미터로 이어붙임
- **시장가 매수는 금액(price) 지정**, 시장가 매도는 수량(volume) 지정 — 파라미터가 비대칭
- 지정가는 **호가단위 정렬 필수** (구간별 tick: 2백만↑ 1000원 … 1원 미만 0.0001)
- 심볼 형식은 `KRW-BTC` (마켓-코인)
- KRW 마켓 종목 수가 많다(2026-07 기준 **272개**) → 유니버스 선별 기준이 주식보다 중요

## 검증 기록 (2026-07-27)

공개 API 전부 정상: KRW 마켓 272종, BTC 현재가/일봉/5분봉 조회 OK.
인증 API(잔고)는 키 입력 후 검증 예정.

관련: [[kis-api-notes]]

## 개별 주문 조회 (GET /v1/order) — 파라미터 있는 프라이빗 GET (2026-07-28)

- `client.get`은 기본 `auth=False` — 프라이빗 GET은 **반드시 `auth=True`** (JWT에
  query_hash 포함). 빠뜨리면 401 "Please check Authorization Header" (404가 아님!).
- 체결 확인: `trades[]`의 funds/volume 가중평균이 실체결가. `state`: wait/done/cancel.
  시장가는 보통 즉시 done. 그룹은 default(30/s) — order 그룹(8/s) 아님.
