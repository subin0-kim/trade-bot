"""조건 변수 스크리닝 — "어떤 조건이 전략 유형별 성과를 갈라내는가".

방법: 전략별 백테스트(240m, 전 구간)를 돌려 **모든 거래를 진입 시점의
조건 상태로 태깅** → 조건 상태 × 전략별 거래당 평균 손익을 측정.
좋은 조건 변수 = 상태에 따라 우세 전략이 명확히 갈리고, 전/후반에서 그 방향이 유지되는 것.

조건 후보 (전부 BTC 일봉 기반, t 시점 정보만 사용):
  ma_fast   : MA10/30/60 배열 (코인 스윕 최선이었던 조합)
  roc20     : 20일 수익률 ±5%
  atr_pct   : ATR% 사분위 (변동성 레짐)
  cross_freq: 최근 30일 종가-MA20 교차 횟수 (이마누엘 '교차 빈발=횡보' 원리)
  shock     : 오픈 첫시간 |수익률|≥1% (btc_shock 신호의 조건화)
  adx14     : ADX 수준 (추세 강도)

  uv run python scripts/condition_screening.py
"""

from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import Backtester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from crypto_regime import to_daily
from indicators import adx, atr, closes, roc, sma
from strategy_kit import build_preset, preset_meta

CACHE_5M = Path("data/cache/upbit/5m")
STRATEGIES = {
    "connors_rsi2": "평균회귀", "bb_meanrev": "평균회귀",
    "st_trend": "추세", "macd_trend_mtf": "추세",
    "breakout_momo": "돌파", "ichimoku_tk": "추세",
}


# ---------------------------------------------------------------- 조건 시리즈
def build_conditions(btc_bars_5m) -> dict[str, dict[date, str]]:
    daily = to_daily(btc_bars_5m)
    xs = closes(daily)
    dates = [c.ts.date() for c in daily]
    out: dict[str, dict[date, str]] = defaultdict(dict)

    ma10, ma30, ma60 = sma(xs, 10), sma(xs, 30), sma(xs, 60)
    r20 = roc(xs, 20)
    a14 = atr(daily, 14)
    adx14 = adx(daily, 14)
    ma20 = sma(xs, 20)

    # ATR% 히스토리 (사분위 산출용)
    atr_pct_series = [
        (a14[i] / xs[i] * 100) if (a14[i] is not None and xs[i] > 0) else None
        for i in range(len(xs))
    ]

    for i, d in enumerate(dates):
        # ma_fast
        if None not in (ma10[i], ma30[i], ma60[i]):
            if xs[i] > ma60[i] and ma10[i] > ma30[i]:
                out["ma_fast"][d] = "bull"
            elif xs[i] < ma60[i] and ma10[i] < ma30[i]:
                out["ma_fast"][d] = "bear"
            else:
                out["ma_fast"][d] = "neutral"
        # roc20
        if r20[i] is not None:
            out["roc20"][d] = "up" if r20[i] > 5 else ("down" if r20[i] < -5 else "flat")
        # atr_pct (지금까지의 분포 기준 — look-ahead 방지)
        hist = [v for v in atr_pct_series[max(0, i - 120) : i + 1] if v is not None]
        if atr_pct_series[i] is not None and len(hist) >= 30:
            qs = statistics.quantiles(hist, n=4)
            cur = atr_pct_series[i]
            out["atr_pct"][d] = "low" if cur <= qs[0] else ("high" if cur >= qs[2] else "mid")
        # cross_freq: 최근 30일 종가-MA20 교차 횟수
        if i >= 31 and ma20[i] is not None:
            crosses = 0
            for j in range(i - 29, i + 1):
                if ma20[j] is None or ma20[j - 1] is None:
                    continue
                above_prev = xs[j - 1] > ma20[j - 1]
                above_now = xs[j] > ma20[j]
                if above_prev != above_now:
                    crosses += 1
            out["cross_freq"][d] = "range" if crosses >= 4 else ("trend" if crosses <= 1 else "mid")
        # adx14
        if adx14[i] is not None:
            out["adx14"][d] = "strong" if adx14[i] > 25 else ("weak" if adx14[i] < 20 else "mid")

    # shock: 오픈 첫시간
    by_day = defaultdict(list)
    for b in btc_bars_5m:
        if b.ts.hour == 9:
            by_day[b.ts.date()].append(b)
    for d, bars in by_day.items():
        bars.sort(key=lambda b: b.ts)
        if len(bars) >= 10 and float(bars[0].open) > 0:
            ret = (float(bars[-1].close) / float(bars[0].open) - 1) * 100
            out["shock"][d] = "shock" if abs(ret) >= 1.0 else "calm"
    return out


