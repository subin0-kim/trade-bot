---
name: strategy-candidates
scope: shared
updated: 2026-07-27
sources:
  - 웹 검색 + 유튜브 자막 분석 (yt-dlp 자동자막, 2026-07-27)
  - 문헌: Connors, 터틀, George&Hwang, Antonacci
---

# 전략 후보 조사 (2026-07 1차)

수집 → 수치화 → 게이트 순. **게이트 결과가 나오기 전까지는 전부 '후보'다.**

## 문헌 전략 (수치화 완료, 프리셋 등재)

| 프리셋 | 규칙 요약 | 원 출처 |
|---|---|---|
| `connors_rsi2` | RSI(2)<10 & 200일선 위 매수 → MA5 복귀 청산 | Connors & Alvarez, *Short Term Trading Strategies That Work* (2008) |
| `turtle_20_10` | 20일 신고가 돌파 매수 → 10일 저점 청산, 2N 리스크 | Richard Dennis 터틀 System 1 (Curtis Faith, *Way of the Turtle*) |
| `high_52w_momo` | 52주 신고가 돌파 + 거래량 → ATR 트레일링 | George & Hwang, *The 52-Week High and Momentum Investing* (J. Finance 2004) |
| `abs_momentum` | 6개월 ROC>0 필터 + MA20/60 골든크로스 | Gary Antonacci, *Dual Momentum Investing* (2014)의 일봉 근사 |

## 유튜브 전략 (자막 분석으로 수치화, 프리셋 등재)

| 프리셋 | 규칙 요약 | 원 출처 영상 |
|---|---|---|
| `dbb_kathy` | 더블 볼린저: 종가가 +1σ 매수존 진입 시 매수, 이탈 시 청산 | 골드핑거 "볼린저밴드에 RSI 하나만 섞으세요" — youtube.com/watch?v=9ewMLrv95io (원전: Kathy Lien DBB) |
| `rsi_bb_gold` | RSI(14) 위에 BB(30,2σ): RSI가 RSI-BB 상단 돌파 + 50일선 위 | 같은 영상 (9ewMLrv95io) |
| `yt_rsi_30_70` | RSI 30 상향돌파 매수 → 70 하향이탈 매도 | "고수들만 몰래 쓰는 MACD+RSI" — youtube.com/watch?v=TWO4NeDg6O4 |
| `yt_rsi_50_trend` | RSI 50선 상향돌파 매수 / 하향이탈 매도 | 같은 영상 (TWO4NeDg6O4) |
| `yt_rsi_sigcross` | RSI-시그널 골든크로스(시그널≤40) → RSI60 익절 | "RSI 지표를 활용한 핵심 매매법" — youtube.com/watch?v=WlUSq19j1Rk (원전 크립토 15분봉 → 일봉 근사) |

## 2차 조사 (2026-07-27): 유튜브 4편 추가 분석

| 프리셋 | 규칙 요약 | 원 출처 영상 | 게이트 판정 |
|---|---|---|---|
| `ichimoku_cloud_bounce` | 일목 양운 터치 + 장대양봉 반등 (표준 9/26/52) | "일목균형표 단타매매법" — youtube.com/watch?v=jE54FTenWsw (1시간봉→일봉 근사, '장대'=평균몸통 1.5배 자체정의) | ❌ 탈락 — 전 구간 중앙값 음수 (-0.7~-0.1%) |
| `accum_box_breakout` | 저변동 박스(40봉,15%) + 거래량 위축 후 2.5배 대량거래 돌파 | "세력 거래량 보는법" — youtube.com/watch?v=2fndu2K7Tv0 (파라미터 자체정의) | 보류 — 거래 6~23회로 표본 부족, 박스 조건 완화 후 재검 여지 |
| `staggered_breakout` | 시간차 돌파: 60>120일선 + 60봉 신고가 + 거래량 1.5배 | 같은 영상 (2fndu2K7Tv0) | ❌ 탈락 — 상승장 -0.41%로 기존 슬롯(macd/turtle)에 완패 |

**2차 조사 결론: 신규 게이트 통과 0건.** 기존 매핑(현금/connors/macd) 유지.

