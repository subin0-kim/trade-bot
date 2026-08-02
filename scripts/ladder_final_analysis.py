"""단타봇 확정 사양의 최종 분석 — 분할 익절 / 패배 해부 / 특수일 분리.

사용자 요구 (2026-08-01):
  1. 청산 비교: 현행(70% 전량) vs 분할(70%에서 절반 + 잔여 100% 복구 목표)
  2. 패배 해부: 승률 ~80%인데 패배가 3:1로 큼 — 패배를 가르는 체결 시점 특징 탐색
  3. 모든 수치를 특수일(재난일) 제외/포함으로 이중 보고 — 단타봇의 목표는
     "평소의 수익"이지 특정일 의존이 아님. 특수일 = 하루 체결 ≥8건인 날 (기계적 정의)

사양: 16종 × -3/-5 2단 × 5분 재산정 × 라우터 k=14 × 적응형(bull360/off120) × 10%×10.

  uv run python scripts/ladder_final_analysis.py
"""

from __future__ import annotations

import collections
import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

import ladder_router_sim as L
import ladder_adaptive_sim as A
from flash_dip_portfolio_sim import simulate
from minute1_backtest import load_1m

COST = 0.2
DEPTHS = [3.0, 5.0]
REC = 0.7
DISASTER_MIN_FILLS = 8


def build_events():
    data = L.load_all()
    flags = A.build_regime()
    # 부가 피처용: 거래량, BTC 1분 수익률
    vols = {}
    for sym, d in data.items():
        vols[sym] = [float(b.volume) for b in d["bars"]]
    btc = load_1m("KRW-BTC")
    btc_close = {b.ts: float(b.close) for b in btc}
    btc_r5 = {}
    for b in btc:
        prev = btc_close.get(b.ts - timedelta(minutes=5))
        if prev:
            btc_r5[b.ts] = (float(b.close) / prev - 1) * 100
    # 심볼별 전일 수익률
    prev_ret = {}
    for sym, d in data.items():
        by_day = {}
        for k, b in enumerate(d["bars"]):
            by_day[b.ts.date()] = k
        days = sorted(by_day)
        for k in range(1, len(days)):
            c1 = d["close"][by_day[days[k]]]
            c0 = d["close"][by_day[days[k - 1]]]
            prev_ret[(sym, days[k] + timedelta(days=1))] = (c1 / c0 - 1) * 100

    all_ts = sorted({b.ts for d in data.values() for b in d["bars"]})
    state = {(s, X): {"pos_until": -1} for s in data for X in DEPTHS}
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
                for X in DEPTHS:
                    ref[(sym, X)] = d["close"][i - 1] * (1 - X / 100)
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
        active = {(s, X) for _, s, X in ranks[:14]}
        for sym, d in data.items():
            i = d["idx"].get(ts)
            if i is None or i < 21 or i >= len(d["bars"]) - 361 - 2:
                continue
            for X in DEPTHS:
                lv = ref.get((sym, X))
                if lv is None or (sym, X) not in active:
                    continue
                st = state[(sym, X)]
                if i <= st["pos_until"]:
                    continue
                if d["low"][i] <= lv:
                    is_bull = flags.get(ts.date(), False)
                    timeout = 360 if is_bull else 120
                    entry = min(lv, d["close"][i - 1])
                    ref_px = lv / (1 - X / 100)          # 기준가 (100% 복구점)
                    tgt1 = entry * (1 + REC * X / 100)
                    end = min(i + timeout, len(d["bars"]) - 1)
                    # 현행: 70% 전량
                    px_full, off_full = d["close"][end], end - i
                    j1 = None
                    for j in range(i + 1, end + 1):
                        if d["high"][j] >= tgt1:
                            px_full, off_full = tgt1, j - i
                            j1 = j
                            break
                    # 분할: 절반 70%, 잔여 100% 복구(ref_px) or 타임아웃
                    if j1 is None:
                        px_split, off_split = px_full, off_full
                    else:
                        px2, off2 = d["close"][end], end - i
                        for j in range(j1 + 1, end + 1):
                            if d["high"][j] >= ref_px:
                                px2, off2 = ref_px, j - i
                                break
                        px_split = (tgt1 + px2) / 2
                        off_split = off2
                    # 피처
                    v20 = sum(vols[sym][i - 20:i]) / 20
                    vr = vols[sym][i] / v20 if v20 > 0 else 0
                    events.append({
                        "symbol": f"{sym}#{X}", "sym": sym, "X": X, "ts": ts,
                        "entry": entry,
                        "exit_ts": d["bars"][i + off_full].ts, "exit": px_full,
                        "exit_split": px_split,
                        "exit_split_ts": d["bars"][i + off_split].ts,
                        "regime": "bull" if is_bull else "off",
                        "hour": ts.hour,
                        "btc5": btc_r5.get(ts),
                        "vr": vr,
                        "pierce": (lv - entry) / lv * 100,
                        "prev_ret": prev_ret.get((sym, ts.date())),
                        "hit70": j1 is not None,
                    })
                    st["pos_until"] = i + off_full
    tagged = {k2: day_close[k2.split("#")[0]] for k2 in {e["symbol"] for e in events}}
    events.sort(key=lambda e: e["ts"])
    # 클러스터 순번 (당일 몇 번째 체결인가)
    per_day = collections.Counter()
    for e in events:
        d = e["ts"].date()
        per_day[d] += 1
        e["day_seq"] = per_day[d]
    return events, tagged