# ---------------------------------------------------------------- 거래 태깅
def collect_trades(symbols: list[str]) -> list[dict]:
    trades = []
    for symbol in symbols:
        bars = to_timeframe(load_5m(symbol), "240m")
        if len(bars) < 600:
            continue
        for preset in STRATEGIES:
            meta = preset_meta(preset)
            strategy = build_preset(preset)
            higher = ["D"] if meta["higher_tfs"] else []
            if higher:
                for f in strategy.filters:
                    if hasattr(f, "tf"):
                        f.tf = "D"
            bt = Backtester(
                strategy, primary_tf="240m", higher_tfs=higher,
                fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
                warmup=300, view_window=400,
                quantity_step=Decimal("0.00000001"), min_order_value=Decimal(5000),
            )
            try:
                result = bt.run(symbol, bars)
            except Exception:
                continue
            for t in result.closed_trades:
                trades.append({
                    "strategy": preset, "type": STRATEGIES[preset],
                    "entry_date": t.entry_ts.date(), "pnl_pct": t.pnl_pct,
                })
    return trades


def main():
    print("조건 시리즈 구성 (BTC 일봉)...")
    conditions = build_conditions(load_5m("KRW-BTC"))
    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    print(f"거래 수집: {len(symbols)}종목 × {len(STRATEGIES)}전략 @240m ...")
    trades = collect_trades(symbols)
    print(f"수집된 거래 {len(trades):,}건\n")

    all_dates = sorted({t["entry_date"] for t in trades})
    mid = all_dates[len(all_dates) // 2]

    for cond_name, series in conditions.items():
        print(f"━━━ 조건: {cond_name} ━━━")
        states = sorted(set(series.values()))
        header = f"{'상태':<9}" + "".join(f"{s:>14}" for s in sorted(set(STRATEGIES.values()))) + f"{'우세유형(전/후반)':>20}"
        print(header)
        for state in states:
            row = {"평균회귀": [], "추세": [], "돌파": []}
            halves = {"h1": {"평균회귀": [], "추세": [], "돌파": []},
                      "h2": {"평균회귀": [], "추세": [], "돌파": []}}
            for t in trades:
                if series.get(t["entry_date"]) != state:
                    continue
                row[t["type"]].append(t["pnl_pct"])
                half = "h1" if t["entry_date"] < mid else "h2"
                halves[half][t["type"]].append(t["pnl_pct"])
            cells = ""
            for typ in sorted(row):
                vals = row[typ]
                cells += f"{statistics.mean(vals):>+9.2f}({len(vals):>4})" if vals else f"{'—':>14}"
            best = {}
            for h in ("h1", "h2"):
                cand = {k: statistics.mean(v) for k, v in halves[h].items() if len(v) >= 10}
                best[h] = max(cand, key=cand.get) if cand else "—"
            agree = "✓" if best["h1"] == best["h2"] and best["h1"] != "—" else "✗"
            print(f"{state:<9}{cells}{best['h1']:>8}/{best['h2']:<6}{agree}")
        print()


if __name__ == "__main__":
    main()
