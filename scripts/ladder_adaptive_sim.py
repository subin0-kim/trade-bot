"""레짐 적응형 타임아웃 사다리 — bull엔 길게 기다리고 off엔 빨리 도망.

타임아웃을 체결일의 레짐(BTC∪ETH OR, 전일 완성 플래그 — 코인봇 신호 재사용)으로 분기:
  A: bull 240분 / off 120분
  B: bull 360분 / off 120분
라우터 k=14 / k=4 각각. 기타 사양은 채택안 (2단 -2/-5, 5분 재산정, 70% 회복, 7%×14).

  uv run python scripts/ladder_adaptive_sim.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

import ladder_router_sim as L
from backtest_upbit import load_5m
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from flash_dip_portfolio_sim import simulate

REC = 0.7
MAX_TO = 360


def build_regime():
    btc_f = ensemble_flags(to_daily(load_5m("KRW-BTC")))
    eth_f = ensemble_flags(to_daily(load_5m("KRW-ETH")))
    dates = sorted(set(btc_f) | set(eth_f))
    # 전일 완성 플래그가 오늘을 지배 (라이브 동일)
    return {d + timedelta(days=1): (btc_f.get(d, False) or eth_f.get(d, False))
            for d in dates}


def run_events(data, k_orders, bull_flags, to_bull, to_off):
    all_ts = sorted({b.ts for d in data.values() for b in d["bars"]})
    state = {(s, X): {"pos_until": -1} for s in data for X in L.DEPTHS}
    ref = {}
    events = []
    day_close = {}
    for sym, d in data.items():
        dc = day_close.setdefault(sym, {})
        for b in d["bars"]:
            dc[b.ts.date()] = float(b.close)
    active = set()
    for ts in all_ts:
        if ts.minute % L.REF_N == 0:
            for sym, d in data.items():
                i = d["idx"].get(ts)
                if i is None or i == 0:
                    continue
                for X in L.DEPTHS:
                    ref[(sym, X)] = d["close"][i - 1] * (1 - X / 100)
        if k_orders is not None:
            ranks = []
            for (sym, X), lv in ref.items():
                d = data[sym]
                i = d["idx"].get(ts)
                if i is None or i < 1 or lv is None:
                    continue
                if i <= state[(sym, X)]["pos_until"]:
                    continue
                ranks.append((d["close"][i - 1] / lv - 1, sym, X))
            ranks.sort()
            active = {(s, X) for _, s, X in ranks[:k_orders]}
        for sym, d in data.items():
            i = d["idx"].get(ts)
            if i is None or i < 1 or i >= len(d["bars"]) - MAX_TO - 2:
                continue
            for X in L.DEPTHS:
                lv = ref.get((sym, X))
                if lv is None:
                    continue
                st = state[(sym, X)]
                if i <= st["pos_until"]:
                    continue
                if k_orders is not None and (sym, X) not in active:
                    continue
                if d["low"][i] <= lv:
                    timeout = to_bull if bull_flags.get(ts.date(), False) else to_off
                    entry = min(lv, d["close"][i - 1])
                    tgt = entry * (1 + REC * X / 100)
                    end = min(i + timeout, len(d["bars"]) - 1)
                    px, off = d["close"][end], end - i
                    for j in range(i + 1, end + 1):
                        if d["high"][j] >= tgt:
                            px, off = tgt, j - i
                            break
                    events.append({"symbol": f"{sym}#{X}", "ts": ts, "entry": entry,
                                   "exit_ts": d["bars"][i + off].ts, "exit": px})
                    st["pos_until"] = i + off
    tagged = {k2: day_close[k2.split("#")[0]] for k2 in {e["symbol"] for e in events}}
    events.sort(key=lambda e: e["ts"])
    return events, tagged, all_ts[-1]


def main():
    data = L.load_all()
    flags = build_regime()
    for k in (14, 4):
        for label, tb, to in (("A bull240/off120", 240, 120), ("B bull360/off120", 360, 120)):
            events, dc, last = run_events(data, k, flags, tb, to)
            end = last.date()
            boundary = end - timedelta(days=365)
            nets = [(e["exit"] / e["entry"] - 1) * 100 - 0.2 for e in events]
            wins = sum(1 for n in nets if n > 0) / len(nets) * 100
            out = []
            rets = []
            for plabel, s, e in (("상승년", boundary - timedelta(days=365), boundary),
                                 ("하락년", boundary + timedelta(days=1), end)):
                r = simulate(events, dc, s, e, 0.07, 14)
                rets.append(r["ret"])
                out.append(f"{plabel} {r['ret']:+6.1f}% (MDD {r['mdd']:4.1f})")
            comp = ((1 + rets[0] / 100) * (1 + rets[1] / 100) - 1) * 100
            print(f"[k={k:>2}] {label}: n={len(events)} | 승률 {wins:.0f}% | "
                  f"기대값 {statistics.mean(nets):+.3f}% | {' | '.join(out)} | 2년 {comp:+.1f}%",
                  flush=True)


if __name__ == "__main__":
    main()
