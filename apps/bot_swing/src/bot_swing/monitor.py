"""장중 손절 감시 — 재난 방지용 리스크 오버레이.

메인 사이클(bot-swing)은 하루 1회 '완성된 일봉 종가'로 판단하므로,
장중에 -15%가 나도 다음 날 아침까지 대응하지 못한다. 이 감시 루프가 그 공백을 메운다.

설계 원칙 (백테스트 결과를 훼손하지 않기 위함):
  1. **매수 없음** — 청산만 수행. 신규 진입은 오직 메인 사이클의 몫
  2. **일봉 손절보다 느슨한 임계** (기본 -8% vs 전략 손절 -5~6%) — 정상 동작에 개입하지 않고
     '갭·급락 재난'만 차단
  3. 진입가 대비 현재가만 본다 — 지표 재계산 없음(진행 중 봉 참조 = 리페인팅 위험 회피)

실행:
  uv run bot-swing-monitor                    # 1회 점검 (cron/스케줄러용, dry-run)
  uv run bot-swing-monitor --loop             # 장중 30분마다 반복
  uv run bot-swing-monitor --live             # 실제 매도 주문
  uv run bot-swing-monitor --threshold 10     # 임계 변경 (%)
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, time as dtime
from decimal import Decimal

from broker_kis import KISApiError, KISBroker
from trading_core import JsonlEventLog, OrderRequest, OrderSide, OrderType

from .main import BOT_NAME, EVENTS_PATH, STATE_PATH, INITIAL_CASH
from .state import BotState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_swing.monitor")

MARKET_OPEN = dtime(9, 0)
MARKET_CLOSE = dtime(15, 20)   # 종가 단일가(15:20~) 전에 마무리


def in_market_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def check_once(broker: KISBroker, threshold_pct: float, live: bool) -> int:
    """보유 종목 점검. 손절 발동 건수 반환."""
    state = BotState.load(STATE_PATH, INITIAL_CASH)
    if not state.positions:
        logger.info("보유 종목 없음")
        return 0

    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)
    fired = 0

    for symbol, held in list(state.positions.items()):
        try:
            price = broker.get_quote(symbol).price
        except KISApiError as e:
            logger.warning("%s 시세 조회 실패 — 스킵: %s", symbol, str(e)[:80])
            continue

        entry = Decimal(held.entry_price)
        change_pct = float((price - entry) / entry * 100)
        logger.info("  %s %s: %s원 (%+.2f%%)", symbol, held.name, f"{price:,}", change_pct)

        if change_pct > -threshold_pct:
            continue

        # --- 재난 손절 발동 ---
        reason = f"장중 긴급손절 {change_pct:.2f}% ≤ -{threshold_pct}%"
        if live:
            broker.place_order(OrderRequest(
                symbol=symbol, side=OrderSide.SELL,
                quantity=Decimal(held.quantity), order_type=OrderType.MARKET,
            ))
        proceeds = price * held.quantity
        cost = entry * held.quantity
        fee_tax = proceeds * Decimal("0.0021")
        pnl = proceeds - fee_tax - cost
        state.cash = str(Decimal(state.cash) + proceeds - fee_tax)
        del state.positions[symbol]
        fired += 1

        logger.warning("🚨 매도 %s %s: %d주 @%s — %s",
                       symbol, held.name, held.quantity, f"{price:,}", reason)
        events.append("exit", {
            "symbol": symbol, "name": held.name, "quantity": str(held.quantity),
            "entry_price": held.entry_price, "exit_price": str(price),
            "pnl": str(pnl), "pnl_pct": round(float(pnl / cost * 100), 3),
            "win": pnl > 0, "holding_bars": held.bars_held,
            "strategy": held.strategy, "reasons": [reason],
            "mode": f"monitor/{'LIVE' if live else 'DRY-RUN'}",
        })

    if fired:
        state.save(STATE_PATH)
    return fired


def main():
    parser = argparse.ArgumentParser(description="장중 손절 감시 (매수 없음)")
    parser.add_argument("--env", choices=["real", "paper"], default="paper")
    parser.add_argument("--live", action="store_true", help="실제 매도 주문")
    parser.add_argument("--threshold", type=float, default=8.0,
                        help="진입가 대비 손실 임계 %% (기본 8, 전략 손절보다 느슨해야 함)")
    parser.add_argument("--loop", action="store_true", help="장중 반복 감시")
    parser.add_argument("--interval", type=int, default=1800, help="반복 간격(초)")
    parser.add_argument("--ignore-hours", action="store_true", help="장시간 체크 생략(테스트용)")
    args = parser.parse_args()

    broker = KISBroker(env=args.env)
    mode = f"{args.env}/{'LIVE' if args.live else 'DRY-RUN'}"
    logger.info("감시 시작 [%s] 임계 -%.1f%% (매수 없음)", mode, args.threshold)

    while True:
        if args.ignore_hours or in_market_hours():
            fired = check_once(broker, args.threshold, args.live)
            if fired:
                logger.warning("긴급손절 %d건 실행", fired)
        else:
            logger.info("장 시간 외 — 대기")
            if not args.loop:
                break

        if not args.loop:
            break
        now = datetime.now()
        if now.time() > MARKET_CLOSE:
            logger.info("장 마감 — 감시 종료")
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
