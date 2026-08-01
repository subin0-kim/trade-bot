"""추세 지속 + 눌림 매수 가족 스윕 — 유튜브(함투사) 기법의 일반화 검증.

원본 기법 (나스닥 선물 1분봉): 이평 기울기 30분 연속 양수 → 눌림 매수 →
조건구간 변동폭(R)의 0.7배에서 절반 익절 + 본전 손절선 → 1.0R 최종 익절. 롱 온리.

일반화 축 (2×3×2×2 = 24변형, 크립토 시총15+ETH 1분봉 2년, 비용 0.2%):
  이평: MA20 / MA60 (1분봉)
  지속: 기울기 연속 양수 15 / 30 / 60분
  진입: 눌림(저가가 이평 터치 후 다음봉 종가) vs 즉시(지속 성립 다음봉 종가)
  청산: 원본근사(0.7R 절반→본전스톱+1.0R, 초기스톱 -0.7R, 240분 타임아웃)
        vs 하우스(0.7R 전량 목표, 무손절, 240분 타임아웃)

  uv run python scripts/trend_persist_dip.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import CACHE_1M, load_1m

UNIVERSE = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})
COST = 0.2
TIMEOUT = 240
MAS = [20, 60]
DURS = [15, 30, 60]


def simulate_exit(closes, highs, i0, entry, r_pct, style):
    """진입 후 청산 시뮬. 순수익% 반환. r_pct = R/entry×100."""
    tp1 = entry * (1 + 0.007 * r_pct)      # 0.7R
    tp2 = entry * (1 + 0.010 * r_pct)      # 1.0R
    stop0 = entry * (1 - 0.007 * r_pct)    # 초기 -0.7R (원본근사만)
    end = min(i0 + TIMEOUT, len(closes) - 1)

    if style == "하우스":
        for j in range(i0 + 1, end + 1):
            if highs[j] >= tp1:
                return (tp1 / entry - 1) * 100 - COST
        return (closes[end] / entry - 1) * 100 - COST

    # 원본근사: 절반 0.7R 익절 → 잔여 본전스톱 + 1.0R
    half1 = None
    j = i0 + 1
    while j <= end:
        if closes[j] <= stop0:
            return (closes[j] / entry - 1) * 100 - COST
        if highs[j] >= tp1:
            half1 = (tp1 / entry - 1) * 100 - COST
            break
        j += 1
    if half1 is None:
        return (closes[end] / entry - 1) * 100 - COST
    for k in range(j + 1, end + 1):
        if closes[k] <= entry:                       # 본전 스톱 (종가 기준)
            return (half1 + (0 - COST)) / 2
        if highs[k] >= tp2:
            return (half1 + (tp2 / entry - 1) * 100 - COST) / 2
    return (half1 + (closes[end] / entry - 1) * 100 - COST) / 2


def main():
    results: dict[tuple, list] = {}
    all_last = None
    for sym in UNIVERSE:
        bars = load_1m(sym)
        if len(bars) < 5000:
            continue
        all_last = max(all_last, bars[-1].ts) if all_last else bars[-1].ts
        closes = [float(b.close) for b in bars]
        highs = [float(b.high) for b in bars]
        lows = [float(b.low) for b in bars]

        for ma_n in MAS:
            # 증분 MA
            ma = [None] * len(closes)
            s = sum(closes[:ma_n])
            ma[ma_n - 1] = s / ma_n
            for i in range(ma_n, len(closes)):
                s += closes[i] - closes[i - ma_n]
                ma[i] = s / ma_n

            streak = 0
            run_high = run_low = None
            armed_at = {d: None for d in DURS}      # 지속 d 성립 시점
            entered = {(d, e): False for d in DURS for e in ("눌림", "즉시")}
            for i in range(ma_n + 1, len(closes) - TIMEOUT - 2):
                if ma[i] > ma[i - 1]:
                    if streak == 0:
                        run_high, run_low = highs[i], lows[i]
                    else:
                        run_high = max(run_high, highs[i])
                        run_low = min(run_low, lows[i])
                    streak += 1
                else:
                    streak = 0
                    armed_at = {d: None for d in DURS}
                    entered = {k: False for k in entered}
                    continue

                for d in DURS:
                    if streak == d:
                        armed_at[d] = i
                    if armed_at[d] is None:
                        continue
                    r_pct = (run_high - run_low) / closes[i] * 100
                    if r_pct <= 0:
                        continue
                    # 즉시: 성립 직후 1회
                    if not entered[(d, "즉시")] and streak == d:
                        entered[(d, "즉시")] = True
                        i0 = i + 1
                        entry = closes[i0]
                        for style in ("원본근사", "하우스"):
                            net = simulate_exit(closes, highs, i0, entry, r_pct, style)
                            results.setdefault((ma_n, d, "즉시", style), []).append(
                                (bars[i0].ts, net))
                    # 눌림: 성립 후 저가가 MA 터치하는 첫 봉
                    if not entered[(d, "눌림")] and streak > d and lows[i] <= ma[i]:
                        entered[(d, "눌림")] = True
                        i0 = i + 1
                        entry = closes[i0]
                        for style in ("원본근사", "하우스"):
                            net = simulate_exit(closes, highs, i0, entry, r_pct, style)
                            results.setdefault((ma_n, d, "눌림", style), []).append(
                                (bars[i0].ts, net))

    boundary = all_last.date() - timedelta(days=365)
    print(f"유니버스 {len(UNIVERSE)}종 × 2년 1분봉 | 비용 {COST}% | 롱 온리\n")
    rows = []
    for (ma_n, d, e, style), evts in sorted(results.items()):
        vals = [v for _, v in evts]
        a = [v for ts, v in evts if ts.date() < boundary]
        b = [v for ts, v in evts if ts.date() >= boundary]
        if len(vals) < 50 or not a or not b:
            continue
        ev = statistics.mean(vals)
        pos = sum(1 for v in vals if v > 0) / len(vals) * 100
        mark = "V" if statistics.mean(a) > 0 and statistics.mean(b) > 0 else " "
        rows.append((ev, f"MA{ma_n:<3} {d:>2}분 {e} {style:<4}: n={len(vals):>6} | "
                     f"기대값 {ev:+.3f}% | 승률 {pos:.0f}% | "
                     f"상승년 {statistics.mean(a):+.3f} / 하락년 {statistics.mean(b):+.3f} {mark}"))
    for _, line in sorted(rows, reverse=True):
        print(line)


if __name__ == "__main__":
    main()
