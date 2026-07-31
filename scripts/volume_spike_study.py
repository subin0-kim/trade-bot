"""분당 거래량 폭발 이벤트 연구 — "거래량이 터질 때 사면 되나?"

이벤트: 1분 거래량 ≥ K × 직전 60분 평균 (쿨다운 60분).
동반 5분 가격 방향으로 3분할: 급등 중(+1%↑) / 급락 중(-1%↓) / 보합.
전방 수익률 +15/+60/+240분 (비용 미차감 — 방향성 판단용, 왕복 0.2% 감안해 읽을 것).

추가: 기존 급락 반전(-3%) 이벤트를 트리거 순간의 거래량 배율로 2분할 —
"투매 클라이맥스(거래량 폭발 동반 급락)가 조용한 급락보다 잘 회복되는가".

  uv run python scripts/volume_spike_study.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import CACHE_1M, load_1m

UNIVERSE = set(TOP_MCAP_ALTS) | {"KRW-ETH"}
K = 10.0                 # 거래량 배율 임계
VMA_N = 60
COOLDOWN = 60
HORIZONS = [15, 60, 240]


def main():
    spike_events: dict[tuple[str, str], list[dict]] = {}
    dip_split: dict[str, list[float]] = {"조용한 급락(<3배)": [], "투매 급락(≥3배)": []}
    all_last = None

    for path in sorted(CACHE_1M.glob("*.jsonl")):
        if path.stem not in UNIVERSE:
            continue
        bars = load_1m(path.stem)
        if len(bars) < 2000:
            continue
        all_last = max(all_last, bars[-1].ts) if all_last else bars[-1].ts
        closes = [float(b.close) for b in bars]
        vols = [float(b.volume) for b in bars]
        # 롤링 거래량 평균 (현재봉 제외, 증분 갱신)
        last_spike = -COOLDOWN
        last_dip = -COOLDOWN
        vsum = sum(vols[5:5 + VMA_N])
        for i in range(VMA_N + 5, len(bars) - HORIZONS[-1] - 1):
            vma = vsum / VMA_N
            r5 = closes[i] / closes[i - 5] - 1

            # ① 거래량 폭발 이벤트
            if vma > 0 and vols[i] >= K * vma and i - last_spike >= COOLDOWN:
                last_spike = i
                direction = "급등 중" if r5 > 0.01 else ("급락 중" if r5 < -0.01 else "보합")
                half = "상승년" if bars[i].ts < all_last - timedelta(days=365) else "하락년"
                evt = {f"f{h}": (closes[i + h] / closes[i] - 1) * 100 for h in HORIZONS}
                spike_events.setdefault((direction, half), []).append(evt)

            # ② 급락 반전(-3%) 이벤트의 거래량 분할 (+60분 순수익, 보수적 종가회복 청산 대신 간이 +60분)
            if r5 <= -0.03 and i - last_dip >= COOLDOWN:
                last_dip = i
                ratio = vols[i] / vma if vma > 0 else 0
                level = closes[i - 5]
                px = closes[i + 240] if i + 240 < len(closes) else closes[-1]
                for j in range(i + 1, min(i + 241, len(closes))):
                    if closes[j] >= level:
                        px = closes[j]
                        break
                net = (px / closes[i + 1] - 1) * 100 - 0.2 if i + 1 < len(closes) else None
                if net is not None:
                    key = "투매 급락(≥3배)" if ratio >= 3 else "조용한 급락(<3배)"
                    dip_split[key].append(net)

            vsum += vols[i] - vols[i - VMA_N]

    print(f"① 거래량 폭발 (1분 거래량 ≥ {K:.0f}×60분 평균) 후 전방 수익률 (비용 미차감):\n")
    for (direction, half), evts in sorted(spike_events.items()):
        parts = []
        for h in HORIZONS:
            vals = [e[f"f{h}"] for e in evts]
            pos = sum(1 for v in vals if v > 0) / len(vals) * 100
            parts.append(f"+{h}분 중앙 {statistics.median(vals):+.2f}% ({pos:.0f}%양수)")
        print(f"  [{direction} | {half}] {len(evts)}건: {' | '.join(parts)}")

    print(f"\n② 급락 반전(-3%)을 거래량으로 나누면 (회복선 청산, 비용 차감):")
    for key, vals in dip_split.items():
        if not vals:
            continue
        wins = sum(1 for v in vals if v > 0) / len(vals) * 100
        print(f"  {key}: {len(vals)}건 | 기대값 {statistics.mean(vals):+.3f}%/건 | "
              f"중앙 {statistics.median(vals):+.2f}% | 승률 {wins:.0f}%")


if __name__ == "__main__":
    main()
