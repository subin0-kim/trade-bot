"""코인봇 — 사이클당 1회 실행 (권장: 시간당 1회, 작업 스케줄러).

전략 (2026-07 검증 — 레짐은 앙상블 2/3 다수결 {ROC30>0, SuperTrend(10,3), MA10>MA30}):
  1. core: BTC·ETH 각자 자체 앙상블이 초록불이면 예산 25%씩 홀드, 꺼지면 청산
     — BTC 신호를 ETH에 튜닝 없이 이식해도 작동 (일반화 증거).
       결합 +100.1→+118.7%/MDD 21.7, 분할 전반 +66.4/후반 +31.5 ✓
  2. bull_breakout: BTC 초록불 5일차부터 나머지 예산 50%로 알트 breakout_momo(240m) 위성
     — 단독은 분할 취약이라 위성으로 강등. 유니버스 = 시총 상위 10
  3. shock_follow: BTC 09~10시 |수익률|≥1% → 10시대에 알트 바스켓 매수 → 익일 09시 청산
     — 분할 전반 +0.84%/후반 +0.68% per 이벤트일

부정지식 필터 (역시 실측 기반):
  - 전일 +20% 이상 급등한 알트는 신규 진입 금지 (급등 익일 -2~-6.5%/일 실측)

안전 (업비트는 모의투자 없음 — 실계좌):
  - 봇 원장(state 파일)에 기록된 포지션만 관리. 기존 보유 자산 절대 불가침
  - --budget은 원장 초기 시드 — 이후 사이징은 원장 자산 비례 (복리, 원장 밖 자산 불가침). dry-run 기본, --live만 실주문

실행:
  uv run bot-coin                      # dry-run 1사이클
  uv run bot-coin --live               # ⚠️ 실계좌 실주문 (확인 프롬프트)
  uv run bot-coin --live --yes         # ⚠️ 무인 실행용 (systemd) — 프롬프트 생략
  uv run bot-coin --budget 500000      # 예산 변경 (기본 100만원)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from broker_upbit import UpbitApiError, UpbitBroker, align_price
from indicators import closes, roc, sma, supertrend
from strategy_kit import MarketView, OpenPosition, build_preset
from trading_core import JsonlEventLog, OrderRequest, OrderSide, OrderType

from .state import CoinBotState, CoinPosition

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_coin")

BOT_NAME = "bot-coin"
DATA_DIR = Path(os.environ.get("TRADING_DATA_DIR", "data"))
STATE_PATH = DATA_DIR / "state" / f"{BOT_NAME}.json"
EVENTS_PATH = DATA_DIR / "events" / f"{BOT_NAME}.jsonl"

MAX_BREAKOUT_POSITIONS = 8   # 검증 구성과 정렬 (2026-07-31: 4슬롯은 -98%p·MDD↑, 얕고 넓게)
SHOCK_THRESHOLD_PCT = 1.0
SHOCK_BASKET_N = 10          # 쇼크 이벤트 시 매수할 알트 수 (24h 거래대금 상위)
SURGE_SKIP_PCT = 20.0        # 전일 급등 진입 금지 임계
CORE_FRACTION = Decimal("0.5")   # 코어 홀드 총 비중 (검증: 50:50 결합 ✓)
CORE_ASSETS = ["KRW-BTC", "KRW-ETH"]  # 각자 자체 앙상블 게이트, 예산 균등 분할 (25%씩)
BREAKOUT_MIN_BULL_AGE = 5        # 위성 진입은 초록불 5일차부터 (전환 직후 깜빡임 구간 패배 실측)
FEE = Decimal("0.0005")

# 알트 유니버스 = 시가총액 상위 15 (2026-07-28 CoinGecko 기준, 사용자 지시).
# 제외: BTC·ETH(코어 전담), 스테이블/연동자산(USDE·XAUT), 상장 200일 미만(CC),
# 업비트 미상장(BNB·HYPE·ZEC·XMR 등). 백테스트: 위성 +74.8→+198.3%/PF 2.2/분할 ✓
# (단, 현재 시총 순위로 과거를 검증한 생존 편향 있음 — 전방 검증이 최종 판정).
# 시총 순위는 업비트 API에 없어 정적 고정 — 분기마다 수동 갱신할 것.
TOP_MCAP_ALTS = ["KRW-XRP", "KRW-SOL", "KRW-TRX", "KRW-DOGE", "KRW-LINK",
                 "KRW-XLM", "KRW-ADA", "KRW-BCH", "KRW-HBAR", "KRW-AVAX",
                 "KRW-SUI", "KRW-SHIB", "KRW-CRO", "KRW-UNI", "KRW-NEAR"]


def load_universe(broker: UpbitBroker) -> list[str]:
    """시총 상위 15 알트 ∩ 현재 유효 마켓 (BTC·ETH 제외 — 코어 전담)."""
    valid = set(broker.list_krw_markets())
    return [s for s in TOP_MCAP_ALTS if s in valid]


def completed_240m(broker: UpbitBroker, symbol: str, count: int = 120):
    """완성된 240분봉만 (진행 중인 마지막 봉 제외)."""
    bars = broker.get_minute_candles(symbol, unit=240, count=count)
    now = datetime.now()
    return [b for b in bars if b.ts + timedelta(minutes=240) <= now]


def asset_regime(broker: UpbitBroker, symbol: str) -> tuple[str, int, dict]:
    """자산 일봉 앙상블 레짐 — {ROC30>0, SuperTrend(10,3), MA10>MA30} 2/3 다수결.

    반환: (레짐, 초록불 연속일수, 일자별 플래그). 코어는 자산별 자체 레짐으로 게이트하고
    (BTC 기준을 ETH에 튜닝 없이 이식 — 일반화 검증 ✓), 위성은 BTC∪ETH OR 게이트
    (2026-07-31 실측: 최악 반쪽 +22.8→+40.2, or_gate 참조) — 일자별 플래그는 그 합집합 계산용.
    위성(돌파) 진입은 OR 초록불 5일차부터만 — 전환 직후 깜빡임 구간 패배 실측.

    2026-07 기준 심사: 3개 강건 가족의 다수결이 '가장 나쁜 반쪽' 최고
    (wiki/crypto-regime-findings). 단일 기준(MA10/30/60 정배열)은 후반 취약으로 교체됨.

    주의: 업비트 일봉 경계 09:00 KST vs 백테스트 자정 경계 — 전방 검증 관찰 대상.
    """
    daily = broker.get_daily_candles(
        symbol, date.today() - timedelta(days=150), date.today()
    )
    done = [c for c in daily if c.ts.date() < date.today()]
    xs = closes(done)
    if len(xs) < 65:
        return "unknown", 0, {}
    r30 = roc(xs, 30)
    st, _ = supertrend(done, 10, 3.0)
    ma10, ma30 = sma(xs, 10), sma(xs, 30)
    flags = []
    for i in range(len(done)):
        votes = sum([
            1 if (r30[i] is not None and r30[i] > 0) else 0,
            1 if st[i] == 1 else 0,
            1 if (ma10[i] is not None and ma30[i] is not None and ma10[i] > ma30[i]) else 0,
        ])
        flags.append(votes >= 2)
    bull_age = 0
    for f in reversed(flags):
        if not f:
            break
        bull_age += 1
    logger.info("%s 레짐 투표: ROC30 %s, SuperTrend %s, MA10>30 %s | 초록불 %d일째",
                symbol.replace("KRW-", ""),
                "○" if (r30[-1] or 0) > 0 else "×",
                "○" if st[-1] == 1 else "×",
                "○" if (ma10[-1] or 0) > (ma30[-1] or 1) else "×", bull_age)
    by_date = {done[i].ts.date(): flags[i] for i in range(len(done))}
    return ("bull" if flags[-1] else "off"), bull_age, by_date


def or_gate(regimes: dict[str, tuple[str, int, dict]]) -> tuple[str, int]:
    """위성 게이트 — 코어 자산들의 일자별 플래그 합집합(OR)으로 레짐·연속일수 계산.

    근거 (2026-07-31 실측, wiki/crypto-regime-findings): BTC 단독 대비 최악 반쪽
    +22.8→+40.2, MDD·PF 동등, 스위치 감소. ETH 단독은 BTC보다 약함 → 개선 원천은
    커버리지 분산 (지표 3종 다수결과 같은 원리의 자산 축 확장). AND는 후반 붕괴로 기각.
    한쪽이 unknown(플래그 없음)이면 남은 쪽만으로 판정 — 둘 다 없으면 unknown (보수 모드).
    """
    merged: dict = {}
    for _, _, flags in regimes.values():
        for d, f in flags.items():
            merged[d] = merged.get(d, False) or f
    if not merged:
        return "unknown", 0
    days = sorted(merged)
    age = 0
    for d in reversed(days):
        if not merged[d]:
            break
        age += 1
    return ("bull" if merged[days[-1]] else "off"), age


def ledger_equity(broker: UpbitBroker, state) -> Decimal:
    """원장 자산 = 현금 + 보유 포지션 평가액 (시세 실패 시 진입가 폴백).

    사이징 기준 (2026-07-31 복리 정렬): 검증 백테스트는 '그 시점 자산의 비율'로
    베팅하는 복리인데 라이브는 시작 예산 고정이었음 — 원장 자산 비례로 정렬.
    원장 안의 돈만 계산하므로 기존 보유 자산 불가침은 그대로 유지된다.
    """
    total = Decimal(state.cash)
    for symbol, pos in state.positions.items():
        try:
            total += broker.get_quote(symbol).price * Decimal(pos.quantity)
        except Exception:
            total += Decimal(pos.entry_price) * Decimal(pos.quantity)
    return total


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
    entry_price = quote.price
    paid_fee = None
    if live:
        try:
            order = broker.place_order(OrderRequest(
                symbol=symbol, side=OrderSide.BUY, quantity=qty, order_type=OrderType.MARKET,
            ))
        except UpbitApiError as e:
            # 주문 1건 실패(잔고 부족·마켓 일시정지 등)가 사이클 전체를 죽이면 안 된다
            logger.error("⚠️ %s 매수 주문 실패: %s — 이번 사이클 스킵", symbol, e)
            return False
        filled, avg, paid_fee = broker.settle_order(order)
        if filled <= 0:
            logger.error("⚠️ %s 매수 미체결 (주문 %s) — 원장 기록 없음", symbol, order.order_id)
            return False
        qty, entry_price = filled, (avg or quote.price)  # 실체결 기준으로 원장 기록
    cost = entry_price * qty
    fee = paid_fee if (live and paid_fee is not None) else cost * FEE  # 라이브=실수수료
    state.cash = str(Decimal(state.cash) - cost - fee)
    state.positions[symbol] = CoinPosition(
        symbol=symbol, quantity=str(qty), entry_price=str(entry_price),
        entry_ts=datetime.now().isoformat(), strategy=strategy_tag,
        highest_close=str(entry_price), exit_due=exit_due,
    )
    state.save(STATE_PATH)  # 체결 즉시 저장 — 사이클 중단 시 원장-실계좌 불일치 방지
    logger.info("매수 %s: %s @ %s (%s)", symbol, qty, f"{entry_price:,}", strategy_tag)
    events.append("entry", {
        "symbol": symbol, "name": symbol.replace("KRW-", ""), "quantity": str(qty),
        "price": str(entry_price), "strategy": strategy_tag, "reasons": reasons,
        "mode": "LIVE" if live else "DRY-RUN",
    })
    return True


def place_sell(broker, state, events, pos: CoinPosition, reason, live):
    quote = broker.get_quote(pos.symbol)
    qty = Decimal(pos.quantity)
    exit_price = quote.price
    partial = False
    paid_fee = None
    if live:
        try:
            order = broker.place_order(OrderRequest(
                symbol=pos.symbol, side=OrderSide.SELL, quantity=qty, order_type=OrderType.MARKET,
            ))
        except UpbitApiError as e:
            logger.error("⚠️ %s 매도 주문 실패: %s — 포지션 유지, 다음 사이클 재시도", pos.symbol, e)
            return
        filled, avg, paid_fee = broker.settle_order(order)
        if filled <= 0:
            logger.error("⚠️ %s 매도 미체결 (주문 %s) — 포지션 유지, 다음 사이클 재시도",
                         pos.symbol, order.order_id)
            return
        exit_price = avg or quote.price
        if filled < qty:  # 부분체결 — 잔여 수량으로 포지션 유지
            logger.warning("%s 부분체결 %s/%s — 잔여분 유지", pos.symbol, filled, qty)
            pos.quantity = str(qty - filled)
            qty = filled
            partial = True
    gross = exit_price * qty
    sell_fee = paid_fee if (live and paid_fee is not None) else gross * FEE  # 라이브=실수수료
    proceeds = gross - sell_fee
    cost = Decimal(pos.entry_price) * qty
    pnl = proceeds - cost
    state.cash = str(Decimal(state.cash) + proceeds)
    if not partial:
        del state.positions[pos.symbol]
    state.save(STATE_PATH)  # 체결 즉시 저장
    pnl_pct = float(pnl / cost * 100) if cost else 0.0
    logger.info("매도 %s: %+.2f%% — %s", pos.symbol, pnl_pct, reason)
    events.append("exit", {
        "symbol": pos.symbol, "name": pos.symbol.replace("KRW-", ""),
        "quantity": str(qty), "entry_price": pos.entry_price,
        "exit_price": str(exit_price), "pnl": str(pnl), "pnl_pct": round(pnl_pct, 3),
        "win": pnl > 0, "holding_bars": 0, "strategy": pos.strategy, "reasons": [reason],
        "mode": "LIVE" if live else "DRY-RUN",
    })


def main():
    parser = argparse.ArgumentParser(description="코인봇 (사이클당 1회)")
    parser.add_argument("--live", action="store_true", help="⚠️ 실계좌 실주문")
    parser.add_argument("--yes", action="store_true",
                        help="--live 확인 프롬프트 생략 (systemd 등 무인 실행용)")
    parser.add_argument("--budget", type=int, default=1_000_000,
                        help="원장 초기 시드(원) — 첫 실행 시에만 사용, 이후 사이징은 원장 자산 비례(복리)")
    args = parser.parse_args()

    if args.live and not args.yes:
        if not sys.stdin.isatty():
            logger.error("--live는 대화형 확인이 필요합니다. 무인 실행은 --live --yes로 명시하세요.")
            sys.exit(2)
        if input("⚠️ 업비트 실계좌에 실주문이 나갑니다 (모의 환경 없음). 'yes' 입력: ") != "yes":
            return

    broker = UpbitBroker()
    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)
    mode = "LIVE" if args.live else "DRY-RUN"
    state_mode = "live" if args.live else "dry-run"
    state = CoinBotState.load(STATE_PATH, Decimal(args.budget), mode=state_mode)

    # 원장 모드 가드 — dry-run 가상 포지션을 물고 live로 돌면
    # 실제로 산 적 없는 코인을 실계좌에서 팔게 된다 (불가침 규칙 위반).
    if state.mode != state_mode:
        logger.error(
            "⛔ 원장 모드 불일치: 원장=%s, 실행=%s. 기존 원장을 보관 후 새로 시작하세요:\n"
            "   mv %s %s.%s.bak", state.mode, state_mode,
            STATE_PATH, STATE_PATH, state.mode)
        sys.exit(3)

    logger.info("코인봇 [%s] 현금 %s원, 보유 %d종목", mode, state.cash, len(state.positions))

    if args.live:
        # 계좌 대조 — 원장 현금보다 실제 주문가능 KRW가 적으면 매수가 실패한다
        bal = broker.get_balance()
        if bal.available_cash < Decimal(state.cash):
            logger.warning("⚠️ 계좌 주문가능 KRW %s < 원장 현금 %s — 입금 필요 (매수 실패 예상)",
                           f"{bal.available_cash:,.0f}", f"{Decimal(state.cash):,.0f}")

    universe = load_universe(broker)
    regimes = {sym: asset_regime(broker, sym) for sym in CORE_ASSETS}
    regime, bull_age = or_gate(regimes)  # 위성 게이트 = BTC∪ETH OR (쇼크는 레짐 무관)
    logger.info("위성 게이트(BTC∪ETH): %s (%d일째) | 유니버스 %d종목",
                regime.upper(), bull_age, len(universe))

    breakout = build_preset("breakout_momo")
    now = datetime.now()

    # ---------- 1) 보유 청산 판단 (원장에 있는 것만!) ----------
    for symbol, pos in list(state.positions.items()):
        if pos.strategy == "shock_follow":
            if pos.exit_due and now >= datetime.fromisoformat(pos.exit_due):
                place_sell(broker, state, events, pos, "쇼크 익일 09시 청산", args.live)
            continue
        if pos.strategy in ("btc_core", "core"):
            # 코어는 돌파 규칙이 아니라 해당 자산의 자체 레짐 신호로만 청산
            r = (regimes.get(pos.symbol) or asset_regime(broker, pos.symbol))[0]
            if r != "bull":
                place_sell(broker, state, events, pos, f"레짐 이탈({r}) — 코어 청산", args.live)
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

    # ---------- 2) 코어 홀드 (BTC·ETH 각자 자체 레짐 게이트) ----------
    ledger_eq = ledger_equity(broker, state)  # 복리: 사이징 기준 = 원장 자산 (예산 고정 아님)
    core_each = ledger_eq * CORE_FRACTION / len(CORE_ASSETS)
    for sym in CORE_ASSETS:
        r = regimes[sym][0]
        if r == "bull" and sym not in state.positions:
            amount = min(core_each, Decimal(state.cash) * Decimal("0.95"))
            place_buy(broker, state, events, sym, amount, "core",
                      [f"{sym.replace('KRW-', '')} 자체 앙상블 초록불 — 코어 홀드 진입"],
                      args.live)

    # ---------- 3) 쇼크 이벤트 (btc_shock_alt_follow) ----------
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

    # ---------- 4) bull_breakout 신규 진입 (위성 — 예산의 나머지 50%) ----------
    breakout_held = sum(1 for p in state.positions.values() if p.strategy == "bull_breakout")
    slots = MAX_BREAKOUT_POSITIONS - breakout_held
    if regime == "bull" and bull_age < BREAKOUT_MIN_BULL_AGE:
        logger.info("초록불 %d일째 < %d일 — 위성 진입 대기 (깜빡임 필터)", bull_age, BREAKOUT_MIN_BULL_AGE)
    if regime == "bull" and bull_age >= BREAKOUT_MIN_BULL_AGE and slots > 0:
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
        per_slot = (ledger_eq * (1 - CORE_FRACTION)
                    * Decimal("0.9") / MAX_BREAKOUT_POSITIONS)
        for score, symbol, decision in candidates[:slots]:
            surge = prev_day_surge(broker, symbol)
            if surge >= SURGE_SKIP_PCT:
                logger.info("  %s 스킵 — 전일 +%.0f%% 급등 (부정지식 필터)", symbol, surge)
                continue
            amount = min(per_slot, Decimal(state.cash) * Decimal("0.95"))
            place_buy(broker, state, events, symbol, amount, "bull_breakout",
                      list(decision.reasons) + [f"게이트(BTC∪ETH):{regime}"], args.live)
    elif regime != "bull":
        logger.info("레짐 %s — 신규 돌파 진입 없음", regime)

    # ---------- 5) 자산 스냅샷 + 저장 ----------
    equity = ledger_equity(broker, state)
    events.append("equity", {"equity": str(equity), "cash": state.cash,
                             "n_positions": len(state.positions), "mode": mode,
                             "regime": regime})
    state.save(STATE_PATH)
    logger.info("종료: 자산 %s원 (현금 %s, 보유 %d)", f"{equity:,.0f}",
                f"{Decimal(state.cash):,.0f}", len(state.positions))


if __name__ == "__main__":
    main()
