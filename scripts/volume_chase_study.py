"""거래량 폭발 + 상승 추격 단타 — "터질 때 올라타서 +1~2%만 먹고 나오기" 검증.

트리거: 1분 거래량 ≥ K × 직전 20분 평균 AND 1분 수익률 ≥ +0.5% (상승 동반)
진입: 다음 1분봉 종가 (1분 폴링 지연 — 보수)
청산: +1% 또는 +2% 지정가 목표 (고가 터치 시 체결) / 30분 타임아웃 종가 / 손절 없음
비용: 왕복 0.2% 차감. 쿨다운 30분/심볼.

이전 실측(실측 4 부속)과의 차이: 그때는 '고정 시간 뒤 수익률'(중앙 음수)이었고,
이번은 목표가 선청산 — 봉 안의 고점을 먹는 비대칭 청산이라 결과가 다를 수 있다.

  uv run python scripts/volume_chase_study.py
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
VMA_N = 20
COOLDOWN = 30
TIMEOUT = 30
KS = [10, 30]
TARGETS = [0.01, 0.02]


def main():
    results: dict[tuple[int, float], list] = {(k, t): [] for k in KS for t in TARGETS}
    day_counter: dict[int, set] = {k: set() for k in KS}
    all_last = None

    for sym in UNIVERSE:
        bars = load_1m(sym)
        if len(bars) < 2000:
            continue
        all_last = max(all_last, bars[-1].ts) if all_last else bars[-1].ts
        closes = [float(b.close) for b in bars]
        highs = [float(b.high) for b in bars]
        vols = [float(b.volume) for b in bars]
        last_evt = {k: -COOLDOWN for k in KS}
        vsum = sum(vols[1:1 + VMA_N])
        for i in range(VMA_N + 1, len(bars) - TIMEOUT - 3):
            vma = vsum / VMA_N
            r1 = closes[i] / closes[i - 1] - 1
            if vma > 0 and r1 >= 0.005:
                ratio = vols[i] / vma
                for k in KS:
                    if ratio >= k and i - last_evt[k] >= COOLDOWN:
                        last_evt[k] = i
                        day_counter[k].add((sym, bars[i].ts.date()))
                        i0 = i + 1
                        entry = closes[i0]
                        for t in TARGETS:
                            tgt = entry * (1 + t)
                            px, off = closes[i0 + TIMEOUT], TIMEOUT
                            for j in range(i0 + 1, i0 + TIMEOUT + 1):
                                if highs[j] >= tgt:
                                    px, off = tgt, j - i0
                                    break
                            net = (px / entry - 1) * 100 - COST
                            results[(k, t)].append((bars[i].ts, net, off))
            vsum += vols[i] - vols[i - VMA_N]

    boundary = all_last.date() - timedelta(days=365)
    print(f"트리거: 1분 거래량 ≥ K×20분평균 + 1분 +0.5%↑ | 진입 다음봉 종가 | "
          f"청산 목표가/{TIMEOUT}분 타임아웃 | 비용 {COST}%\n")
    for k in KS:
        n_days = len({d for _, d in day_counter[k]})
        print(f"[K={k}배] 심볼-일 {len(day_counter[k]):,}건")
        for t in TARGETS:
            evts = results[(k, t)]
            for label, sel in (("전체", evts),
                              ("상승년", [e for e in evts if e[0].date() < boundary]),
                              ("하락년", [e for e in evts if e[0].date() >= boundary])):
                vals = [v for _, v, _ in sel]
                if not vals:
                    continue
                pos = sum(1 for v in vals if v > 0) / len(vals) * 100
                hold = statistics.mean(o for _, _, o in sel)
                print(f"  목표+{t*100:.0f}% {label:<4}: n={len(vals):,} | "
                      f"기대값 {statistics.mean(vals):+.3f}% | 승률 {pos:.0f}% | "
                      f"평균 보유 {hold:.0f}분")
        print()


if __name__ == "__main__":
    main()