2차에서 수치화 불가로 탈락한 것: 수정일목+컬러MA+WTO(zyxon9HCIls — 비공개 지표 3종 마케팅),
자석구름(jE54FTenWsw — 유료 비공개 지표), 세력 거래량 스파이크(진입/청산 미정의 — 스크리너 소재로 보관),
눌림목/돌파 4유형(6YeEtWXzXD8 — 순수 개념 강의, 파라미터 전무).

**보관 소재**: ① 스윙 검색식(2fndu2K7Tv0 — 시총·등락률·수렴·신고가 근접 등 조건 다수가 수치 명시,
청산 없어 스크리너로만), ② '구름 안 종가 3연속 → 청산' 아이디어 (자석구름 영상의 유일한 수치 규칙)

## 조사했으나 탈락 (수치화 불가/재현 불가)

| 후보 | 탈락 사유 | 출처 |
|---|---|---|
| RSI 다이버전스 단독 | 스윙 고점/저점 판정 규칙 미정의 | TWO4NeDg6O4, WlUSq19j1Rk |
| RSI 페일류 + MACD 필터 | "돌파" 기준선 미정의 | TWO4NeDg6O4 |
| RSI50+MACD 0선 2차 매수 | 청산 규칙 부재, "낮은 위치" 미정의 | TWO4NeDg6O4 |
| 맥시밴드 | 자체 지표 계산식 비공개 (마케팅) | WlUSq19j1Rk |
| 마이크로밴드 | 프라이빗 지표, 계산식 비공개 | 9ewMLrv95io |
| Larry Williams 변동성 돌파 | 장중 체결 필요 — 일봉 엔진으로 백테스트 불가 (분봉 엔진 도입 시 재검토) | 문헌 |
| MACD 0선 돌파 스크리너 | 청산 규칙 없음 (종목 발굴용) — 필터 조합 소재로 보관 | TWO4NeDg6O4 |

## 게이트 판정 (2026-07-27, 37종목 × 3구간 + 실시간 레짐 스위칭)

| 후보 | 판정 | 근거 |
|---|---|---|
| `connors_rsi2` | ✅ **통과 — SIDEWAYS 슬롯** | 횡보 중앙 +0.56%, 수익종목 62%, 전 구간 중앙값 비음수 → [[connors-rsi2]] |
| `macd_trend_mtf` | ✅ **통과 — BULL 슬롯** | 실시간 스위칭 최고 조합 (+58.2%/MDD 21.7) |
| `turtle_20_10` | ✅ 통과 — BULL 백업 | 상승장 수익종목 73%(최다), 실시간에서도 강건 → [[turtle-20-10]] |
| `bb_meanrev` | 보류 — SIDEWAYS 백업 | 횡보 2위, connors에 밀림 |
| `yt_rsi_30_70` | 보류 | 하락장 방어(17/35 양수) 특이점 — 하락 레짐 보조 후보로 추가 검증 여지 |
| `high_52w_momo` | 보류 | 거래 수 부족(구간당 8~74회)으로 판정 불가 |
| `yt_rsi_50_trend` | ❌ 탈락 | 세그먼트 1위였으나 실시간 스위칭에서 붕괴(+26.1%) — 과적합 사례로 기록 |
| `dbb_kathy` | ❌ 탈락 | 전 구간 중앙값 음수 + 과다거래(1100회+) 비용 잠식 |
| `rsi_bb_gold` | ❌ 탈락 | 전 구간 중앙값 음수 |
| `yt_rsi_sigcross` | ❌ 탈락 | 전 구간 중앙값 0 이하 |
| `abs_momentum` | ❌ 탈락 | 슬롯 경쟁에서 열세 (상승 +1.35%로 turtle/macd에 밀림) |
| 시드 4종 (ma_trend, breakout_momo, vol_spike_rebound, rsi_rebound) | ❌ 탈락 | 기존 판정 유지 |

## 교훈

- 유튜브 전략의 다수는 "승률 90%+" 류 주장 + 비공개 지표 마케팅. **자막에서 수치 규칙을 추출할 수 있는 것만 후보가 된다**
- 크립토 분봉 전제 전략의 일봉 이식은 근사일 뿐 — 결과 해석 시 감안

관련: [[strategy-framework]], [[regime-strategy-observations]]
