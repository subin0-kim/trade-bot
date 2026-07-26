---
name: connors-rsi2
scope: shared
updated: 2026-07-27
sources:
  - "Larry Connors & Cesar Alvarez, 'Short Term Trading Strategies That Work' (2008)"
  - data/reports/universe_backtest.json (2026-07-27)
---

# Connors RSI(2) — 횡보장 평균회귀

## 가설

단기 급락(RSI(2)<10)은 장기 상승 추세 안에서는 과잉반응이며 수일 내 되돌아온다.
극단적으로 짧은 RSI(2)가 진입 빈도를, 200일선 필터가 "하락 추세에서 물타기" 함정을 통제.

## 원 출처

Larry Connors & Cesar Alvarez, *Short Term Trading Strategies That Work* (2008).
원전 규칙: 종가 > 200일 SMA & RSI(2) < 10 매수 → 종가 > 5일 SMA 청산 (S&P 종목·ETF 대상 검증).

## 등재 설정 (`connors_rsi2`)

```json
{
  "entry":   {"type": "rsi_below", "period": 2, "threshold": 10},
  "filters": [{"type": "price_above_ma", "period": 200}],
  "exits":   [{"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
              {"type": "above_ma_exit", "period": 5},
              {"type": "time_stop", "max_bars": 10}],
  "sizer":   {"type": "fixed_fraction", "fraction": 0.2}
}
```

## 백테스트 (코스피 37종목, 2021~2026)

| 구간 | 중앙수익 | 수익종목 | MDD(중앙) | 거래 |
|---|---|---|---|---|
| 하락장 | 0.00% | 10/35 | **0.7%** | 111 |
| **횡보·회복** | **+0.56%** | **23/37 (62%)** | 1.9% | 376 |
| 상승장 | +0.35% | 19/37 | 2.8% | 365 |

- **횡보장 담당으로 게이트 통과** — 전 구간에서 유일하게 중앙값 음수가 없는 전략
- 하락장에서 MA200 필터가 진입 자체를 차단 → 사실상 자동 현금화 (MDD 0.7%)
- 레짐 스위칭 매핑에서 SIDEWAYS 슬롯 채택 ([[regime-strategy-observations]])

## 개정 이력

- 2026-07-27 v1 등재. 파라미터는 원전 그대로 (튜닝 없음)
