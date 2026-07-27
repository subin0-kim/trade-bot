"""코인봇 — 사이클당 1회 실행 (권장: 시간당 1회, 작업 스케줄러).

전략 (2026-07 분할검증 생존 2종):
  1. bull_breakout: BTC 일봉 MA10/30/60 정배열일 때만 알트 breakout_momo(240m) 가동, 그외 현금
     — 백테스트 +78.7%/PF 1.61 (B&H -75% 구간), 분할 전반 +71.7/후반 +3.8
  2. shock_follow: BTC 09~10시 |수익률|≥1% → 10시대에 알트 바스켓 매수 → 익일 09시 청산
     — 분할 전반 +0.84%/후반 +0.68% per 이벤트일

부정지식 필터 (역시 실측 기반):
  - 전일 +20% 이상 급등한 알트는 신규 진입 금지 (급등 익일 -2~-6.5%/일 실측)

안전 (업비트는 모의투자 없음 — 실계좌):
  - 봇 원장(state 파일)에 기록된 포지션만 관리. 기존 보유 자산 절대 불가침
  - 예산 상한(--budget) 내에서만 매수. dry-run 기본, --live만 실주문

실행:
  uv run bot-coin                      # dry-run 1사이클
  uv run bot-coin --live               # ⚠️ 실계좌 실주문 (확인 프롬프트)
  uv run bot-coin --budget 500000      # 예산 변경 (기본 100만원)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from broker_upbit import UpbitBroker, align_price
from indicators import closes, sma
from strategy_kit import MarketView, OpenPosition, build_preset
from trading_core import JsonlEventLog, OrderRequest, OrderSide, OrderType

from .state import CoinBotState, CoinPosition

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_coin")

BOT_NAME = "bot-coin"
DATA_DIR = Path(os.environ.get("TRADING_DATA_DIR", "data"))
STATE_PATH = DATA_DIR / "state" / f"{BOT_NAME}.json"
EVENTS_PATH = DATA_DIR / "events" / f"{BOT_NAME}.jsonl"
UNIVERSE_PATH = DATA_DIR / "cache" / "upbit" / "universe.json"

MAX_BREAKOUT_POSITIONS = 4
SHOCK_THRESHOLD_PCT = 1.0
SHOCK_BASKET_N = 10          # 쇼크 이벤트 시 매수할 알트 수 (24h 거래대금 상위)
SURGE_SKIP_PCT = 20.0        # 전일 급등 진입 금지 임계
FEE = Decimal("0.0005")


def load_universe(broker: UpbitBroker) -> list[str]:
    """백테스트 유니버스 ∩ 현재 유효 마켓 (BTC 제외 — 신호용)."""
    valid = set(broker.list_krw_markets())
    if UNIVERSE_PATH.exists():
        saved = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
        return [s for s in saved if s in valid and s != "KRW-BTC"]
    return []


def completed_240m(broker: UpbitBroker, symbol: str, count: int = 120):
    """완성된 240분봉만 (진행 중인 마지막 봉 제외)."""
    bars = broker.get_minute_candles(symbol, unit=240, count=count)
    now = datetime.now()
    return [b for b in bars if b.ts + timedelta(minutes=240) <= now]


def btc_regime(broker: UpbitBroker) -> str:
    """BTC 일봉 MA10/30/60 정배열 여부. 오늘(진행 중) 봉 제외.

    주의: 업비트 일봉 경계는 09:00 KST — 백테스트(자정 경계)와 미세하게 다르다.
    전방 검증에서 이 괴리의 영향을 관찰한다 (wiki/crypto-condition-switching 한계 참조).
    """
    daily = broker.get_daily_candles(
        "KRW-BTC", date.today() - timedelta(days=100), date.today()
    )
    done = [c for c in daily if c.ts.date() < date.today()]
    xs = closes(done)
    ma10, ma30, ma60 = sma(xs, 10), sma(xs, 30), sma(xs, 60)
    if ma60[-1] is None:
        return "unknown"
    if xs[-1] > ma60[-1] and ma10[-1] > ma30[-1]:
        return "bull"
    if xs[-1] < ma60[-1] and ma10[-1] < ma30[-1]:
        return "bear"
    return "neutral"


def btc_open_shock(broker: UpbitBroker) -> float | None:
    """오늘 09~10시 BTC 수익률(%). 10시 이전이면 None."""
    now = datetime.now()
    if now.hour < 10:
        return None
    bars = broker.get_minute_candles("KRW-BTC", unit=5, count=200)
    today9 = [b for b in bars if b.ts.date() == date.today() and b.ts.hour == 9]
    if len(today9) < 12:
        return None
    today9.sort(key=lambda b: b.ts)
    o, c = float(today9[0].open), float(today9[-1].close)
    return (c / o - 1) * 100 if o > 0 else None


def prev_day_surge(broker: UpbitBroker, symbol: str) -> float:
    """전일(업비트 일봉) 등락률 % — 급등 익일 진입 금지 필터용."""
    daily = broker.get_daily_candles(
        symbol, date.today() - timedelta(days=5), date.today()
    )
    done = [c for c in daily if c.ts.date() < date.today()]
    if not done:
        return 0.0
    last = done[-1]
    return float((last.close / last.open - 1) * 100) if last.open > 0 else 0.0


def place_buy(broker, state, events, symbol, krw_amount, strategy_tag, reasons, live, exit_due=""):
    quote = broker.get_quote(symbol)
    qty = (Decimal(str(krw_amount)) / quote.price).quantize(Decimal("0.00000001"))
    if qty * quote.price < 5000:
        return False
    if live:
        broker.place_order(OrderRequest(
            symbol=symbol, side=OrderSide.BUY, quantity=qty, order_type=OrderType.MARKET,
        ))
    cost = quote.price * qty
    state.cash = str(Decimal(state.cash) - cost * (1 + FEE))
    state.positions[symbol] = CoinPosition(
        symbol=symbol, quantity=str(qty), entry_price=str(quote.price),
        entry_ts=datetime.now().isoformat(), strategy=strategy_tag,
        highest_close=str(quote.price), exit_due=exit_due,
    )
    logger.info("매수 %s: %s @ %s (%s)", symbol, qty, f"{quote.price:,}", strategy_tag)
    events.append("entry", {
        "symbol": symbol, "name": symbol.replace("KRW-", ""), "quantity": str(qty),
        "price": str(quote.price), "strategy": strategy_tag, "reasons": reasons,
    })
    return True


def place_sell(broker, state, events, pos: CoinPosition, reason, live):
    quote = broker.get_quote(pos.symbol)
    qty = Decimal(pos.quantity)
    if live:
        broker.place_order(OrderRequest(
            symbol=pos.symbol, side=OrderSide.SELL, quantity=qty, order_type=OrderType.MARKET,
        ))
    proceeds = quote.price * qty * (1 - FEE)
    cost = Decimal(pos.entry_price) * qty
    pnl = proceeds - cost
    state.cash = str(Decimal(state.cash) + proceeds)
    del state.positions[pos.symbol]
    pnl_pct = float(pnl / cost * 100) if cost else 0.0
    logger.info("매도 %s: %+.2f%% — %s", pos.symbol, pnl_pct, reason)
    events.append("exit", {
        "symbol": pos.symbol, "name": pos.symbol.replace("KRW-", ""),
        "quantity": pos.quantity, "entry_price": pos.entry_price,
        "exit_price": str(quote.price), "pnl": str(pnl), "pnl_pct": round(pnl_pct, 3),
        "win": pnl > 0, "holding_bars": 0, "strategy": pos.strategy, "reasons": [reason],
    })


def main():
    parser = argparse.ArgumentParser(description="코인봇 (사이클당 1회)")
    parser.add_argument("--live", action="store_true", help="⚠️ 실계좌 실주문")
    parser.add_argument("--budget", type=int, default=1_000_000, help="봇 할당 예산(원)")
    args = parser.parse_args()

    if args.live:
        if input("⚠️ 업비트 실계좌에 실주문이 나갑니다 (모의 환경 없음). 'yes' 입력: ") != "yes":
            return

    broker = UpbitBroker()
    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)
    state = CoinBotState.load(STATE_PATH, Decimal(args.budget))
    mode = "LIVE" if args.live else "DRY-RUN"
    logger.info("코인봇 [%s] 현금 %s원, 보유 %d종목", mode, state.cash, len(state.positions))

    universe = load_universe(broker)
    regime = btc_regime(broker)
    logger.info("BTC 레짐: %s | 유니버스 %d종목", regime.upper(), len(universe))

    breakout = build_preset("breakout_momo")
    now = datetime.now()

    # ---------- 1) 보유 청산 판단 (원장에 있는 것만!) ----------
    for symbol, pos in list(state.positions.items()):
        if pos.strategy == "shock_follow":
            if pos.exit_due and now >= datetime.fromisoformat(pos.exit_due):
                place_sell(broker, state, events, pos, "쇼크 익일 09시 청산", args.live)
            continue
        # bull_breakout: 완성 240m 봉으로 전략 청산 규칙 평가
        bars = completed_240m(broker, symbol, 200)
        if len(bars) < 60:
            continue
        quote_price = bars[-1].close
        held = OpenPosition(
            side=OrderSide.BUY, quantity=Decimal(pos.quantity),
            entry_price=Decimal(pos.entry_price),
            entry_ts=datetime.fromisoformat(pos.entry_ts),
            bars_held=int((now - datetime.fromisoformat(pos.entry_ts)).total_seconds() // (240 * 60)),
            highest_close=max(Decimal(pos.highest_close), quote_price),
        )
        pos.highest_close = str(held.highest_close)
        view = MarketView(symbol=symbol, primary_tf="240m", candles={"240m": bars[-320:]},
                          quantity_step=Decimal("0.00000001"), min_order_value=Decimal(5000))
        decision = breakout.evaluate(view, held, Decimal(state.cash))
        if decision.action == "exit":
            place_sell(broker, state, events, pos, " / ".join(decision.reasons), args.live)
        elif regime != "bull":
            place_sell(broker, state, events, pos, f"레짐 이탈({regime}) — 현금화", args.live)

    # ---------- 2) 쇼크 이벤트 (btc_shock_alt_follow) ----------
    today_str = date.today().isoformat()
    if state.last_shock_date != today_str and 10 <= now.hour <= 11:
        shock = btc_open_shock(broker)
        if shock is not None and abs(shock) >= SHOCK_THRESHOLD_PCT:
            logger.info("⚡ BTC 오픈쇼크 %+.2f%% — 알트 바스켓 진입", shock)
            tickers = broker.client.get("/v1/ticker", {"markets": ",".join(universe)})
            ranked = sorted(tickers, key=lambda t: t.get("acc_trade_price_24h", 0), reverse=True)
            targets = [t["market"] for t in ranked[:SHOCK_BASKET_N]
                       if t["market"] not in state.positions]
            per_coin = Decimal(state.cash) * Decimal("0.5") / max(len(targets), 1)
            entered = 0
            for symbol in targets:
                if prev_day_surge(broker, symbol) >= SURGE_SKIP_PCT:
                    logger.info("  %s 스킵 — 전일 +%.0f%% 급등 (부정지식 필터)", symbol,
                                prev_day_surge(broker, symbol))
                    continue
                next_9am = datetime.combine(date.today() + timedelta(days=1),
                                            datetime.min.time()).replace(hour=9)
                if place_buy(broker, state, events, symbol, per_coin, "shock_follow",
                             [f"BTC 오픈쇼크 {shock:+.2f}%", "익일 09시 청산 예정"],
                             args.live, exit_due=next_9am.isoformat()):
                    entered += 1
            state.last_shock_date = today_str
            logger.info("쇼크 진입 %d종목", entered)
        elif shock is not None:
            state.last_shock_date = today_str  # 오늘은 평온 — 재확인 불필요

    # ---------- 3) bull_breakout 신규 진입 ----------
    breakout_held = sum(1 for p in state.positions.values() if p.strategy == "bull_breakout")
    slots = MAX_BREAKOUT_POSITIONS - breakout_held
    if regime == "bull" and slots > 0:
        candidates = []
        for symbol in universe:
            if symbol in state.positions:
                continue
            bars = completed_240m(broker, symbol, 200)
            if len(bars) < 60:
                continue
            view = MarketView(symbol=symbol, primary_tf="240m", candles={"240m": bars[-320:]},
                              quantity_step=Decimal("0.00000001"), min_order_value=Decimal(5000))
            decision = breakout.evaluate(view, None, Decimal(state.cash))
            if decision.action == "enter":
                candidates.append((decision.score, symbol, decision))
        candidates.sort(key=lambda c: (-c[0], c[1]))
        if candidates:
            logger.info("돌파 후보 %d개 (슬롯 %d)", len(candidates), slots)
        per_slot = Decimal(args.budget) * Decimal("0.9") / MAX_BREAKOUT_POSITIONS
        for score, symbol, decision in candidates[:slots]:
            surge = prev_day_surge(broker, symbol)
            if surge >= SURGE_SKIP_PCT:
                logger.info("  %s 스킵 — 전일 +%.0f%% 급등 (부정지식 필터)", symbol, surge)
                continue
            amount = min(per_slot, Decimal(state.cash) * Decimal("0.95"))
            place_buy(broker, state, events, symbol, amount, "bull_breakout",
                      list(decision.reasons) + [f"BTC레짐:{regime}"], args.live)
    elif regime != "bull":
        logger.info("레짐 %s — 신규 돌파 진입 없음", regime)

    # ---------- 4) 자산 스냅샷 + 저장 ----------
    equity = Decimal(state.cash)
    for symbol, pos in state.positions.items():
        try:
            equity += broker.get_quote(symbol).price * Decimal(pos.quantity)
        except Exception:
            equity += Decimal(pos.entry_price) * Decimal(pos.quantity)
    events.append("equity", {"equity": str(equity), "cash": state.cash,
                             "n_positions": len(state.positions), "mode": mode,
                             "regime": regime})
    state.save(STATE_PATH)
    logger.info("종료: 자산 %s원 (현금 %s, 보유 %d)", f"{equity:,.0f}",
                f"{Decimal(state.cash):,.0f}", len(state.positions))


if __name__ == "__main__":
    main()
