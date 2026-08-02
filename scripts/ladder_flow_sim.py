"""체결강도(바이낸스 taker buy) 기반 업그레이드 — 설계 A(극단 회수)·B(흐름 타임아웃)·C(매물대 목표) 조합.

임계 사전 고정 (스윕 부채 방지):
  A: 체결 순간 직전 5분 바이낸스 매수 체결 비율 < 0.30 → 주문 회수(체결 무효)
  B: 체결 +15분 시점, 직전 15분 매수 비율 < 0.35 → 타임아웃을 체결+60분으로 단축
  C: 회복 경로 최대 매물대(3일) 직전 목표 (회복의 43% 이상일 때만)

  uv run python scripts/ladder_flow_sim.py
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, "scripts")

import ladder_router_sim as L
import ladder_adaptive_sim as A_
from flash_dip_portfolio_sim import simulate

DEPTHS = [3.0, 5.0]
COST = 0.2
PROF_N = 4320
BIN = 0.0025
PAIRS = {"KRW-ETH": "ETHUSDT", "KRW-XRP": "XRPUSDT", "KRW-SOL": "SOLUSDT",
         "KRW-TRX": "TRXUSDT", "KRW-DOGE": "DOGEUSDT", "KRW-LINK": "LINKUSDT",
         "KRW-XLM": "XLMUSDT", "KRW-ADA": "ADAUSDT", "KRW-BCH": "BCHUSDT",
         "KRW-HBAR": "HBARUSDT", "KRW-AVAX": "AVAXUSDT", "KRW-SUI": "SUIUSDT",
         "KRW-SHIB": "SHIBUSDT", "KRW-UNI": "UNIUSDT", "KRW-NEAR": "NEARUSDT"}


def load_flow():
    """심볼 → {ts_str: (v, tb)}"""
    out = {}
    for krw, pair in PAIRS.items():
        path = Path(f"data/cache/binance/1m/{pair}.jsonl")
        if not path.exists():
            continue
        m = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
                m[d["ts"]] = (float(d["v"]), float(d["tb"]))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        out[krw] = m
    return out


def buy_ratio(flow_m, ts, minutes):
    v = tb = 0.0
    for k in range(minutes):
        row = flow_m.get((ts - timedelta(minutes=k)).strftime("%Y-%m-%dT%H:%M:%S"))
        if row:
            v += row[0]
            tb += row[1]
    return tb / v if v > 0 else None


def main():
    data = L.load_all()
    flags = A_.build_regime()
    flow = load_flow()
    vols = {sym: [float(b.volume) for b in d["bars"]] for sym, d in data.items()}
    day_close = {}
    for sym, d in data.items():
        dc = day_close.setdefault(sym, {})
        for b in d["bars"]:
            dc[b.ts.date()] = float(b.close)

    def vp_target(sym, i, entry, full_tgt):
        d = data[sym]
        v = vols[sym]
        hist = collections.Counter()
        for j in range(max(0, i - PROF_N), i):
            px = d["close"][j]
            if entry < px < full_tgt:
                hist[int(px / (entry * BIN))] += v[j] * px
        if not hist:
            return full_tgt
        node = (max(hist, key=hist.get) + 0.5) * entry * BIN
        if (node / entry - 1) >= 0.43 * (full_tgt / entry - 1):
            return min(full_tgt, node * 0.999)
        return full_tgt

    def run(use_a, use_b, use_c):
        all_ts = sorted({b.ts for d in data.values() for b in d["bars"]})
        state = {(s, X): -1 for s in data for X in DEPTHS}
        ref = {}
        events = []
        for ts in all_ts:
            if ts.minute % 5 == 0:
                for sym, d in data.items():
                    i = d["idx"].get(ts)
                    if i is None or i == 0:
                        continue
                    for X in DEPTHS:
                        ref[(sym, X)] = d["close"][i - 1] * (1 - X / 100)
            ranks = []
            for (sym, X), lv in ref.items():
                d = data[sym]
                i = d["idx"].get(ts)
                if i is None or i < 1 or lv is None or i <= state[(sym, X)]:
                    continue
                ranks.append((d["close"][i - 1] / lv - 1, sym, X))
            ranks.sort()
            active = {(s, X) for _, s, X in ranks[:14]}
            for sym, d in data.items():
                i = d["idx"].get(ts)
                if i is None or i < 1 or i >= len(d["bars"]) - 363:
                    continue
                for X in DEPTHS:
                    lv = ref.get((sym, X))
                    if lv is None or (sym, X) not in active or i <= state[(sym, X)]:
                        continue
                    if d["low"][i] <= lv:
                        fm = flow.get(sym)
                        if use_a and fm:
                            br = buy_ratio(fm, ts, 5)
                            if br is not None and br < 0.30:
                                continue          # 주문 회수 — 체결 무효
                        timeout = 360 if flags.get(ts.date(), False) else 120
                        entry = min(lv, d["close"][i - 1])
                        full_tgt = entry * (1 + 0.7 * X / 100)
                        tgt = vp_target(sym, i, entry, full_tgt) if use_c else full_tgt
                        end = min(i + timeout, len(d["bars"]) - 1)
                        if use_b and fm and timeout > 60:
                            br15 = buy_ratio(fm, d["bars"][min(i + 15, end)].ts, 15)
                            if br15 is not None and br15 < 0.35:
                                end = min(i + 60, end)
                        px, off = d["close"][end], end - i
                        for j in range(i + 1, end + 1):
                            if d["high"][j] >= tgt:
                                px, off = tgt, j - i
                                break
                        events.append({"symbol": f"{sym}#{X}", "ts": ts, "entry": entry,
                                       "exit_ts": d["bars"][i + off].ts, "exit": px})
                        state[(sym, X)] = i + off
        tagged = {k2: day_close[k2.split("#")[0]] for k2 in {e["symbol"] for e in events}}
        events.sort(key=lambda e: e["ts"])
        return events, tagged

    def rep(tag, evs, tagged):
        per_day = collections.Counter(e["ts"].date() for e in evs)
        disaster = {dd for dd, c in per_day.items() if c >= 8}
        for scope, sel in (("전체", evs), ("평시", [e for e in evs if e["ts"].date() not in disaster])):
            nets = [(e["exit"] / e["entry"] - 1) * 100 - COST for e in sel]
            wins = sum(1 for n in nets if n > 0) / len(nets) * 100
            last = max(e["exit_ts"] for e in sel).date()
            b = last - timedelta(days=365)
            rets, out = [], []
            for label, s, e2 in (("상승년", b - timedelta(days=365), b),
                                 ("하락년", b + timedelta(days=1), last)):
                r = simulate(sel, tagged, s, e2, 0.10, 10)
                rets.append(r["ret"])
                out.append(f"{label} {r['ret']:+6.1f}% (MDD {r['mdd']:4.1f})")
            comp = ((1 + rets[0] / 100) * (1 + rets[1] / 100) - 1) * 100
            print(f"[{tag} | {scope}] n={len(sel)} | 승률 {wins:.0f}% | "
                  f"건당 {statistics.mean(nets):+.3f}% | {' | '.join(out)} | 2년 {comp:+.1f}%",
                  flush=True)

    print("(기준: 현행 +61.2/+15.1, C단독 +62.7/+16.2)")
    for tag, a, b_, c in (("B 흐름타임아웃", False, True, False),
                          ("A 극단회수", True, False, False),
                          ("B+C", False, True, True),
                          ("A+B+C", True, True, True)):
        evs, tagged = run(a, b_, c)
        rep(tag, evs, tagged)


if __name__ == "__main__":
    main()
