"""침묵 후 폭발 추격 — "거래가 거의 바닥이었다가 터지며 오르는 경우는 다른가".

가설 (사용자): 평소 거래대금이 바닥이던 코인이 갑자기 터지며 상승하는 경우가
평소 활발하던 코인의 폭발보다 낫고, 소형 시총에서 더 잘 맞을 것.

침묵도 Q = 직전 20분 평균 거래대금 ÷ 직전 3일 평균 거래대금
  Q ≤ 0.2 바닥 / 0.2~0.7 한산 / 0.7~1.5 평소 / >1.5 이미 활발
트리거: 1분 거래대금 ≥ 10 × 20분 평균 AND 1분 수익률 ≥ +0.5%
전략: 다음 1분봉 종가 진입 → +1%/+2% 목표 / 30분 타임아웃 / 무손절, 비용 0.2%
그룹: 대형(시총15+ETH) vs 중소형(DOT·AAVE·PEPE·ETC·ONDO·WLD·STX·BONK·LPT·STORJ)

  uv run python scripts/quiet_volume_chase.py
"""

from __future__ import annotations

import statistics
import sys

sys.path.insert(0, "scripts")

from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import CACHE_1M, load_1m

LARGE = set(TOP_MCAP_ALTS) | {"KRW-ETH"}
SMALL = {"KRW-DOT", "KRW-AAVE", "KRW-PEPE", "KRW-ETC", "KRW-ONDO",
         "KRW-WLD", "KRW-STX", "KRW-BONK", "KRW-LPT", "KRW-STORJ"}
COST = 0.2
VMA_N = 20
BASE_N = 4320          # 3일
COOLDOWN = 30
TIMEOUT = 30
K = 10
TARGETS = [0.01, 0.02]


def q_bucket(q: float) -> str:
    if q <= 0.2:
        return "바닥(≤0.2)"
    if q <= 0.7:
        return "한산(0.2~0.7)"
    if q <= 1.5:
        return "평소(0.7~1.5)"
    return "활발(>1.5)"


def main():
    results: dict[tuple[str, str, float], list] = {}
    for path in sorted(CACHE_1M.glob("*.jsonl")):
        sym = path.stem
        group = "대형" if sym in LARGE else ("중소형" if sym in SMALL else None)
        if group is None or sym == "KRW-BTC":
            continue
        bars = load_1m(sym)
        if len(bars) < BASE_N + 100:
            continue
        closes = [float(b.close) for b in bars]
        highs = [float(b.high) for b in bars]
        turn = [float(b.volume) * float(b.close) for b in bars]  # 분당 거래대금(원)

        last_evt = -COOLDOWN
        s20 = sum(turn[BASE_N - VMA_N:BASE_N])
        sbase = sum(turn[:BASE_N])
        for i in range(BASE_N, len(bars) - TIMEOUT - 3):
            m20 = s20 / VMA_N
            mbase = sbase / BASE_N
            r1 = closes[i] / closes[i - 1] - 1
            if (m20 > 0 and mbase > 0 and turn[i] >= K * m20 and r1 >= 0.005
                    and i - last_evt >= COOLDOWN):
                last_evt = i
                q = m20 / mbase
                i0 = i + 1
                entry = closes[i0]
                for t in TARGETS:
                    tgt = entry * (1 + t)
                    px = closes[i0 + TIMEOUT]
                    for j in range(i0 + 1, i0 + TIMEOUT + 1):
                        if highs[j] >= tgt:
                            px = tgt
                            break
                    net = (px / entry - 1) * 100 - COST
                    results.setdefault((group, q_bucket(q), t), []).append(net)
            s20 += turn[i] - turn[i - VMA_N]
            sbase += turn[i] - turn[i - BASE_N]

    print(f"트리거: 1분 거래대금 ≥ {K}×20분평균 + 1분 +0.5%↑ | 침묵도 Q = 20분평균/3일평균\n")
    for group in ("대형", "중소형"):
        print(f"[{group}]")
        for t in TARGETS:
            for qb in ("바닥(≤0.2)", "한산(0.2~0.7)", "평소(0.7~1.5)", "활발(>1.5)"):
                vals = results.get((group, qb, t), [])
                if len(vals) < 20:
                    print(f"  목표+{t*100:.0f}% {qb:<13}: n={len(vals)} (표본 부족)")
                    continue
                pos = sum(1 for v in vals if v > 0) / len(vals) * 100
                print(f"  목표+{t*100:.0f}% {qb:<13}: n={len(vals):>5} | "
                      f"기대값 {statistics.mean(vals):+.3f}% | 중앙 {statistics.median(vals):+.3f}% | "
                      f"승률 {pos:.0f}%")
            print()


if __name__ == "__main__":
    main()
