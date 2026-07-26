# stock-trade-bot — 멀티 봇 자동매매 모노레포

## 프로젝트 개요

한국투자증권(KIS) / 업비트 API 기반 자동매매 봇 모음. uv workspace 모노레포.

- `packages/core` (`trading_core`): 브로커 비종속 도메인 모델, Broker Protocol, DryRunBroker, 리스크 엔진, 정책, 이벤트 로그
- `packages/broker_kis` (`broker_kis`): KIS Open API 어댑터
- `packages/indicators` (`indicators`): 기술적 지표 (시리즈 정렬 반환, float)
- `packages/strategy_kit` (`strategy_kit`): 전략 모듈 분해 — Entry/Filter/Exit/Sizing 조립식. 전략 정의는 `registry.PRESETS` 설정 dict
- `packages/backtest` (`backtest`): 백테스트 엔진 3종 — 단일종목/포트폴리오/레짐스위칭 (MTF 완성봉만 노출, 다음 봉 시가 체결, 비용 모델)
- `packages/regime` (`regime`): 시장 레짐 판별 (KOSPI 지수 → bull/bear/sideways, 히스테리시스)
- `apps/bot_scalper`: 단타봇 (분봉 기반)
- 예정: `apps/bot_swing` (1~2주 스윙), `apps/commander` (레짐 판별 → 우세 전략 선택 → 정책 발행), `apps/dashboard`, `packages/broker_upbit`
- `wiki/`: LLM-wiki (아래 스키마 참고)
- `data/`: 런타임 산출물 (이벤트 JSONL, 정책 파일) — gitignore됨

참고 자료: `../open-trading-api` (KIS 공식 샘플. API 스펙 확인은 `examples_llm/<카테고리>/<기능>/` 참조)

## 아키텍처 원칙

1. **봇 앱은 전략 로직만** — 주문 실행·리스크·로깅은 core가 담당. 새 봇 = 전략 클래스 + 설정.
2. **기본은 dry-run** — `--live` 플래그 없이는 절대 실주문이 나가지 않는다. 실전(`--env real --live`)은 확인 프롬프트 필수.
3. **리스크 하드리밋은 정책과 별개** — Commander의 어떤 정책도 `RiskLimits`를 완화할 수 없다.
4. **정책은 pull 기반** — 봇이 `data/policies/<bot>.json`을 읽는다. 만료/파손 시 보수 모드. (Commander 가동 전에는 파일 없음 = 기본 정책)
5. **모든 행동은 이벤트로** — 시그널/주문/체결/차단을 `data/events/<bot>.jsonl`에 append. 대시보드와 wiki ingest의 데이터 소스.
6. **금액·수량은 Decimal** — float 금지 (코인 소수점 대비).
7. **공통 인터페이스는 최소로** — 브로커 고유 기능(조건부지정가 등)은 어댑터 확장 메서드로. 시장 차이는 `MarketRules` 메타데이터로 노출.
8. **전략은 모듈 조립** — 전략 = Entry+Filter+Exit+Sizing 설정 dict. 신규 전략은 반드시 수치화된 규칙 + 백테스트 게이트 통과 후 등재 (`wiki/shared/strategies/strategy-framework.md`).
9. **백테스트 현실성** — 판단은 봉 종가, 체결은 다음 봉 시가+슬리피지. 상위 TF는 완성봉만 (미래참조 금지).

## 명령어

```bash
uv sync                                    # 전체 워크스페이스 설치
uv run bot-scalper --offline --once        # API 키 없이 루프 검증
uv run bot-scalper --env paper --once      # 모의투자 시세 + dry-run
uv run python scripts/backtest_demo.py --offline           # 합성 데이터 백테스트
uv run python scripts/backtest_demo.py --symbol 005930     # KIS 일봉 백테스트
uv run python scripts/universe_backtest.py                 # 유니버스 37종목 × 3구간 (일봉 캐시 생성)
uv run python scripts/portfolio_backtest.py                # 포트폴리오 백테스트 (캐시 필요)
```

KIS 인증정보는 `D:/kis/config/kis_devlp.yaml` (repo 밖, 공식 샘플과 동일 포맷. `KIS_CONFIG_PATH`로 변경 가능). 토큰 캐시는 `D:/kis/config/tokens/`.

### 환경 주의사항 (Windows + 한글 경로)

- **Python은 3.13 고정** (`.python-version`). 3.11/3.12는 `.pth` 파일을 cp949로 읽어
  한글 경로(`D:\프로젝트\...`)의 venv가 `UnicodeDecodeError`로 기동 실패한다 (3.13에서 UTF-8 읽기로 수정됨).
- 콘솔 한글 출력이 깨지면 `PYTHONUTF8=1` 환경변수 설정.

## LLM-Wiki 스키마 (`wiki/`)

Karpathy llm-wiki 방법론. Raw(불변) → Wiki(LLM 유지) → Schema(이 문서).

### 디렉토리 규칙

- `wiki/shared/` — **봇 경계를 넘는 지식만**: `market-regimes/`(시장 레짐), `brokers/kis/`·`brokers/upbit/`(API quirk), `indicators/`(지표 개념)
- `wiki/bots/<봇이름>/` — 봇 전용: 전략 이력, 성과, 교훈
- `wiki/incidents/` — 장애·실수 기록 (frontmatter로 관련 봇 태깅)
- `wiki/index.md` — 전체 카탈로그 (카테고리별, 한 줄 요약). **모든 ingest 시 갱신**
- `wiki/log.md` — append-only 연대기. `## [YYYY-MM-DD] ingest|query|lint | 제목` 형식

### 페이지 규칙

- frontmatter: `scope: shared | scalper | swing | commander | ...`, `updated: YYYY-MM-DD`, `sources:` (raw 출처)
- 크로스링크는 `[[페이지명]]`
- 배치 기준: **"이 지식이 다른 봇에도 참인가?"** → yes면 `shared/`, no면 `bots/<이름>/`. 애매하면 `bots/`에 두고 lint 때 승격 검토

### 운영

- **Ingest**: 새 지식(거래 로그 분석, 장애, API 발견사항, 백테스트 결과) 발생 시 관련 페이지 갱신 + index.md + log.md
- **Lint**: 주기적으로 모순·낡은 정보·고아 페이지·승격 후보 점검
- Raw 소스: `data/events/*.jsonl`(거래 이벤트), 백테스트 리포트, 리서치 노트(`raw/`)

## 코딩 컨벤션

- Python 3.11+, 타입 힌트 필수, 한국어 주석/docstring
- 패키지 간 의존 방향: apps → packages, broker_* → core (역방향 금지)
- KIS API 추가 시: `../open-trading-api/examples_llm/`에서 스펙(tr_id, 파라미터) 확인 후 구현, 특이사항은 `wiki/shared/brokers/kis/`에 기록
