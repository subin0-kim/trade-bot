---
name: scalper-overview
scope: scalper
updated: 2026-07-23
sources:
  - apps/bot_scalper (초기 구현)
---

# 단타봇 개요

분봉 기반 데이트레이딩 봇. `apps/bot_scalper`.

## 현재 상태 (2026-07-23)

- 뼈대 완성: 시세 → 시그널 → 정책/리스크 체크 → 주문 → 이벤트 로그 루프
- 전략: `MACrossStrategy` (MA5/MA20 분봉 크로스) — **배관 검증용 샘플, 실전용 아님**
- 실행 모드: `--offline`(가짜 시세) / `--env paper` dry-run / `--env paper --live`(모의투자 실주문)
- 미구현: 당일 실현손익 집계(리스크 엔진의 daily_pnl이 항상 0), 웹소켓 실시간 시세, 장시간 체크

## 결정 이력

- 포지션 크기: 계좌의 5% × aggressiveness (임시 규칙, 백테스트 후 재설계)
- 매도는 전량 매도 (부분 청산 미지원)

## 다음 단계

- KIS 모의투자 계좌로 end-to-end 검증 ([[kis-api-notes]]의 모의투자 제약 주의)
- 전략 백테스트 파이프라인 연결 (open-trading-api backtester 활용 검토)
