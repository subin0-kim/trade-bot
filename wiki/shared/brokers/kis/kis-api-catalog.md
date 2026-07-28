---
name: kis-api-catalog
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 (총람)

한투 Open API 전체 334개의 함수 원형·설명·tr_id·URL 정리.
`uv run python scripts/gen_kis_api_catalog.py`로 재생성 가능 (샘플 저장소 업데이트 시).

| 카테고리 | 개수 | 문서 |
|---|---|---|
| 인증 | 2 | [[kis-api-auth]] |
| 국내주식 | 156 | [[kis-api-domestic-stock]] |
| ETF/ETN | 6 | [[kis-api-etfetn]] |
| 국내채권 | 18 | [[kis-api-domestic-bond]] |
| 국내선물옵션 | 43 | [[kis-api-domestic-futureoption]] |
| 해외주식 | 50 | [[kis-api-overseas-stock]] |
| 해외선물옵션 | 35 | [[kis-api-overseas-futureoption]] |
| ELW | 24 | [[kis-api-elw]] |

## 우리 프로젝트 핵심 API 빠른 참조

### 시세·차트 (봇 공통)

| 함수 | 용도 | 비고 |
|---|---|---|
| `inquire_price` | 현재가 | 구현됨: `KISBroker.get_quote` |
| `inquire_daily_itemchartprice` | 일/주/월봉 (최대 100건/콜) | 구현됨: `get_daily_candles` |
| `inquire_time_itemchartprice` | 당일 1분봉 (30건/콜) | 구현됨: `get_minute_candles` |
| `inquire_time_dailychartprice` | **과거 1분봉 (최대 1년 보관)** | 백테스트 데이터 소스 |
| `intstock_multprice` | 1콜에 최대 30종목 시세 | 대량 폴링 시 유량 절약 |

### 주문·계좌 (봇 공통)

| 함수 | 용도 | 비고 |
|---|---|---|
| `order_cash` | 현금 매수/매도 | 구현됨: `place_order` |
| `order_rvsecncl` | 정정/취소 | 구현됨: `cancel_order` |
| `inquire_balance` | 잔고+보유종목 | 구현됨: `get_balance`/`get_positions` |
| `inquire_psbl_rvsecncl` | 미체결 조회 | 구현됨 (모의투자 미지원 주의) |
| `inquire_psbl_order` | 매수가능금액 조회 | 미구현 |
| `chk_holiday` | 휴장일 확인 | ✅ 구현 (broker.is_open_day, 모의 미지원 — 실전으로 조회) |

레이트리밋 등 운영 주의사항은 [[kis-api-notes]] 참조.
