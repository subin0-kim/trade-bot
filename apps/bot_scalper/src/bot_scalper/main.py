"""단타봇 엔트리포인트.

실행 모드:
  uv run bot-scalper --offline --once          # API 키 없이 가짜 시세로 루프 검증
  uv run bot-scalper --env paper --once        # 모의투자 시세 + 로컬 모의체결(dry-run)
  uv run bot-scalper --env paper --live        # 모의투자 서버에 실제 주문
  uv run bot-scalper --env real --live         # ★ 실전 (충분한 검증 전 금지)

기본값은 항상 dry-run — --live 없이는 어떤 경우에도 실주문이 나가지 않는다.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from decimal import Decimal
from pathlib import Path

from trading_core import (
    DryRunBroker,
    JsonlEventLog,
    OrderRequest,
    OrderType,
    Policy,
    RiskEngine,
    RiskLimits,
    load_policy,
)
from trading_core.testing import FakeBroker

from .strategy import MACrossStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_scalper")

BOT_NAME = "bot-scalper"
# 기본: 실행 위치(repo 루트) 기준 data/. 배포 시 TRADING_DATA_DIR로 재지정
DATA_DIR = Path(os.environ.get("TRADING_DATA_DIR", "data"))
POLICY_PATH = DATA_DIR / "policies" / f"{BOT_NAME}.json"
EVENTS_PATH = DATA_DIR / "events" / f"{BOT_NAME}.jsonl"


def build_broker(args):
    if args.offline:
        data_broker = FakeBroker(seed=args.seed)
        return DryRunBroker(data_broker), data_broker

    from broker_kis import KISBroker

    kis = KISBroker(env=args.env)
    if args.live:
        return kis, None
    return DryRunBroker(kis), None


def run_cycle(broker, strategy, risk, events, symbols, trades_today: int) -> int:
    """1회 사이클: 정책 확인 → 심볼별 시그널 → 리스크 체크 → 주문."""
    # Commander 미가동 단계: 정책 파일 없으면 기본 정책으로 운용
    policy = load_policy(POLICY_PATH, default=Policy(reason="기본 정책 (Commander 미가동)"))
    if not policy.trading_enabled:
        logger.info("정책상 거래 중지: %s", policy.reason)
        events.append("policy_blocked", {"reason": policy.reason})
        return trades_today

    max_trades = policy.max_trades_today or risk.limits.max_trades_per_day

    for symbol in symbols:
        candles = broker.get_minute_candles(symbol)
        signal = strategy.decide(symbol, candles)
        logger.info("[%s] %s (strength=%.2f)", symbol, signal.reason, signal.strength)
        events.append("signal", {
            "symbol": symbol,
            "action": signal.action.value if signal.action else "hold",
            "strength": signal.strength,
            "reason": signal.reason,
            "strategy": strategy.name,
        })

        if not signal.is_actionable or trades_today >= max_trades:
            continue

        quote = broker.get_quote(symbol)
        balance = broker.get_balance()
        positions = broker.get_positions()

        # 포지션 크기: 계좌의 (기본 5% × aggressiveness) — 우선은 단순 규칙
        budget = balance.total_value * Decimal("0.05") * Decimal(str(policy.aggressiveness))
        quantity = budget // quote.price
        if signal.action.value == "sell":
            held = next((p for p in positions if p.symbol == symbol), None)
            if held is None:
                continue
            quantity = held.quantity  # 전량 매도
        if quantity < 1:
            logger.info("[%s] 주문 수량 0 → 스킵 (예산 %s / 현재가 %s)", symbol, budget, quote.price)
            continue

        request = OrderRequest(
            symbol=symbol,
            side=signal.action,
            quantity=Decimal(quantity),
            order_type=OrderType.LIMIT,
            price=quote.price,
        )

        verdict = risk.check(
            request, quote=quote, balance=balance, positions=positions,
            trades_today=trades_today,
            daily_pnl=Decimal(0),  # TODO: 이벤트 로그에서 당일 실현손익 집계
        )
        if not verdict.allowed:
            logger.warning("[%s] 리스크 차단: %s", symbol, verdict.reason)
            events.append("risk_blocked", {"symbol": symbol, "reason": verdict.reason})
            continue

        order = broker.place_order(request)
        trades_today += 1
        logger.info(
            "[%s] 주문 %s: %s %s주 @ %s (status=%s)",
            symbol, order.order_id, order.side.value, order.quantity, order.price, order.status.value,
        )
        events.append("order", {
            "order_id": order.order_id,
            "symbol": symbol,
            "side": order.side.value,
            "quantity": str(order.quantity),
            "price": str(order.price),
            "status": order.status.value,
        })

    return trades_today


def main():
    parser = argparse.ArgumentParser(description="단타봇")
    parser.add_argument("--env", choices=["real", "paper"], default="paper")
    parser.add_argument("--live", action="store_true",
                        help="실제 주문 전송 (없으면 dry-run 모의체결)")
    parser.add_argument("--offline", action="store_true",
                        help="API 키 없이 가짜 시세로 실행")
    parser.add_argument("--symbols", default="005930", help="쉼표 구분 종목코드")
    parser.add_argument("--once", action="store_true", help="1사이클만 실행")
    parser.add_argument("--interval", type=int, default=60, help="사이클 간격(초)")
    parser.add_argument("--cycles", type=int, default=0, help="최대 사이클 수 (0=무한)")
    parser.add_argument("--seed", type=int, default=42, help="offline 모드 시세 시드")
    args = parser.parse_args()

    if args.env == "real" and args.live:
        confirm = input("⚠️  실전 계좌에 실제 주문이 나갑니다. 'yes' 입력 시 진행: ")
        if confirm != "yes":
            logger.info("중단됨")
            return

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    broker, fake = build_broker(args)
    strategy = MACrossStrategy()
    risk = RiskEngine(RiskLimits())
    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)

    mode = "OFFLINE" if args.offline else f"{args.env.upper()}/{'LIVE' if args.live else 'DRY-RUN'}"
    logger.info("시작: %s | 전략=%s | 종목=%s", mode, strategy.name, symbols)
    events.append("bot_start", {"mode": mode, "strategy": strategy.name, "symbols": symbols})

    trades_today = 0
    cycle = 0
    try:
        while True:
            cycle += 1
            trades_today = run_cycle(broker, strategy, risk, events, symbols, trades_today)

            if hasattr(broker, "tick"):
                for filled in broker.tick():
                    events.append("fill", {
                        "order_id": filled.order_id, "symbol": filled.symbol,
                        "side": filled.side.value, "price": str(filled.price),
                        "quantity": str(filled.quantity),
                    })

            if args.once or (args.cycles and cycle >= args.cycles):
                break
            if args.offline and fake is not None:
                for symbol in symbols:
                    fake.advance(symbol)
            else:
                time.sleep(args.interval)
    finally:
        if hasattr(broker, "summary"):
            summary = broker.summary()
            logger.info("dry-run 요약: %s", summary)
            events.append("bot_stop", {"summary": summary})
        else:
            events.append("bot_stop", {})


if __name__ == "__main__":
    main()
