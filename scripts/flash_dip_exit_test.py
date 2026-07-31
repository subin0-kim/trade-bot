"""급락 반전 매수의 청산 규칙 후보 비교 — 같은 이벤트 표본, 다른 출구.

진입은 고정 (5분 -3% 급락 확인 순간의 1분봉 종가), 청산만 4종 비교:
  A. 시간 15분   — 이벤트 15분 뒤 종가 매도
  B. 시간 60분   — 60분 뒤 종가 매도
  C. 회복선     — 급락 직전 가격(5분 전 종가) 도달 시 지정가 매도, 240분 내 미도달 시 종가
  D. 브래킷     — +3% 목표(지정가) / 1분 종가 -5% 손절 / 240분 타임아웃

수익률은 왕복 비용 0.2%(수수료 0.05%×2 + 슬리피지 0.05%×2) 차감 후.
한계: 진입 체결을 이벤트 봉 종가로 가정 (실전은 지정가 대기라 더 유리할 수도, 뉴스 급락은 더 불리할 수도).

  uv run python scripts/flash_dip_exit_test.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from backtest_upbit import load_5m
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from minute1_backtest import CACHE_1M, load_1m

THRESH = 0.03
COOLDOWN = 60
TIMEOUT = 240
COST = 0.2               # 왕복 비용 %
TARGET, STOP = 0.03, 0.05


def simulate(closes, highs, i):
    """이벤트 i에서 진입했을 때 각 청산안의 (수익률%, 보유분) — 비용 차감 전."""
    entry = closes[i]
    out = {}
    out["A_15분"] = ((closes[i + 15] / entry - 1) * 100, 15)
    out["B_60분"] = ((closes[i + 60] / entry - 1) * 100, 60)

    level = closes[i - 5]                      # 급락 직전가 (공백 메움 기준)
    res = ((closes[i + TIMEOUT] / entry - 1) * 100, TIMEOUT)
    for j in range(i + 1, i + TIMEOUT + 1):
        if highs[j] >= level:
            res = ((level / entry - 1) * 100, j - i)
            break
    out["C_회복선"] = res

    tgt, stp = entry * (1 + TARGET), entry * (1 - STOP)
    res = ((closes[i + TIMEOUT] / entry - 1) * 100, TIMEOUT)
    for j in range(i + 1, i + TIMEOUT + 1):
        if closes[j] <= stp:                   # 보수적: 손절 먼저 판정
            res = ((closes[j] / entry - 1) * 100, j - i)
            break
        if highs[j] >= tgt:
            res = ((tgt / entry - 1) * 100, j - i)
            break
    out["D_브래킷"] = res
    return out


def main():
    daily_5m = {c.ts.date(): c for c in to_daily(load_5m("KRW-BTC"))}
    daily_1m = {c.ts.date(): c for c in to_daily(load_1m("KRW-BTC"))}
    merged = {**daily_5m, **daily_1m}
    ens = ensemble_flags([merged[d] for d in sorted(merged)])
    all_last = max(b[-1].ts for p in CACHE_1M.glob("*.jsonl") if (b := load_1m(p.stem)))
    boundary = all_last - timedelta(days=365)

    results: dict[str, list] = {}
    subsets: dict[str, dict[str, list]] = {}
    for path in sorted(CACHE_1M.glob("*.jsonl")):
        if path.stem == "KRW-BTC":
            continue
        bars = load_1m(path.stem)
        if len(bars) < 2000:
            continue
        closes = [float(b.close) for b in bars]
        highs = [float(b.high) for b in bars]
        last_evt = -COOLDOWN
        for i in range(5, len(bars) - TIMEOUT - 1):
            r5 = closes[i] / closes[i - 5] - 1
            if r5 > -THRESH or i - last_evt < COOLDOWN:
                continue
            last_evt = i
            sim = simulate(closes, highs, i)
            half = "상승년" if bars[i].ts < boundary else "하락년"
            regime = "bull" if ens.get(bars[i].ts.date(), False) else "off"
            for scheme, v in sim.items():
                results.setdefault(scheme, []).append(v)
                subsets.setdefault(f"{half}×{regime}", {}).setdefault(scheme, []).append(v)

    def show(tag, res):
        print(f"[{tag}]")
        for scheme in ("A_15분", "B_60분", "C_회복선", "D_브래킷"):
            vals = res.get(scheme, [])
            if not vals:
                continue
            net = [r - COST for r, _ in vals]
            hold = statistics.mean(m for _, m in vals)
            pos = sum(1 for v in net if v > 0) / len(net) * 100
            print(f"  {scheme:<8} 순수익 중앙 {statistics.median(net):+.2f}% | 평균 {statistics.mean(net):+.2f}% | "
                  f"승률 {pos:.0f}% | 평균 보유 {hold:.0f}분 | n={len(net)}")
        print()

    show(f"전체 (비용 {COST}% 차감)", results)
    for tag in sorted(subsets):
        show(tag, subsets[tag])


if __name__ == "__main__":
    main()
