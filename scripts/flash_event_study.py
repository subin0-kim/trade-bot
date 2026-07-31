"""플래시 이벤트 연구 — 분 단위 급락/급등 후 가격은 어디로 가는가.

질문 (2026-07-31, 사용자):
  1. 초·분 단위 급락에서 포지션을 지킬 수 있나? → 급락 후 회복이 일반적이면
     '장중 반응 매도'는 또 휩쏘다 (재해선 실측과 같은 결론이 나와야 정합).
  2. 급등을 포착해 따라붙는 전략이 되나? → 급등 후 지속 수익이 비용(왕복 0.2%)을
     넘어야 전략이 된다.

방법: 1분봉 캐시(시총15+BTC·ETH, 180일)에서 5분 수익률 ±3% 이벤트 추출 (60분 쿨다운),
이벤트 시점 종가 기준 전방 수익률(+15m/+1h/+4h/+24h)과 급락 후 60분 내 추가 낙폭(칼날 위험),
레짐(BTC 앙상블)별로 분리 집계.

  uv run python scripts/flash_event_study.py
"""

from __future__ import annotations

import statistics
import sys

sys.path.insert(0, "scripts")

from backtest_upbit import load_5m
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from minute1_backtest import CACHE_1M, load_1m

THRESH = 0.03          # 5분 ±3%
COOLDOWN = 60          # 이벤트 후 60분간 재추출 금지
HORIZONS = [15, 60, 240, 1440]


def fwd(closes: list[float], i: int, h: int) -> float | None:
    if i + h >= len(closes):
        return None
    return (closes[i + h] / closes[i] - 1) * 100


def main():
    daily_5m = {c.ts.date(): c for c in to_daily(load_5m("KRW-BTC"))}
    daily_1m = {c.ts.date(): c for c in to_daily(load_1m("KRW-BTC"))}
    merged = {**daily_5m, **daily_1m}
    ens = ensemble_flags([merged[d] for d in sorted(merged)])

    # 기간 분할: 마지막 봉 기준 최근 365일 = 후반(하락장), 그 이전 = 전반(상승장 포함)
    from datetime import timedelta
    all_last = max(load_1m(p.stem)[-1].ts for p in sorted(CACHE_1M.glob("*.jsonl"))
                   if load_1m(p.stem))
    boundary = all_last - timedelta(days=365)

    events: dict[tuple[str, str, str], list[dict]] = {}   # (종류, 기간, 레짐) → 이벤트들
    n_sym = 0
    for path in sorted(CACHE_1M.glob("*.jsonl")):
        bars = load_1m(path.stem)
        if len(bars) < 2000:
            continue
        n_sym += 1
        closes = [float(b.close) for b in bars]
        lows = [float(b.low) for b in bars]
        last_evt = -COOLDOWN
        for i in range(5, len(bars)):
            r5 = closes[i] / closes[i - 5] - 1
            if abs(r5) < THRESH or i - last_evt < COOLDOWN:
                continue
            last_evt = i
            kind = "급락" if r5 < 0 else "급등"
            half = "전반(상승)" if bars[i].ts < boundary else "후반(하락)"
            regime = "bull" if ens.get(bars[i].ts.date(), False) else "off"
            evt = {"r5": r5 * 100}
            for h in HORIZONS:
                evt[f"f{h}"] = fwd(closes, i, h)
            if kind == "급락" and i + 60 < len(bars):
                evt["knife"] = (min(lows[i + 1 : i + 61]) / closes[i] - 1) * 100
            events.setdefault((kind, half, regime), []).append(evt)

    print(f"이벤트 정의: 5분 수익률 ±{THRESH*100:.0f}% | {n_sym}종목 | 쿨다운 {COOLDOWN}분 | "
          f"기간 경계 {boundary:%Y-%m-%d}\n")
    for (kind, half, regime), evts in sorted(events.items()):
        print(f"[{kind} | {half} | 레짐 {regime}] {len(evts)}건 "
              f"(평균 트리거 {statistics.mean(e['r5'] for e in evts):+.2f}%)")
        for h in HORIZONS:
            vals = [e[f"f{h}"] for e in evts if e[f"f{h}"] is not None]
            if not vals:
                continue
            pos = sum(1 for v in vals if v > 0) / len(vals) * 100
            print(f"  +{h:>4}분: 평균 {statistics.mean(vals):+.3f}% | 중앙 {statistics.median(vals):+.3f}% | "
                  f"양수 {pos:.0f}% (n={len(vals)})")
        knives = [e["knife"] for e in evts if "knife" in e]
        if knives:
            knives.sort()
            k10 = knives[max(0, len(knives) // 10 - 1)]
            print(f"  급락 후 60분 내 추가 저점: 중앙 {statistics.median(knives):+.2f}% | "
                  f"하위10% {k10:+.2f}% | 최악 {knives[0]:+.2f}%")
        print()


if __name__ == "__main__":
    main()
