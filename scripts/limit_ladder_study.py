"""지정가 사다리 연구 — "반등 직전 가격에 미리 깔아두고 기다리기" (사용자 설계).

A. 변동성 특성: 하루 등락(고저폭/시가) ≥5%의 빈도·심볼 분포·군집성(어제 5%면 오늘도?)
   ·연속 스트릭·캔들 모양 분류 — "변동성 심하겠다"를 미리 알 수 있는가의 답
B. 전략 시뮬: 매 n분마다 현재가 -X% 지정가 재산정/재주문 → 저가 터치 시 그 가격 체결
   → 목표 +0.7X 지정가 매도 / 손절 -X (유·무) / 240분 타임아웃
   변동성 게이트: 전일 등락 ≥5%인 날만 주문 (유·무)
   비용: 왕복 0.2% (지정가 체결이라 실제론 슬리피지 절감 여지 — 보수 유지)

  uv run python scripts/limit_ladder_study.py
"""

from __future__ import annotations

import collections
import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import CACHE_1M, load_1m

UNIVERSE = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})
COST = 0.2
TIMEOUT = 240
DEPTHS = [2.0, 3.0, 5.0]
REFRESH = [1, 5, 15]


def day_shape(o, h, l, c):
    rng = h - l
    if rng <= 0:
        return "무변동"
    body = abs(c - o) / rng
    upper = (h - max(o, c)) / rng
    lower = (min(o, c) - l) / rng
    if body >= 0.6:
        return "장대양봉" if c > o else "장대음봉"
    if upper >= 0.4:
        return "윗꼬리형"
    if lower >= 0.4:
        return "아래꼬리형"
    return "팽이(양꼬리)"


