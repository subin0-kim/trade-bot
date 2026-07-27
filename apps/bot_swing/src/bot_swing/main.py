"""스윙봇 — 하루 1회 실행 (장중 아무 때나, 권장: 개장 직후).

사이클:
  1. 레짐 판별 (KOSPI 완성봉) → 활성 전략 결정
  2. US 쇼크필터 (나스닥 야간 |수익률|≥2% → 신규진입 금지)
  3. 보유 종목 청산 판단 → 매도
  4. 슬롯 여유 시 유니버스 스캔 → 매수
  5. 이벤트 로그(entry/exit/equity) + 상태 저장 → 대시보드 자동 반영

실행:
  uv run bot-swing                    # dry-run (로컬 모의체결, 기본)
  uv run bot-swing --live             # 모의투자 서버에 실주문 (paper 계좌)
  uv run bot-swing --env real --live  # ★ 실전 (확인 프롬프트)

검증된 구성(2026-07): 현금/connors_rsi2/macd_trend_mtf + US필터,
100만원 · 4슬롯 · 슬롯예산 사이징. 백테스트 5년 +44.1%/MDD 27.3%.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from broker_kis import KISBroker
from regime import Regime, RegimeClassifier
from strategy_kit import MarketView, build_preset, preset_meta
from strategy_kit.sizing import FixedFractionSizer
from trading_core import JsonlEventLog, OrderRequest, OrderSide, OrderType

from .state import BotState, HeldPosition

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_swing")

BOT_NAME = "bot-swing"
DATA_DIR = Path(os.environ.get("TRADING_DATA_DIR", "data"))
STATE_PATH = DATA_DIR / "state" / f"{BOT_NAME}.json"
EVENTS_PATH = DATA_DIR / "events" / f"{BOT_NAME}.jsonl"

# 검증된 운용 설정 (wiki/shared/market-regimes/regime-strategy-observations.md)
INITIAL_CASH = Decimal(1_000_000)
MAX_POSITIONS = 4
US_SHOCK_PCT = 2.0
REGIME_MAPPING = {
    Regime.BEAR: None,
    Regime.SIDEWAYS: "connors_rsi2",
    Regime.BULL: "macd_trend_mtf",
}

# 유니버스 (universe_backtest.py와 동일 — 추후 설정 파일로 승격)
UNIVERSE: dict[str, str] = {
    "005930": "삼성전자", "000660": "SK하이닉스", "005380": "현대차", "000270": "기아",
    "068270": "셀트리온", "005490": "POSCO홀딩스", "035420": "NAVER", "035720": "카카오",
    "051910": "LG화학", "006400": "삼성SDI", "012330": "현대모비스", "105560": "KB금융",
    "055550": "신한지주", "086790": "하나금융지주", "032830": "삼성생명", "015760": "한국전력",
    "017670": "SK텔레콤", "030200": "KT", "066570": "LG전자", "009150": "삼성전기",
    "010950": "S-Oil", "011170": "롯데케미칼", "090430": "아모레퍼시픽", "051900": "LG생활건강",
    "097950": "CJ제일제당", "139480": "이마트", "004370": "농심", "021240": "코웨이",
    "036570": "엔씨소프트", "251270": "넷마블", "352820": "하이브", "323410": "카카오뱅크",
    "018260": "삼성SDS", "012450": "한화에어로스페이스", "329180": "HD현대중공업",
    "011200": "HMM", "010130": "고려아연",
}


def fetch_completed_daily(broker: KISBroker, symbol: str, days: int = 500):
    """오늘(진행 중) 봉 제외한 완성 일봉."""
    from datetime import timedelta

    today = date.today()
    candles = []
    cursor = today - timedelta(days=days)
    while cursor <= today:
        window_end = min(cursor + timedelta(days=140), today)
        candles.extend(broker.get_daily_candles(symbol, cursor, window_end))
        cursor = window_end + timedelta(days=1)
    unique = {c.ts: c for c in candles if c.ts.date() < today}
    return [unique[k] for k in sorted(unique)]


def determine_regime(broker: KISBroker) -> Regime:
    from datetime import timedelta

    today = date.today()
    candles = []
    cursor = today - timedelta(days=500)
    while cursor <= today:
        window_end = min(cursor + timedelta(days=65), today)  # 지수 API 50건/콜
        candles.extend(broker.get_index_daily_candles("0001", cursor, window_end))
        cursor = window_end + timedelta(days=1)
    done = sorted({c.ts: c for c in candles if c.ts.date() < today}.values(), key=lambda c: c.ts)
    series = RegimeClassifier().classify_series(done)
    return series[done[-1].ts.date()]


def us_overnight_return(broker: KISBroker) -> float:
    from datetime import timedelta

    today = date.today()
    candles = []
    cursor = today - timedelta(days=20)
    data = broker.client.get(
        "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
        "FHKST03030100",
        {
            "FID_COND_MRKT_DIV_CODE": "N", "FID_INPUT_ISCD": "COMP",
            "FID_INPUT_DATE_1": cursor.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": today.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
        },
    )
    rows = sorted(
        (r for r in data.get("output2", []) if r.get("stck_bsop_date")),
        key=lambda r: r["stck_bsop_date"],
    )
    done = [r for r in rows if r["stck_bsop_date"] < today.strftime("%Y%m%d")]
    if len(done) < 2:
        return 0.0
    prev, cur = float(done[-2]["ovrs_nmix_prpr"]), float(done[-1]["ovrs_nmix_prpr"])
    return (cur / prev - 1) * 100 if prev else 0.0


def main():
    parser = argparse.ArgumentParser(description="스윙봇 (하루 1회)")
    parser.add_argument("--env", choices=["real", "paper"], default="paper")
    parser.add_argument("--live", action="store_true", help="실제 주문 전송 (기본 dry-run)")
    args = parser.parse_args()

    if args.env == "real" and args.live:
        if input("⚠️  실전 계좌 실주문. 'yes' 입력 시 진행: ") != "yes":
            return

    broker = KISBroker(env=args.env)
    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)
    state = BotState.load(STATE_PATH, INITIAL_CASH)
    mode = f"{args.env}/{'LIVE' if args.live else 'DRY-RUN'}"
    logger.info("스윙봇 시작 [%s] 현금 %s원, 보유 %d종목", mode, state.cash, len(state.positions))

    # --- 1. 레짐 ---
    regime = determine_regime(broker)
    preset_name = REGIME_MAPPING[regime]
    logger.info("레짐: %s → 전략: %s", regime.value.upper(), preset_name or "현금 (신규진입 없음)")

    # --- 2. US 필터 ---
    us_ret = us_overnight_return(broker)
    us_blocked = abs(us_ret) >= US_SHOCK_PCT
    logger.info("나스닥 야간 %+.2f%% → %s", us_ret, "쇼크일: 신규진입 차단" if us_blocked else "정상")

    strategy = build_preset(preset_name) if preset_name else None
    if strategy is not None:
        strategy.sizer = FixedFractionSizer(fraction=0.9 / MAX_POSITIONS)

    # --- 3. 보유 종목 청산 판단 ---
    equity = Decimal(state.cash)
    candle_cache = {}
    for symbol, held in list(state.positions.items()):
        candles = fetch_completed_daily(broker, symbol)
        candle_cache[symbol] = candles
        last = candles[-1]
        held.bars_held += 1
        if last.close > Decimal(held.highest_close):
            held.highest_close = str(last.close)
        equity += last.close * held.quantity

        # 청산 판단: 레짐이 현금이면 전량 청산, 아니면 활성 전략의 청산 모듈
        view = MarketView(symbol=symbol, primary_tf="D", candles={"D": candles[-320:]})
        exit_reason = None
        if strategy is None:
            exit_reason = f"레짐 {regime.value} → 현금화"
        else:
            decision = strategy.evaluate(view, held.to_open_position(), equity)
            if decision.action == "exit":
                exit_reason = " / ".join(decision.reasons)

        if exit_reason:
            price = broker.get_quote(symbol).price
            if args.live:
                broker.place_order(OrderRequest(
                    symbol=symbol, side=OrderSide.SELL,
                    quantity=Decimal(held.quantity), order_type=OrderType.MARKET,
                ))
            entry_price = Decimal(held.entry_price)
            proceeds = price * held.quantity
            cost = entry_price * held.quantity
            fee_tax = proceeds * Decimal("0.0021")  # 수수료+거래세 근사
            pnl = proceeds - fee_tax - cost
            state.cash = str(Decimal(state.cash) + proceeds - fee_tax)
            del state.positions[symbol]
            logger.info("매도 %s %s: %d주 @%s (%+.2f%%) — %s",
                        symbol, held.name, held.quantity, price,
                        float(pnl / cost * 100), exit_reason)
            events.append("exit", {
                "symbol": symbol, "name": held.name, "quantity": str(held.quantity),
                "entry_price": held.entry_price, "exit_price": str(price),
                "pnl": str(pnl), "pnl_pct": round(float(pnl / cost * 100), 3),
                "win": pnl > 0, "holding_bars": held.bars_held,
                "strategy": held.strategy, "reasons": [exit_reason], "mode": mode,
            })

    # --- 4. 신규 진입 스캔 ---
    if strategy is not None and not us_blocked:
        slots = MAX_POSITIONS - len(state.positions)
        if slots > 0:
            meta = preset_meta(preset_name)
            for symbol, name in UNIVERSE.items():
                if slots <= 0:
                    break
                if symbol in state.positions:
                    continue
                candles = candle_cache.get(symbol) or fetch_completed_daily(broker, symbol)
                if len(candles) < 260:
                    continue
                view_candles = {"D": candles[-320:]}
                if "W" in meta["higher_tfs"]:
                    from backtest import resample
                    view_candles["W"] = resample(candles, "W")[:-1]
                view = MarketView(symbol=symbol, primary_tf="D", candles=view_candles)
                decision = strategy.evaluate(view, None, equity)
                if decision.action != "enter":
                    continue
                price = broker.get_quote(symbol).price
                qty = int(min(decision.quantity, Decimal(state.cash) / price))
                if qty < 1:
                    continue
                if args.live:
                    broker.place_order(OrderRequest(
                        symbol=symbol, side=OrderSide.BUY,
                        quantity=Decimal(qty), order_type=OrderType.MARKET,
                    ))
                cost = price * qty
                fee = cost * Decimal("0.00015")
                state.cash = str(Decimal(state.cash) - cost - fee)
                state.positions[symbol] = HeldPosition(
                    symbol=symbol, name=name, quantity=qty,
                    entry_price=str(price), entry_ts=datetime.now().isoformat(),
                    strategy=preset_name, highest_close=str(price),
                )
                slots -= 1
                reasons = list(decision.reasons) + [f"레짐:{regime.value}", f"나스닥 {us_ret:+.2f}%"]
                logger.info("매수 %s %s: %d주 @%s — %s", symbol, name, qty, price, reasons[0])
                events.append("entry", {
                    "symbol": symbol, "name": name, "quantity": str(qty),
                    "price": str(price), "strategy": preset_name,
                    "reasons": reasons, "mode": mode,
                })
    elif us_blocked:
        events.append("policy_blocked", {"reason": f"US 쇼크일 (나스닥 {us_ret:+.2f}%)"})

    # --- 5. 자산 스냅샷 + 저장 ---
    equity = Decimal(state.cash)
    for symbol, held in state.positions.items():
        candles = candle_cache.get(symbol)
        price = candles[-1].close if candles else broker.get_quote(symbol).price
        equity += price * held.quantity
    events.append("equity", {"equity": str(equity), "cash": state.cash,
                             "n_positions": len(state.positions), "mode": mode})
    state.save(STATE_PATH)
    logger.info("종료: 자산 %s원 (현금 %s, 보유 %d종목)", equity, state.cash, len(state.positions))


if __name__ == "__main__":
    main()
