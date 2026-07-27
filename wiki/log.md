# Wiki Log

> append-only. 형식: `## [YYYY-MM-DD] ingest|query|lint | 제목`

## [2026-07-23] ingest | 프로젝트 초기화 + KIS API 분석

- `../open-trading-api` 공식 샘플 분석 → [[kis-api-notes]] 생성
- 모노레포 뼈대 구축 (core / broker_kis / bot_scalper) → [[scalper-overview]] 생성
- 아키텍처 결정: 모노레포(위키 포함, 비대해지면 submodule 분리), 정책 pull 기반, 기본 dry-run

## [2026-07-23] ingest | KIS 실전·모의 인증/조회 검증 완료

- 실전·모의 양쪽 인증, 시세, 일봉, ETF NAV, 잔고 조회 전부 통과 (scripts/smoke_kis.py)
- 모의 레이트리밋이 HTTP 500 + EGW00201로 반환되는 것 발견 → 클라이언트에 백오프 재시도 추가 → [[kis-api-notes]] 갱신
- ETF봇 전략 확정: NAV 괴리율 평균회귀. 다음 단계 = 괴리율 과거 데이터 수집·엣지 분석

## [2026-07-26] ingest | KIS API 카탈로그 자동 생성 (334개)

- scripts/gen_kis_api_catalog.py 작성 — 샘플 저장소 AST 파싱으로 함수 원형·tr_id·URL 추출
- wiki/shared/brokers/kis/api/ 에 카테고리별 8개 문서 + [[kis-api-catalog]] 총람 생성
- 발견: 일별 NAV비교추이는 날짜범위 지정 가능(과거 이력 OK), 분별은 당일만 — 괴리율 수집기 필요성 재확인

## [2026-07-26] pivot | ETF NAV 괴리율 전략 폐기 → 기술적 전략 라이브러리로 방향 전환

- ETF 괴리율 평균회귀 전략 중단 (코드화 전 단계라 삭제 영향 적음). smoke_kis.py의 ETF 조회, wiki의 ETF봇 참조 제거
- 새 방향: 유튜브 등에서 검증된 기술적 전략 20~30종 조사 → 수치화된 진입/청산 규칙으로 프로그램화
  → 장세(레짐)·종목별로 우세 전략을 판별해 매매. 전략은 모듈(진입/필터/청산/포지션관리)로 분해, 멀티타임프레임 지원
- KIS 카탈로그(etfetn.md 등)는 전체 API 참조이므로 유지

## [2026-07-26] ingest | 전략 프레임워크 구축 (indicators / strategy_kit / backtest)

- 신규 패키지 3종: indicators(지표 12종), strategy_kit(진입6/필터4/청산5/사이징2 + CompositeStrategy + 레지스트리), backtest(MTF·look-ahead 안전 엔진)
- 시드 프리셋 6종 등재(배관 검증용). 005930/000660 3년 일봉 백테스트 → 추세계 우세 확인 → [[strategy-framework]]
- 다음: 유튜브 전략 조사(/watch) → 수치화 → 게이트 → 등재 반복

## [2026-07-26] ingest | 유니버스 37종목 × 3구간 백테스트 + 벤치마크 방법론 개정

- 사용자 지적("삼전 3년 들고 있었으면 더 벌었다")이 맞음 → 리포트에 B&H 벤치마크·노출%·비중% 추가, 게이트 기준 개정
- 37종목 × 6전략 × 3구간(하락/횡보/상승) 실행 → [[regime-strategy-observations]]:
  하락장 방어(31/35 B&H 승), 횡보=평균회귀 우세, 상승=모멘텀 우세하나 B&H 열세(노출 부족)
- 포트폴리오 백테스터(PortfolioBacktester) 추가 — 공유 자본·최대 N포지션·동일가중 B&H 벤치마크
- 일봉 캐시 구축: data/cache/daily/ 37종목 × 2021~2026 (재실행 시 API 호출 없음)
- 포트폴리오 백테스트 결과: 시드 6종 전부 게이트 탈락 (최고 +7.0% vs 벤치 +133.7%).
  원인 = 레짐 무관 상시 가동 + 거래비용 잠식 + 저품질 신호 집행 → 다음 검증은 레짐 스위칭 포트폴리오

