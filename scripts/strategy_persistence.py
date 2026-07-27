"""전략 성과 지속성 검증 — "직전 구간 승자를 따라가면 이기는가".

사용자 가설: 최근 n봉에서 A가 우세했으면 다음 구간도 A로 가는 게 낫다.
성립 전제: 전략 성과의 구간 간 지속성 (순위 자기상관 > 0).

측정:
  1. 순위 지속성 — 구간 t의 전략 순위와 t+1 순위의 스피어만 상관
  2. 정책 비교 (모두 동일 데이터, 비용 동일):
     - follow_winner: 직전 구간 1위 전략을 다음 구간에 사용 (사용자 제안)
     - follow_loser: 직전 꼴찌 사용 (역발상 대조군)
     - equal_blend: 전 전략 평균 (스위칭 안 함)
     - fixed_<each>: 한 전략 고정

  uv run python scripts/strategy_persistence.py --tf 240m --window 400
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest_upbit import load_5m, run_one, to_timeframe

CACHE_5M = Path("data/cache/upbit/5m")
STRATEGIES = ["connors_rsi2", "bb_meanrev", "macd_trend_mtf",
              "ichimoku_tk", "breakout_momo", "st_trend"]


def window_returns(symbol: str, bars, window: int, warmup: int = 300) -> list[dict]:
    """겹치지 않는 구간별 전략 수익률 매트릭스. [{strategy: ret}, ...]"""
    out = []
    start = 0
    while start + warmup + window <= len(bars):
        seg = bars[start : start + warmup + window]
        row = {}
        for name in STRATEGIES:
            try:
                r = run_one(symbol, seg, name, tf="_seg")
            except Exception:
                continue
            if r is not None:
                row[name] = r["total_return_pct"]
        if len(row) == len(STRATEGIES):
            out.append(row)
        start += window
    return out


def spearman(a: list[float], b: list[float]) -> float:
    def rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        rk = [0.0] * len(xs)
        for pos, i in enumerate(order):
            rk[i] = pos
        return rk
    ra, rb = rank(a), rank(b)
    n = len(a)
    if n < 2:
        return 0.0
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="240m")
    parser.add_argument("--window", type=int, default=400)
    args = parser.parse_args()

    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    matrices = {}
    for s in symbols:
        bars = to_timeframe(load_5m(s), args.tf)
        rows = window_returns(s, bars, args.window)
        if len(rows) >= 3:
            matrices[s] = rows

    print(f"지속성 검증: {len(matrices)}종목, {args.tf}, 구간 {args.window}봉 "
          f"(전략 {len(STRATEGIES)}종)\n")

    # 1) 순위 지속성
    corrs = []
    for rows in matrices.values():
        for i in range(1, len(rows)):
            a = [rows[i - 1][s] for s in STRATEGIES]
            b = [rows[i][s] for s in STRATEGIES]
            corrs.append(spearman(a, b))
    print(f"1) 순위 지속성 (구간 t 순위 vs t+1 순위, 스피어만):")
    print(f"   평균 {statistics.mean(corrs):+.3f}, 중앙값 {statistics.median(corrs):+.3f}, "
          f"표본 {len(corrs)} (0이면 무작위 = 갈아타기 근거 없음)\n")

    # 2) 정책 비교
    policies: dict[str, list[float]] = {"follow_winner": [], "follow_loser": [], "equal_blend": []}
    for name in STRATEGIES:
        policies[f"fixed_{name}"] = []
    for rows in matrices.values():
        for i in range(1, len(rows)):
            prev, cur = rows[i - 1], rows[i]
            winner = max(prev, key=prev.get)
            loser = min(prev, key=prev.get)
            policies["follow_winner"].append(cur[winner])
            policies["follow_loser"].append(cur[loser])
            policies["equal_blend"].append(statistics.mean(cur.values()))
            for name in STRATEGIES:
                policies[f"fixed_{name}"].append(cur[name])

    print(f"2) 정책 비교 (다음 구간 수익률, 구간당 {args.window}봉):")
    print(f"{'정책':<22}{'평균%':>8}{'중앙값%':>9}{'수익구간':>9}")
    for name, vals in sorted(policies.items(), key=lambda kv: -statistics.mean(kv[1])):
        pos = sum(1 for v in vals if v > 0)
        print(f"{name:<22}{statistics.mean(vals):>+8.2f}{statistics.median(vals):>+9.2f}"
              f"{pos:>6}/{len(vals)}")


if __name__ == "__main__":
    main()
