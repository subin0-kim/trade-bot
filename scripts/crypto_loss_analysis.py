"""코인 돌파 전략 패배 분석 — 진입 시점에 알 수 있었던 것은 무엇인가.

앙상블+breakout_momo 171건(승률 34.5%)의 패배를 해부한다:
  1. 청산 사유별 구조 (손절/트레일링/시간청산/레짐)
  2. 진입 시점 피처를 승/패 대조 — 신호봉까지의 정보만 사용 (look-ahead 없음)
  3. 분리력 있는 피처의 사분위별 승률/평균 손익

피처 (신호봉 = 체결봉 직전 240분봉, 그 시점까지의 데이터만):
  돌파의 질: vol_ratio(거래량배수), margin(돌파폭%), body(몸통비), uwick(윗꼬리비)
  과열도:    rsi14, ext20(20봉 상승폭%), dist_ma20(MA20 이격%), consec_up(연속양봉)
  추세/변동: adx14, atr_pct
  맥락:      hour(신호봉 시각), btc_roc5/btc_roc20(진입일 BTC 모멘텀), votes(앙상블 표수),
             bull_age(초록불 지속일)

  uv run python scripts/crypto_loss_analysis.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from crypto_ensemble_verify import CACHE_5M, ensemble_flags
from crypto_regime import to_daily
from indicators import adx, atr, closes, roc, rsi, sma
from strategy_kit import RegimeMappedStrategy, build_preset


def btc_context():
    """일자별 BTC 피처: roc5, roc20, 앙상블 표수, 초록불 지속일."""
    daily = to_daily(load_5m("KRW-BTC"))
    xs = closes(daily)
    r5, r20 = roc(xs, 5), roc(xs, 20)
    ens = ensemble_flags(daily)
    from indicators import supertrend
    st, _ = supertrend(daily, 10, 3.0)
    ma10, ma30 = sma(xs, 10), sma(xs, 30)
    r30 = roc(xs, 30)
    ctx = {}
    bull_age = 0
    for i, c in enumerate(daily):
        d = c.ts.date()
        votes = sum([
            1 if (r30[i] is not None and r30[i] > 0) else 0,
            1 if st[i] == 1 else 0,
            1 if (ma10[i] is not None and ma30[i] is not None and ma10[i] > ma30[i]) else 0,
        ])
        bull_age = bull_age + 1 if ens.get(d) else 0
        ctx[d] = {"btc_roc5": r5[i], "btc_roc20": r20[i], "votes": votes, "bull_age": bull_age}
    return ctx


def entry_features(bars, i0, ctx):
    """i0 = 체결봉 인덱스. 신호봉(i0-1)까지의 정보만 사용."""
    s = i0 - 1  # 신호봉
    if s < 30:
        return None
    sig = bars[s]
    hist = bars[: s + 1]
    xs = closes(hist)
    vols = [float(b.volume) for b in hist]
    vol20 = statistics.mean(vols[-21:-1])
    rng = float(sig.high - sig.low) or 1e-9
    prior_high = max(float(b.high) for b in bars[s - 20 : s])
    a = atr(hist, 14)
    ax = adx(hist, 14)
    r = rsi(xs, 14)
    m20 = sma(xs, 20)
    consec = 0
    for k in range(s, 0, -1):
        if float(bars[k].close) > float(bars[k - 1].close):
            consec += 1
        else:
            break
    d = sig.ts.date()
    c = ctx.get(d, {})
    return {
        "vol_ratio": vols[-1] / vol20 if vol20 else None,
        "margin": (float(sig.close) / prior_high - 1) * 100,
        "body": (float(sig.close) - float(sig.open)) / rng,
        "uwick": (float(sig.high) - float(sig.close)) / rng,
        "rsi14": r[-1],
        "ext20": (xs[-1] / xs[-21] - 1) * 100 if len(xs) > 21 else None,
        "dist_ma20": (xs[-1] / m20[-1] - 1) * 100 if m20[-1] else None,
        "consec_up": consec,
        "adx14": ax[-1] if ax else None,
        "atr_pct": a[-1] / xs[-1] * 100 if a and a[-1] else None,
        "hour": sig.ts.hour,
        "btc_roc5": c.get("btc_roc5"),
        "btc_roc20": c.get("btc_roc20"),
        "votes": c.get("votes"),
        "bull_age": c.get("bull_age"),
    }


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    states = {d: ("bull" if f else "off") for d, f in ens.items()}
    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    data = {s: to_timeframe(load_5m(s), "240m") for s in symbols}
    data = {s: b for s, b in data.items() if len(b) > 600}

    strat = RegimeMappedStrategy("ens", states, {"bull": build_preset("breakout_momo"), "off": None})
    pbt = PortfolioBacktester(strat, max_positions=8, warmup=300, view_window=400,
                              fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX,
                              slippage_rate=COIN_SLIPPAGE, initial_cash=Decimal(50_000_000))
    result = pbt.run(data)
    closed = [t for t in result.trades if t.exit_ts is not None]

    # ---------- 1) 청산 사유 구조 ----------
    print(f"=== 청산 사유별 구조 (총 {len(closed)}건) ===")
    groups: dict[str, list] = {}
    for t in closed:
        key = t.exit_reason.split(":")[0].split(" ")[0][:12] or "?"
        groups.setdefault(key, []).append(t.pnl_pct)
    for k, pnls in sorted(groups.items(), key=lambda kv: sum(kv[1])):
        wins = sum(1 for p in pnls if p > 0)
        print(f"  {k:<14} {len(pnls):>3}건 | 승 {wins:>3} | 평균 {statistics.mean(pnls):+7.2f}% | "
              f"합계 {sum(pnls):+8.1f}%p")

    # ---------- 2) 피처 계산 ----------
    ctx = btc_context()
    rows = []
    for t in closed:
        bars = data[t.symbol]
        idx = {b.ts: i for i, b in enumerate(bars)}
        i0 = idx.get(t.entry_ts)
        if i0 is None:
            continue
        f = entry_features(bars, i0, ctx)
        if f:
            rows.append((t, f))

    feats = list(rows[0][1].keys())
    print(f"\n=== 진입 피처: 승({sum(1 for t,_ in rows if t.pnl_pct>0)}) vs "
          f"패({sum(1 for t,_ in rows if t.pnl_pct<=0)}) 중앙값 ===")
    print(f"{'피처':<12}{'승 중앙값':>10}{'패 중앙값':>10}")
    for k in feats:
        w = [f[k] for t, f in rows if t.pnl_pct > 0 and f[k] is not None]
        l = [f[k] for t, f in rows if t.pnl_pct <= 0 and f[k] is not None]
        if not w or not l:
            continue
        print(f"{k:<14}{statistics.median(w):>9.2f}{statistics.median(l):>9.2f}")

    # ---------- 3) 사분위별 승률/평균pnl ----------
    print("\n=== 피처 사분위(Q1=낮음 → Q4=높음)별 [승률% | 평균pnl%] ===")
    for k in feats:
        vals = [(f[k], t.pnl_pct) for t, f in rows if f[k] is not None]
        if len(vals) < 40:
            continue
        vals.sort(key=lambda v: v[0])
        qs = [vals[i * len(vals) // 4 : (i + 1) * len(vals) // 4] for i in range(4)]
        cells = []
        for q in qs:
            pn = [p for _, p in q]
            wr = sum(1 for p in pn if p > 0) / len(pn) * 100
            cells.append(f"{wr:4.0f}%|{statistics.mean(pn):+6.2f}")
        edges = [vals[i * len(vals) // 4][0] for i in range(1, 4)]
        print(f"{k:<12} {' / '.join(cells)}   (경계 {', '.join(f'{e:.1f}' for e in edges)})")


if __name__ == "__main__":
    main()