## [2026-07-26] ingest | 레짐 스위칭 검증 — 아키텍처 핵심 가설 입증 (상한선)

- ScheduledStrategy(기간별 전략 스위칭 메타전략) 추가 — Commander의 백테스트 대응물
- 하락→현금/횡보→평균회귀/상승→모멘텀: +82.5%, MDD 16.2% (상시가동 최고 +7.0%/MDD45, B&H +133.7%/MDD33)
- 리스크 조정수익은 B&H 상회 (5.1 vs 4.1). 하락장 회피가 최대 기여, 레짐 매칭이 3배 증폭
- 한계 명시: 사후 라벨(상한선) + 매핑 선택 편향 → packages/regime(실시간 판별)로 재검증이 다음 단계

## [2026-07-27] ingest | packages/regime v1 + 실시간 스위칭 검증

- RegimeClassifier v1 (규칙 기반 + 히스테리시스 5일), KISBroker.get_index_daily_candles 추가
- 발견: 지수 일봉 API(FHKUP03500100)는 1콜 최대 50건 (종목 100건과 다름) → [[kis-api-notes]] 갱신 필요
- 실시간 판별 스위칭: +48.9%/MDD 27.1% — 상한선의 59% 보존, 상시가동 대비 7배 → [[regime-strategy-observations]]
- 결론: 아키텍처 실증 완료. 다음 병목은 전략 풀 품질 (시드 6종 전부 게이트 탈락 상태)

## [2026-07-27] ingest | 전략 조사 1차 (문헌 4 + 유튜브 5) → 게이트 → 매핑 갱신

- 수집: 웹검색 + 유튜브 자막(yt-dlp) 3편 분석 (골드핑거 DBB/RSI-BB, MACD+RSI, RSI 시그널크로스).
  수치화 가능 9종 프리셋 등재, 비공개 지표·애매 규칙 7종 탈락 → [[strategy-candidates]]
- 게이트 결과: connors_rsi2(횡보), macd_trend_mtf(상승), turtle_20_10(상승 백업) 통과 → 전략 페이지 생성
- 실시간 스위칭 최고 갱신: 현금/connors/macd = +58.2%, MDD 21.7%, PF 1.63 (기존 +48.9%)
- 핵심 교훈: 세그먼트 1위(yt_rsi_50_trend)가 실시간에서 붕괴 — 게이트에 '실시간 스위칭 강건성' 추가
- 신규 모듈: rsi_below/bb_zone/rsi_bb_breakout/rsi_signal_cross 진입, donchian/above_ma/bb_band/rsi_bb/rsi_level/rsi_above 청산, roc 필터

## [2026-07-27] ingest | 전략 조사 2차 (유튜브 4편) — 통과 0건

- 일목균형표 2편 + 세력거래량 + 눌림목/돌파 강의 자막 분석 → 구현 가능 3종 등재, 게이트 전부 탈락/보류
- 신규 자산: ichimoku 지표(indicators), ichimoku_bounce/box_breakout 진입, ichimoku 청산, ma_compare 필터 (모듈은 재사용 가능)
- 관측: 유튜브 전략의 게이트 생존율이 매우 낮음 (2차 누적: 후보 18개 시도 → 통과 3개, 유튜브발 0개).
  비공개 지표 마케팅 비중 높음 → [[strategy-candidates]]

## [2026-07-27] ingest | 미국장 선행 효과 검증 → 쇼크일 필터로 성과 갱신

- 가설 "미국장 좋으면 선제 매수" 검증: 갭 상관 +0.53 / 장중 상관 +0.01 → **알파 기각** (전량 시가 반영)
- 발견: 나스닥 양극단(|야간|≥2%) 다음 날 장중이 방향 불문 음수 (갭 페이드 + 공포 지속)
- 쇼크일 진입 차단 필터 백테스트: **+58.2% → +68.3%, MDD 21.7→20.3, PF 1.63→1.82** (양방향 차단 채택)
- 신규: 해외지수 수집(COMP/SPX/NDX 코드 확인), EntryBlockedDatesStrategy, scripts/us_lead_analysis.py → [[us-lead-effect]]
- Commander 함의: 나스닥 야간 수익률 = 아침 정책(trading_enabled)의 검증된 입력