_flags_cache = None
def flags_lookup(d):
    global _flags_cache
    if _flags_cache is None:
        _flags_cache = A.build_regime()
    return _flags_cache.get(d, False)


def net_of(e, split=False):
    px = e["exit_split"] if split else e["exit"]
    return (px / e["entry"] - 1) * 100 - COST


def show_portfolio(tag, events, dc, split=False):
    if not events:
        print(f"  {tag}: 이벤트 없음")
        return
    evs = [dict(e, exit=e["exit_split"], exit_ts=e["exit_split_ts"]) if split else e
           for e in events]
    last = max(e["exit_ts"] for e in evs).date()
    boundary = last - timedelta(days=365)
    rets = []
    out = []
    for label, s, e2 in (("상승년", boundary - timedelta(days=365), boundary),
                         ("하락년", boundary + timedelta(days=1), last)):
        r = simulate(evs, dc, s, e2, 0.10, 10)
        rets.append(r["ret"])
        out.append(f"{label} {r['ret']:+6.1f}% (MDD {r['mdd']:4.1f})")
    comp = ((1 + rets[0] / 100) * (1 + rets[1] / 100) - 1) * 100
    nets = [net_of(e, split) for e in events]
    wins = sum(1 for n in nets if n > 0) / len(nets) * 100
    print(f"  {tag}: n={len(events)} | 승률 {wins:.0f}% | 건당 {statistics.mean(nets):+.3f}% | "
          f"{' | '.join(out)} | 2년 {comp:+.1f}%")


def main():
    events, dc = build_events()
    per_day = collections.Counter(e["ts"].date() for e in events)
    disaster_days = {d for d, c in per_day.items() if c >= DISASTER_MIN_FILLS}
    ordinary = [e for e in events if e["ts"].date() not in disaster_days]
    print(f"특수일 정의: 하루 체결 ≥{DISASTER_MIN_FILLS}건 → {len(disaster_days)}일: "
          f"{', '.join(str(d) for d in sorted(disaster_days))}\n")

    print("== 1) 청산 비교 (10%×10) ==")
    for split, sl in ((False, "현행 70% 전량"), (True, "분할 70%½+100%½")):
        print(f"[{sl}]")
        show_portfolio("전체 기간", events, dc, split)
        show_portfolio("특수일 제외", ordinary, dc, split)

    print("\n== 2) 패배 해부 (현행 청산 기준) ==")
    for scope, evs in (("전체", events), ("특수일 제외", ordinary)):
        losses = [e for e in evs if net_of(e) <= 0]
        wins = [e for e in evs if net_of(e) > 0]
        lens = [net_of(e) for e in losses]
        print(f"[{scope}] 패배 {len(losses)}/{len(evs)}건 | 패배 평균 {statistics.mean(lens):+.2f}% | "
              f"최악 {min(lens):+.1f}%")
        def rate(sel):
            if len(sel) < 15:
                return f"n={len(sel)}<15"
            l = sum(1 for e in sel if net_of(e) <= 0) / len(sel) * 100
            ev = statistics.mean(net_of(e) for e in sel)
            return f"패배율 {l:.0f}% 기대값 {ev:+.2f}% (n={len(sel)})"
        print(f"  단: -3 {rate([e for e in evs if e['X']==3.0])} | -5 {rate([e for e in evs if e['X']==5.0])}")
        print(f"  레짐: bull {rate([e for e in evs if e['regime']=='bull'])} | off {rate([e for e in evs if e['regime']=='off'])}")
        print(f"  BTC동반: ≤-1% {rate([e for e in evs if e['btc5'] is not None and e['btc5']<=-1])} | "
              f">-1% {rate([e for e in evs if e['btc5'] is not None and e['btc5']>-1])}")
        print(f"  거래량: ≥3배 {rate([e for e in evs if e['vr']>=3])} | <3배 {rate([e for e in evs if e['vr']<3])}")
        print(f"  관통: 0(정확) {rate([e for e in evs if e['pierce']<=0.01])} | "
              f">0.5% {rate([e for e in evs if e['pierce']>0.5])}")
        print(f"  당일순번: 1~2 {rate([e for e in evs if e['day_seq']<=2])} | "
              f"3+ {rate([e for e in evs if e['day_seq']>=3])}")
        print(f"  전일: ≤-5% {rate([e for e in evs if e['prev_ret'] is not None and e['prev_ret']<=-5])} | "
              f"-5~0 {rate([e for e in evs if e['prev_ret'] is not None and -5<e['prev_ret']<=0])} | "
              f">0 {rate([e for e in evs if e['prev_ret'] is not None and e['prev_ret']>0])}")
        print(f"  시간: 00-08 {rate([e for e in evs if e['hour']<9])} | 09-16 {rate([e for e in evs if 9<=e['hour']<17])} | "
              f"17-23 {rate([e for e in evs if e['hour']>=17])}")


if __name__ == "__main__":
    main()