def main():
    # ---------- A. 변동성 특성 ----------
    vol_day: dict = {}          # (sym, date) -> range%
    shape_count = collections.Counter()
    sym_counts = collections.Counter()
    all_days_set = set()
    day_bars_all: dict = {}     # sym -> {date: bars}
    arrays: dict = {}           # sym -> (bars, closes, highs, lows) 프리로드
    for sym in UNIVERSE:
        bars = load_1m(sym)
        if len(bars) < 5000:
            continue
        arrays[sym] = (bars, [float(b.close) for b in bars],
                       [float(b.high) for b in bars], [float(b.low) for b in bars])
        by_day: dict = {}
        for b in bars:
            by_day.setdefault(b.ts.date(), []).append(b)
        day_bars_all[sym] = by_day
        for d, db in by_day.items():
            if len(db) < 600:
                continue
            all_days_set.add(d)
            o = float(db[0].open); c = float(db[-1].close)
            h = max(float(b.high) for b in db); l = min(float(b.low) for b in db)
            rng = (h - l) / o * 100
            vol_day[(sym, d)] = rng
            if rng >= 5:
                sym_counts[sym] += 1
                shape_count[day_shape(o, h, l, c)] += 1

    n_days = len(all_days_set)
    total_sd = len(vol_day)
    hot = [k for k, v in vol_day.items() if v >= 5]
    print(f"== A. 등락 5%+ 특성 ({len(day_bars_all)}종 × {n_days}일) ==")
    print(f"빈도: 심볼-일 {len(hot):,}/{total_sd:,} ({len(hot)/total_sd*100:.0f}%) | "
          f"심볼당 평균 {len(hot)/len(day_bars_all)/n_days*365:.0f}일/년")
    tops = sym_counts.most_common(3); bots = sym_counts.most_common()[-3:]
    print(f"심볼 편차: 최다 {', '.join(f'{s.replace('KRW-','')}({n})' for s, n in tops)} | "
          f"최소 {', '.join(f'{s.replace('KRW-','')}({n})' for s, n in bots)}")
    print("캔들 모양: " + ", ".join(f"{k} {v}건({v/len(hot)*100:.0f}%)" for k, v in shape_count.most_common()))
    # 군집성
    base = len(hot) / total_sd
    cond_n = cond_hit = 0
    streaks = collections.Counter()
    for sym, by_day in day_bars_all.items():
        ds = sorted(d for d in by_day if (sym, d) in vol_day)
        run = 0
        for k in range(1, len(ds)):
            prev_hot = vol_day[(sym, ds[k-1])] >= 5
            today_hot = vol_day[(sym, ds[k])] >= 5
            if prev_hot:
                cond_n += 1
                cond_hit += today_hot
            if today_hot:
                run += 1
            elif run:
                streaks[min(run, 7)] += 1
                run = 0
    print(f"군집성: P(오늘 5%+) 기본 {base*100:.0f}% → 어제 5%+였다면 {cond_hit/cond_n*100:.0f}% "
          f"({cond_hit/cond_n/base:.1f}배)")
    print(f"연속 스트릭 분포: " + ", ".join(f"{k}일×{v}" for k, v in sorted(streaks.items())) + " (7=7일+)\n")

    # ---------- B. 지정가 사다리 스윕 ----------
    print("== B. 지정가 사다리 (체결가=지정가, 목표 +0.7X 지정가, 타임아웃 240분) ==")
    boundary = max(all_days_set) - timedelta(days=365)
    for X in DEPTHS:
        for n in REFRESH:
            events = []   # (ts, 손절없음 net, 손절있음 net, 게이트여부)
            for sym in day_bars_all:
                bars, closes, highs, lows = arrays[sym]
                i = 60
                while i < len(bars) - TIMEOUT - 2:
                    ref = closes[i]
                    level = ref * (1 - X / 100)
                    fill = None
                    for j in range(i + 1, min(i + n + 1, len(bars))):
                        if lows[j] <= level:
                            fill = j
                            break
                    if fill is None:
                        i += n
                        continue
                    entry = level
                    tgt = entry * (1 + 0.7 * X / 100)
                    stp = entry * (1 - X / 100)
                    end = min(fill + TIMEOUT, len(bars) - 1)
                    # 무손절: 목표 지정가 or 타임아웃
                    net_ns = (closes[end] / entry - 1) * 100 - COST
                    for j in range(fill + 1, end + 1):
                        if highs[j] >= tgt:
                            net_ns = (tgt / entry - 1) * 100 - COST
                            break
                    # 손절: 종가 -X% 손절 우선 → 목표 → 타임아웃
                    net_st = (closes[end] / entry - 1) * 100 - COST
                    for j in range(fill + 1, end + 1):
                        if closes[j] <= stp:
                            net_st = (closes[j] / entry - 1) * 100 - COST
                            break
                        if highs[j] >= tgt:
                            net_st = (tgt / entry - 1) * 100 - COST
                            break
                    d = bars[fill].ts.date()
                    prev_d = d - timedelta(days=1)
                    gated = vol_day.get((sym, prev_d), 0) >= 5
                    events.append((bars[fill].ts, net_ns, net_st, gated))
                    i = end + 1   # 청산 후 재개
                # 심볼 끝
            for gate_label, sel in (("상시", events), ("변동성일만", [e for e in events if e[3]])):
                if len(sel) < 100:
                    continue
                for stop_label, idx in (("무손절", 1), ("손절-X%", 2)):
                    vals = [e[idx] for e in sel]
                    a = [e[idx] for e in sel if e[0].date() < boundary]
                    b = [e[idx] for e in sel if e[0].date() >= boundary]
                    if not a or not b:
                        continue
                    pos = sum(1 for v in vals if v > 0) / len(vals) * 100
                    mark = "V" if statistics.mean(a) > 0 and statistics.mean(b) > 0 else " "
                    print(f"  -{X:.0f}%/{n:>2}분 {gate_label:<5} {stop_label:<5}: n={len(vals):>6} | "
                          f"기대값 {statistics.mean(vals):+.3f}% | 승률 {pos:.0f}% | "
                          f"상승년 {statistics.mean(a):+.3f}/하락년 {statistics.mean(b):+.3f} {mark}",
                          flush=True)


if __name__ == "__main__":
    main()