## [2026-07-27] ingest | 100만원 소액 계좌 운용 설정 확정

- 실계좌 100만원 시작 결정 → 계좌 크기별 백테스트: ATR 사이징이 소액에서 수량 0 다발 (노출 17%, +12%)
- 소액 사이징(슬롯예산 고정비율) 도입 → **4슬롯 +44.1% / MDD 27.3 / PF 1.82** (대형 계좌와 PF 동일) 채택
- scan_today.py: 오늘의 봇 판단 스캔 (레짐→US필터→진입신호). 첫 실행: BULL, 필터 통과, 신호 0건 (정상)
- 다음: 스윙봇 앱 구현 → 모의투자 dry-run

## [2026-07-27] ingest | 대시보드 + 스윙봇 가동 개시

- 이벤트 스키마 확정: entry/exit(pnl·win·reasons)/equity — 봇보다 먼저 확정해 스윙봇이 처음부터 준수
- apps/dashboard: 이벤트 → self-contained HTML (승률·총/주간/월간/연간 수익률·거래 사유 테이블·자산곡선/월간 차트)
- apps/bot_swing 가동: 하루 1회 사이클(레짐→US필터→청산→진입→이벤트), 포지션 파일 영속화
- 첫 사이클(2026-07-27): BULL/macd, 나스닥 -0.64% 정상, 신호 0건, 자산 100만 무변동 — 정상 동작 확인
- 분봉 수집: 초기 백필 진행 중 (완료 후 매일 증분 ~480콜)

## [2026-07-27] ingest | 60분봉 vs 일봉 비교 (17종목, 1년)

- 분봉 캐시 → 60분봉 리샘플 백테스트 (scripts/backtest_60m.py)
- 결과 분기: 평균회귀 붕괴(connors +0.30→-3.71), 추세추종 개선(macd +2.23→+5.10) → [[timeframe-comparison]]
- 원인: 거래당 기대폭 차이. 평균회귀는 목표가 작아 비용에 잠식, 추세추종은 이익을 길게 끌어 내성
- 공통 대가: 승률 50%→35~40%, MDD 1.5~3배
- 스크립트 버그 교훈: 상위TF를 W→D로 바꿀 때 **필터 모듈의 tf 파라미터도 함께** 치환해야 함
  (설정만 바꾸면 필터가 데이터를 못 찾아 전량 차단 → 거래 0건이 '결과'로 보임)
- 한계: 1년·강세장 단일 레짐, 17종목, 장중 현실성(호가단위·단일가) 미반영

## [2026-07-27] ingest | 전략 조사 3차 (문헌 5종) — 챔피언 교체 없음

- 신규 등재: double_seven, ibs_reversion, three_day_reversion, minervini_breakout, clenow_momentum
- 신규 지표: IBS(봉내 종가 위치), Clenow 모멘텀(연율 지수회귀 기울기×R²)
- 신규 모듈: n_day_low/ibs_below/consecutive_down 진입, n_day_high/ibs_above 청산, minervini/clenow 필터
- 게이트: ibs_reversion·double_seven 탈락(과다거래 비용잠식), three_day_reversion 보류(스위칭 66.6 vs 챔피언 68.3)
- **미국 시장 전략의 이식 한계 관측**: Minervini(7조건)·Clenow(회귀 모멘텀)는 코스피 대형주에서
  신호가 거의 발생하지 않음(거래 5~81회) → 유니버스 확대 또는 한국 시장 맞춤 임계값이 선결 과제
- 누적 통계: 후보 23개 등재 → 게이트 통과 3개 (문헌 2 + 시드 1), 유튜브발 0개 → [[strategy-candidates]]
