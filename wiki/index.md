# Wiki Index

> 전체 페이지 카탈로그. 모든 ingest 시 이 파일을 갱신한다.

## shared/brokers/kis

- [[kis-api-notes]] — KIS Open API 사용 시 주의사항 (tr_id 규칙, 레이트리밋, 모의투자 제약) (2026-07-23, sources: 1)
- [[kis-api-catalog]] — 전체 334개 API 총람 + 프로젝트 핵심 API 빠른 참조 (2026-07-26, 자동 생성)
- `api/` — 카테고리별 상세 카탈로그 8종: [[kis-api-auth]], [[kis-api-domestic-stock]](156), [[kis-api-etfetn]], [[kis-api-domestic-bond]], [[kis-api-domestic-futureoption]], [[kis-api-overseas-stock]], [[kis-api-overseas-futureoption]], [[kis-api-elw]]

## bots/scalper

- [[scalper-overview]] — 단타봇 개요와 현재 상태 (2026-07-23, sources: 1)

## shared/brokers/upbit

- [[upbit-api-notes]] — JWT 인증, 그룹별 레이트리밋, 주식과의 시장 규칙 차이(거래세 0·24시간·모의투자 없음) (2026-07-27)

## shared/strategies

- [[strategy-framework]] — 전략 모듈 분해 스키마, 등재 게이트, MTF 규칙 (2026-07-26)
- [[strategy-candidates]] — 2026-07 1차 조사: 문헌 4종 + 유튜브 5종 수치화 + 게이트 판정 (2026-07-27)
- [[connors-rsi2]] — ✅ 게이트 통과, SIDEWAYS 슬롯. Connors & Alvarez (2008) (2026-07-27)
- [[turtle-20-10]] — ✅ 게이트 통과, BULL 백업. 터틀 System 1 (2026-07-27)
- [[timeframe-comparison]] — 60분봉 vs 일봉: 평균회귀는 붕괴, 추세추종은 개선 (2026-07-27)
- [[performance-chasing-verdict]] — 성과 추종 스위칭 기각: 순위 자기상관 -0.14, follow_winner가 9정책 중 8위 (2026-07-27)
- [[walkforward-validation]] — 워크포워드 프레임: IS선택/OOS측정 분리. 코인 메이저·알트 모두 OOS 마이너스 (2026-07-27)
- [[crypto-principle-strategies]] — 원리 기반 설계: btc_shock_alt_follow 첫 분할검증 통과, 급등익일 역신호 발견 (2026-07-27)
- [[crypto-backtest-round1]] — 코인 1차(하락장 1년): 방어 압도적(B&H -71.9% vs -4.6%), 게이트 통과 0건, 30분봉<60분봉 (2026-07-27)

## incidents

(없음)

## shared/market-regimes

- [[regime-strategy-observations]] — 레짐 × 전략 1차 관측: 하락=방어, 횡보=평균회귀, 상승=모멘텀+노출 (2026-07-26)
- [[crypto-regime-findings]] — 코인 레짐: 주식 MA설정이 역전 작동, 재보정 필수 (2026-07-27)
- [[us-lead-effect]] — 미국장 선행 효과: 갭 상관 0.53이나 장중 0 → 알파 기각, 쇼크일 방어 필터로 전환 (2026-07-27)
