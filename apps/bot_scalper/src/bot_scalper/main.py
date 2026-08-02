"""단타봇 — 2단 지정가 사다리 (급락 유동성 공백 수확).

확정 사양 (wiki/shared/strategies/strategy-candidates.md 실측 5~9, 2026-08-01):
  유니버스 시총15+ETH × 사다리 -3%/-5% (기준가 5분 재산정) × 근접도 라우터(주문 14)
  × 매물대 목표 청산(기본 낙폭 70% 회복, 경로상 최대 매물대 직전) × 적응형 타임아웃
  (bull 360분/off 120분, 코인봇 레짐 재사용) × 무손절 × 원장 자산 비례 슬롯.
  방어: 광폭 하락 매수중지(16종 중 8종이 5분 -2%↓) + 유의·주의 종목 제외(+플래그 로깅).

사이징 프로파일 (--profile):
  insurance 20%×5 | aggressive 25%×4 | very-aggressive 33%×3 | high-risk 50%×2(기본)

  uv run bot-scalper --once            # 1사이클 dry-run (검증용)
  uv run bot-scalper                   # 상주 루프 dry-run (1분 주기)
  uv run bot-scalper --live --yes      # 실주문 (무인 승인)
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from broker_upbit import UpbitApiError, UpbitBroker
from trading_core import JsonlEventLog, OrderRequest, OrderSide, OrderType

from .state import Position, ScalperState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot_scalper")

BOT_NAME = "bot_scalper"
DATA_DIR = Path("data")
STATE_PATH = DATA_DIR / "state" / f"{BOT_NAME}.json"
EVENTS_PATH = DATA_DIR / "events" / f"{BOT_NAME}.jsonl"
FLAGS_PATH = DATA_DIR / "events" / "market_flags.jsonl"   # 유의·주의 이력 (선수집 자산)

TIERS = [3.0, 5.0]
REC = 0.7                 # 기본 회복 목표 (낙폭의 70%)
MAX_ORDERS = 14           # 근접도 라우터 동시 주문 상한
REF_MIN = 5               # 기준가 재산정 주기(분)
BREADTH_N, BREADTH_PCT = 8, -2.0    # 광폭 중지: 8종 이상 5분 -2%↓
PROFILE = {"insurance": (Decimal("0.20"), 5), "aggressive": (Decimal("0.25"), 4),
           "very-aggressive": (Decimal("0.33"), 3), "high-risk": (Decimal("0.50"), 2)}
PROF_MIN = 4320           # 매물대 히스토그램 창 (3일)
VP_BIN = 0.0025           # 매물대 빈 폭 (0.25%)
FEE = Decimal("0.0005")


def universe(broker: UpbitBroker) -> list[str]:
    from bot_coin.main import TOP_MCAP_ALTS
    markets = set(broker.list_krw_markets())
    return [s for s in sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"}) if s in markets]


def bull_regime(broker: UpbitBroker) -> bool:
    """BTC∪ETH OR 게이트 (코인봇 재사용) — 적응형 타임아웃용."""
    from bot_coin.main import asset_regime, or_gate
    regimes = {s: asset_regime(broker, s) for s in ("KRW-BTC", "KRW-ETH")}
    regime, _ = or_gate(regimes)
    return regime == "bull"


def market_excludes(broker: UpbitBroker) -> set[str]:
    """유의(warning)·주의(caution) 종목 제외 + 플래그 스냅샷 로깅."""
    try:
        rows = broker.client.get("/v1/market/all", {"is_details": "true"})
    except UpbitApiError as e:
        logger.warning("마켓 경보 조회 실패: %s", str(e)[:60])
        return set()
    bad, flagged = set(), []
    for r in rows:
        ev = r.get("market_event") or {}
        cautions = [k for k, v in (ev.get("caution") or {}).items() if v]
        if ev.get("warning") or cautions:
            flagged.append({"market": r["market"], "warning": bool(ev.get("warning")),
                            "caution": cautions})
            bad.add(r["market"])
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FLAGS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(), "flags": flagged},
                           ensure_ascii=False) + "\n")
    return bad


class MinuteHistory:
    """심볼별 1분봉 롤링 이력 — 매물대·광폭 판정·5분 수익률의 데이터 소스."""

    def __init__(self, broker: UpbitBroker, symbols: list[str]):
        self.broker = broker
        self.bars: dict[str, collections.deque] = {}
        for s in symbols:
            got: list = []
            to = None
            while len(got) < PROF_MIN:
                chunk = broker.get_minute_candles(s, to_time=to, unit=1, count=200)
                if not chunk:
                    break
                got = chunk + got
                to = chunk[0].ts.strftime("%Y-%m-%dT%H:%M:%S")
            self.bars[s] = collections.deque(got[-PROF_MIN:], maxlen=PROF_MIN)
        logger.info("1분봉 이력 적재 완료 (%d종 × ~%d분)", len(symbols), PROF_MIN)

    def update(self, symbol: str) -> None:
        recent = self.broker.get_minute_candles(symbol, unit=1, count=5)
        dq = self.bars[symbol]
        known = {b.ts for b in list(dq)[-10:]}
        for b in recent:
            if b.ts not in known:
                dq.append(b)

    def r5(self, symbol: str) -> float | None:
        dq = self.bars[symbol]
        if len(dq) < 6:
            return None
        return (float(dq[-1].close) / float(dq[-6].close) - 1) * 100

    def vp_target(self, symbol: str, entry: Decimal, full_tgt: Decimal) -> Decimal:
        """회복 경로(진입가~완전목표) 안의 최대 매물대 직전 가격. 없으면 완전목표."""
        hist: collections.Counter = collections.Counter()
        e, ft = float(entry), float(full_tgt)
        for b in self.bars[symbol]:
            px = float(b.close)
            if e < px < ft:
                hist[int(px / (e * VP_BIN))] += float(b.volume) * px
        if not hist:
            return full_tgt
        node = (max(hist, key=hist.get) + 0.5) * e * VP_BIN
        if (node / e - 1) >= 0.43 * (ft / e - 1):
            return min(full_tgt, Decimal(str(node)) * Decimal("0.999"))
        return full_tgt


def main() -> None:
    parser = argparse.ArgumentParser(description="단타봇 — 2단 지정가 사다리")
    parser.add_argument("--profile", choices=list(PROFILE), default="high-risk",
                        help="사이징 (기본 high-risk 50%%×2 — 최초 드라이런 셋업)")
    parser.add_argument("--budget", type=int, default=1_000_000, help="원장 초기 시드(원)")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--yes", action="store_true", help="live 무인 승인")
    parser.add_argument("--once", action="store_true", help="1사이클만 (검증용)")
    args = parser.parse_args()

    mode = "live" if args.live else "dry-run"
    if args.live and not args.yes:
        if input("실계좌 실주문입니다. 'yes' 입력: ") != "yes":
            raise SystemExit(2)
    frac, slots = PROFILE[args.profile]
    broker = UpbitBroker()
    state = ScalperState.load(STATE_PATH, Decimal(args.budget), mode)
    events = JsonlEventLog(EVENTS_PATH, source=BOT_NAME)
    syms = universe(broker)
    logger.info("단타봇 [%s] %s (%s×%d) | 유니버스 %d종 | 원장 현금 %s원",
                mode.upper(), args.profile, frac, slots, len(syms),
                f"{Decimal(state.cash):,.0f}")

    hist = MinuteHistory(broker, syms)
    refs: dict[tuple[str, float], Decimal] = {}
    is_bull = bull_regime(broker)
    excludes = market_excludes(broker)
    last_regime = last_flags = datetime.now()
    logger.info("레짐 %s | 경보 제외 %d종", "BULL" if is_bull else "OFF",
                len(excludes & set(syms)))

    while True:
        now = datetime.now()
        try:
            if (now - last_regime) > timedelta(hours=1):
                is_bull = bull_regime(broker)
                last_regime = now
            if (now - last_flags) > timedelta(minutes=30):
                excludes = market_excludes(broker)
                last_flags = now
            for s in syms:
                hist.update(s)
            if now.minute % REF_MIN == 0 or not refs:
                for s in syms:
                    if hist.bars[s]:
                        base = Decimal(str(hist.bars[s][-1].close))
                        for X in TIERS:
                            refs[(s, X)] = base * (1 - Decimal(X) / 100)

            breadth = sum(1 for s in syms
                          if (r := hist.r5(s)) is not None and r <= BREADTH_PCT)
            halted = breadth >= BREADTH_N
            if halted:
                logger.warning("광폭 하락 %d종 — 신규 매수 중지", breadth)

            # ---------- 청산: 목표 도달 / 타임아웃 ----------
            equity = Decimal(state.cash)
            for key, pos in list(state.positions.items()):
                q = broker.get_quote(pos.symbol).price
                equity += q * Decimal(pos.quantity)
                tgt = Decimal(pos.target_price)
                reason, exit_px = None, None
                if q >= tgt:
                    reason, exit_px = f"매물대 목표 도달 ({tgt:,.0f})", tgt
                elif now >= datetime.fromisoformat(pos.timeout_at):
                    reason, exit_px = "타임아웃 청산", q
                if reason:
                    qty = Decimal(pos.quantity)
                    if args.live:
                        order = broker.place_order(OrderRequest(
                            symbol=pos.symbol, side=OrderSide.SELL, quantity=qty,
                            order_type=OrderType.MARKET))
                        filled, avg, paid_fee = broker.settle_order(order)
                        if filled <= 0:
                            continue
                        qty, exit_px = filled, (avg or exit_px)
                        fee = paid_fee if paid_fee is not None else exit_px * qty * FEE
                    else:
                        fee = exit_px * qty * FEE
                    proceeds = exit_px * qty - fee
                    cost = Decimal(pos.entry_price) * qty
                    pnl = proceeds - cost * (1 + FEE)
                    state.cash = str(Decimal(state.cash) + proceeds)
                    del state.positions[key]
                    state.save(STATE_PATH)
                    logger.info("매도 %s: %+.2f%% — %s", key, float(pnl / cost * 100), reason)
                    events.append("exit", {
                        "symbol": pos.symbol, "tier": pos.tier, "quantity": str(qty),
                        "entry_price": pos.entry_price, "exit_price": str(exit_px),
                        "pnl": str(pnl), "pnl_pct": round(float(pnl / cost * 100), 3),
                        "win": pnl > 0, "strategy": "ladder", "reasons": [reason],
                        "mode": mode.upper()})

            # ---------- 라우터: 근접도 상위 주문 + 체결 판정 ----------
            slot_size = equity * frac
            free_slots = slots - len(state.positions)
            n_orders = (min(MAX_ORDERS, int(Decimal(state.cash) / slot_size))
                        if slot_size > 0 else 0)
            if not halted and free_slots > 0 and n_orders > 0:
                ranks = []
                for (s, X), lv in refs.items():
                    if s in excludes or f"{s}#{X}" in state.positions:
                        continue
                    if not hist.bars[s] or lv <= 0:
                        continue
                    cur = Decimal(str(hist.bars[s][-1].close))
                    ranks.append((float(cur / lv - 1), s, X, lv, cur))
                ranks.sort()
                for _, s, X, lv, cur in ranks[:n_orders]:
                    if free_slots <= 0:
                        break
                    low = Decimal(str(hist.bars[s][-1].low))
                    if low > lv:
                        continue          # 지정가 미관통 — 대기 유지
                    entry = min(lv, cur)
                    qty = (slot_size / entry).quantize(Decimal("0.00000001"))
                    if entry * qty < 5000 or entry * qty > Decimal(state.cash):
                        continue
                    if args.live:
                        order = broker.place_order(OrderRequest(
                            symbol=s, side=OrderSide.BUY, quantity=qty,
                            order_type=OrderType.LIMIT, price=entry))
                        filled, avg, paid_fee = broker.settle_order(order)
                        if filled <= 0:
                            continue
                        qty, entry = filled, (avg or entry)
                        fee = paid_fee if paid_fee is not None else entry * qty * FEE
                    else:
                        fee = entry * qty * FEE
                    full_tgt = entry * (1 + Decimal(str(REC * X)) / 100)
                    tgt = hist.vp_target(s, entry, full_tgt)
                    timeout_min = 360 if is_bull else 120
                    state.cash = str(Decimal(state.cash) - entry * qty - fee)
                    state.positions[f"{s}#{X}"] = Position(
                        symbol=s, tier=X, quantity=str(qty), entry_price=str(entry),
                        entry_ts=now.isoformat(), target_price=str(tgt),
                        timeout_at=(now + timedelta(minutes=timeout_min)).isoformat())
                    state.save(STATE_PATH)
                    free_slots -= 1
                    logger.info("매수 %s#%s: %s @ %s → 목표 %s (타임아웃 %d분)",
                                s.replace("KRW-", ""), X, qty, f"{entry:,.0f}",
                                f"{Decimal(str(tgt)):,.2f}", timeout_min)
                    events.append("entry", {
                        "symbol": s, "tier": X, "quantity": str(qty),
                        "entry_price": str(entry), "target_price": str(tgt),
                        "timeout_min": timeout_min, "strategy": "ladder",
                        "reasons": [f"사다리 -{X}% 관통 체결",
                                     f"레짐:{'bull' if is_bull else 'off'}",
                                     f"광폭:{breadth}종"],
                        "mode": mode.upper()})

            events.append("equity", {"equity": str(equity), "cash": state.cash,
                                     "n_positions": len(state.positions), "mode": mode})
        except UpbitApiError as e:
            logger.warning("API 오류 — 이번 사이클 건너뜀: %s", str(e)[:80])
        except Exception:
            logger.exception("사이클 오류 — 계속")

        if args.once:
            break
        time.sleep(max(5, 60 - datetime.now().second))


if __name__ == "__main__":
    main()
