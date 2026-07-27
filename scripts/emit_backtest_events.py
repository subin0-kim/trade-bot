"""백테스트 결과 → 이벤트 로그 변환.

용도: 대시보드가 읽는 이벤트 스키마의 데모/검증 데이터 생성.
스윙봇이 실제 가동되면 동일 스키마로 실시간 이벤트를 쌓는다.

이벤트 스키마 (data/events/<bot>.jsonl, 한 줄 = JSON 하나):
  공통 필드: ts(ISO), source(봇 이름), type
  type=entry:  symbol, name, quantity, price, strategy, reasons[]
  type=exit:   symbol, quantity, entry_price, exit_price, pnl, pnl_pct,
               win(bool), holding_bars, strategy, reasons[]
  type=equity: equity (일별 스냅샷 — 수익률 곡선의 원천)
  (+기존: signal, order, fill, risk_blocked, policy_blocked, bot_start, bot_stop)

  uv run python scripts/emit_backtest_events.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from regime import RegimeClassifier
from regime_eval import build_us_blocked_dates, fetch_index_daily
from strategy_kit import EntryBlockedDatesStrategy, RegimeMappedStrategy, build_preset
from strategy_kit.sizing import FixedFractionSizer
from universe_backtest import UNIVERSE, WARMUP, fetch_daily

BOT_NAME = "bot-swing-sim"
OUT = Path(f"data/events/{BOT_NAME}.jsonl")

CASH = 1_000_000
MAX_POSITIONS = 4


def main():
    # 챔피언 구성 재현: 현금/connors/macd + 소액 사이징 + US 쇼크필터
    kospi = fetch_index_daily()
    series = RegimeClassifier().classify_series(kospi)

    mapping = {
        "bear": None,
        "sideways": build_preset("connors_rsi2"),
        "bull": build_preset("macd_trend_mtf"),
    }
    for s in mapping.values():
        if s is not None:
            s.sizer = FixedFractionSizer(fraction=0.9 / MAX_POSITIONS)

    strategy = EntryBlockedDatesStrategy(
        "swing_champion",
        RegimeMappedStrategy("regime_switch", {d: r.value for d, r in series.items()}, mapping),
        build_us_blocked_dates("both"),
        reason="US쇼크",
    )

    data = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
        except Exception:
            continue

    print(f"백테스트 실행 ({len(data)}종목, {CASH:,}원, {MAX_POSITIONS}슬롯)...")
    pbt = PortfolioBacktester(
        strategy, higher_tfs=["W"], initial_cash=Decimal(CASH),
        max_positions=MAX_POSITIONS, warmup=WARMUP,
    )
    result = pbt.run(data)
    print(f"수익 {result.summary()['total_return_pct']}% | 거래 {result.summary()['trades']}")

    # --- 이벤트 변환 ---
    events = []

    def strategy_of(reason: str) -> str:
        if "rsi_below" in reason:
            return "connors_rsi2"
        if "macd" in reason:
            return "macd_trend_mtf"
        return "unknown"

    for t in result.trades:
        events.append({
            "ts": t.entry_ts.isoformat(), "source": BOT_NAME, "type": "entry",
            "symbol": t.symbol, "name": UNIVERSE.get(t.symbol, t.symbol),
            "quantity": str(t.quantity), "price": str(t.entry_price),
            "strategy": strategy_of(t.entry_reason),
            "reasons": t.entry_reason.split(" / "),
        })
        if t.exit_ts is not None:
            events.append({
                "ts": t.exit_ts.isoformat(), "source": BOT_NAME, "type": "exit",
                "symbol": t.symbol, "name": UNIVERSE.get(t.symbol, t.symbol),
                "quantity": str(t.quantity),
                "entry_price": str(t.entry_price), "exit_price": str(t.exit_price),
                "pnl": str(t.pnl), "pnl_pct": round(t.pnl_pct, 3),
                "win": t.pnl > 0, "holding_bars": t.bars_held,
                "strategy": strategy_of(t.entry_reason),
                "reasons": t.exit_reason.split(" / "),
            })
    for ts, equity in result.equity_curve:
        events.append({
            "ts": ts.isoformat(), "source": BOT_NAME, "type": "equity",
            "equity": str(equity),
        })

    events.sort(key=lambda e: e["ts"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"이벤트 {len(events)}건 → {OUT}")


if __name__ == "__main__":
    main()
