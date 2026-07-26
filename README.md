# stock-trade-bot

KIS(한국투자증권) / Upbit 기반 멀티 봇 자동매매 모노레포.

## 구조

| 경로 | 내용 |
|---|---|
| `packages/core` | 도메인 모델, Broker 추상화, DryRunBroker, 리스크/정책 엔진 |
| `packages/broker_kis` | KIS Open API 어댑터 |
| `apps/bot_scalper` | 단타봇 |
| `wiki/` | LLM-wiki (지식 베이스) |

자세한 컨벤션과 아키텍처 원칙은 [CLAUDE.md](CLAUDE.md) 참고.

## 빠른 시작

```bash
uv sync

# API 키 없이 루프 검증 (가짜 시세)
uv run bot-scalper --offline --cycles 50

# 모의투자 시세 + 로컬 모의체결 (D:/kis/config/kis_devlp.yaml 필요)
uv run bot-scalper --env paper --once
```

`--live` 플래그 없이는 어떤 경우에도 실제 주문이 나가지 않습니다.
