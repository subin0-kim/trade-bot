---
name: turtle-20-10
scope: shared
updated: 2026-07-27
sources:
  - "Curtis Faith, 'Way of the Turtle' (2007) — Richard Dennis 터틀 System 1"
  - data/reports/universe_backtest.json (2026-07-27)
---

# 터틀 20/10 돌파 — 상승장 추세추종

## 가설

신고가 돌파는 정보 반영의 시작이며, 추세는 관성을 가진다.
돌파로 진입하고 반대 신호(10일 저점 이탈)까지 추세에 올라탄다. 손실은 짧게, 이익은 길게.

## 원 출처

Richard Dennis & William Eckhardt의 터틀 트레이딩 실험 (1983), System 1 규칙.
문서화: Curtis Faith, *Way of the Turtle* (2007). 원전: 20일 돌파 진입 / 10일 반대 돌파 청산 /
2N(ATR) 리스크 사이징. (원전은 선물·양방향, 여기서는 주식 현물 롱온리 근사)

## 등재 설정 (`turtle_20_10`)

```json
{
  "entry":  {"type": "breakout", "lookback": 20},
  "exits":  [{"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
             {"type": "donchian_exit", "lookback": 10}],
  "sizer":  {"type": "atr_risk", "risk_pct": 1.0, "atr_period": 20, "stop_mult": 2.0}
}
```

## 백테스트 (코스피 37종목, 2021~2026)

| 구간 | 중앙수익 | 수익종목 | MDD(중앙) | 거래 |
|---|---|---|---|---|
| 하락장 | -2.63% | 4/35 | 4.3% | 178 |
| 횡보·회복 | -0.65% | 17/37 | 4.9% | 284 |
| **상승장** | **+2.96%** | **27/37 (73%)** — 전 전략 중 최다 | 4.8% | 235 |

- **상승장 담당으로 게이트 통과** — 수익종목 비율이 가장 높고(73%), 실시간 레짐 스위칭에서
  BULL 슬롯 채택 시 전체 성과 +50.7%/MDD 23.2%로 최고 기록 ([[regime-strategy-observations]])
- 하락장 성적 나쁨 → 반드시 레짐 필터와 함께 운용 (상시 가동 금지)
- 주의: 상승장 세그먼트 중앙값 1위였던 yt_rsi_50_trend는 실시간 판별에서 +26.1%로 붕괴
  (세그먼트 최적화의 과적합) — 터틀은 세그먼트 2위였지만 실시간에서 더 강건했음

## 개정 이력

- 2026-07-27 v1 등재. 원전 System 1 그대로, 손절 6% 안전벨트만 추가
