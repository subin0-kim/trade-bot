---
name: strategy-framework
scope: shared
updated: 2026-07-26
sources:
  - packages/strategy_kit (구현)
  - packages/backtest (검증 엔진)
---

# 전략 프레임워크

모든 전략은 4개 모듈의 조립이다: **Entry(진입) + Filter(필터) + Exit(청산) + Sizing(사이징)**.
전략 정의는 코드가 아니라 **설정(dict)** — `strategy_kit.registry.PRESETS` 참조.

## 등재 파이프라인 (게이트)

```
후보 발굴 (유튜브 /watch 조사, 서적, 논문)
  → 수치화: 진입/청산 규칙을 registry 설정 스키마로 변환
     (수치화 불가능하면 탈락 — "느낌적인" 규칙 금지)
  → KIS 데이터로 계산 가능 검증 (지표가 indicators 패키지에 있는가)
  → 백테스트 게이트: 다종목·다구간에서 성적 확인
  → 생존 시 PRESETS 등재 + 이 폴더에 전략 페이지 작성
```

**게이트 기준(2026-07-26 개정)**:
- 거래 수 ≥ 10 (표본), 여러 종목·여러 구간에서 일관성
- **벤치마크 비교 필수**: 동일 기간 바이앤홀드 대비 리스크 조정 성과(수익/MDD)가 우수할 것
- **구간별 검증**: 상승장만이 아니라 하락·횡보 구간 포함 (전략의 존재 이유는 나쁜 레짐에서의 생존)
- 사후 승자 종목(삼전·하이닉스류)만으로 검증 금지 — 유니버스에 부진 종목 포함

교훈(2026-07-26): 첫 백테스트에서 벤치마크 없이 +26.8%를 "좋은 성적"으로 오독할 뻔함.
같은 기간 바이앤홀드 +234%(삼전). 단 실효 자본투입 ~6% vs 100%, MDD 4.9% vs 43.2%로
단순 수익 비교는 불공정 — 그래서 리포트에 노출%·비중%·벤치마크 열을 추가함.

## 전략 페이지 템플릿

각 전략은 `wiki/shared/strategies/<이름>.md`로 기록:
가설(왜 먹히는가) / 출처(영상 링크 등) / 설정(JSON) / 백테스트 성적 / 적합 레짐 / 개정 이력.

## 사용 가능 모듈 (2026-07-26)

- **Entry**: bollinger_touch, rsi_rebound, ma_cross, breakout, macd_cross, volume_spike_reversal
- **Filter**: adx(min/max), higher_tf_trend(MTF), volume, price_above_ma
- **Exit**: fixed_stop_take, atr_trailing, time_stop, ma_cross_exit, bollinger_mid_exit
- **Sizing**: fixed_fraction, atr_risk
- **지표**: sma, ema, rsi, macd, bollinger, atr, adx, stochastic, roc, rolling_max/min

## 멀티타임프레임 규칙

- 상위 TF는 Filter로 구현 (`higher_tf_trend`) — 방향은 상위, 타이밍은 하위
- **완성봉만 사용**: `resample_progressive`가 보장. 진행 중 봉 참조는 미래참조 버그
- 백테스트 체결은 신호 다음 봉 시가 + 슬리피지 (look-ahead 방지)

## 첫 백테스트 관찰 (2026-07-26, 시드 프리셋 배관 검증)

005930/000660 일봉 3년: 추세 구간이라 추세계(macd_trend_mtf, breakout_momo)가 PF 4~11로 우세,
평균회귀계(bb_meanrev)는 부진. → "레짐별 우세 전략" 가설과 부합. 단 거래 수 5~9회로 표본 부족 —
결론이 아니라 배관 검증. 다종목·다구간 확대 필요.
