"""워크포워드 검증 — 전략 선택과 성과 측정을 구조적으로 분리.

문제: 여러 전략·파라미터를 전 구간에 돌려 최고를 고르면, 그 성적은 '선택 편향'에 오염된다.
     (코인 검증에서 50조합 중 유일한 플러스가 분할검증에서 재현 실패한 사례)

해결: 롤링 윈도로 **IS(In-Sample)에서만 전략을 고르고, OOS(Out-of-Sample)에서 측정**한다.
     OOS 결과는 선택에 사용되지 않았으므로 편향이 없다.

    |---- IS 1 ----|- OOS 1 -|
              |---- IS 2 ----|- OOS 2 -|
                        |---- IS 3 ----|- OOS 3 -|

보고 항목:
  - OOS 성과 (이것만이 정직한 추정치)
  - IS 성과와의 격차 = 과적합 정도
  - 선택 안정성 = 매 폴드에서 같은 전략이 뽑히는가 (낮으면 신호가 아니라 잡음)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable

from trading_core.models import Candle


@dataclass
class FoldResult:
    fold: int
    selected: str
    is_score: float
    oos_score: float
    oos_trades: int


@dataclass
class WalkForwardResult:
    symbol: str
    folds: list[FoldResult] = field(default_factory=list)

    @property
    def oos_scores(self) -> list[float]:
        return [f.oos_score for f in self.folds]

    @property
    def is_scores(self) -> list[float]:
        return [f.is_score for f in self.folds]

    def summary(self) -> dict:
        if not self.folds:
            return {}
        oos, is_ = self.oos_scores, self.is_scores
        picks = [f.selected for f in self.folds]
        most_common = max(set(picks), key=picks.count)
        return {
            "symbol": self.symbol,
            "folds": len(self.folds),
            "oos_median": round(statistics.median(oos), 2),
            "oos_mean": round(statistics.mean(oos), 2),
            "oos_positive": sum(1 for v in oos if v > 0),
            "is_median": round(statistics.median(is_), 2),
            # IS - OOS = 과적합 정도 (클수록 IS 성적이 허상)
            "degradation": round(statistics.median(is_) - statistics.median(oos), 2),
            "top_pick": most_common,
            "pick_stability": round(picks.count(most_common) / len(picks) * 100, 0),
            "oos_trades": sum(f.oos_trades for f in self.folds),
        }


def walk_forward(
    symbol: str,
    bars: list[Candle],
    candidates: list[str],
    run_fn: Callable[[str, list[Candle], str], dict | None],
    *,
    is_bars: int = 1200,
    oos_bars: int = 400,
    step: int | None = None,
    min_trades: int = 3,
    score_key: str = "total_return_pct",
) -> WalkForwardResult:
    """롤링 워크포워드.

    run_fn(symbol, bars, preset) -> summary dict (백테스트 실행기 주입)
    is_bars/oos_bars: 각 폴드의 학습·검증 구간 길이 (봉 개수)
    """
    result = WalkForwardResult(symbol=symbol)
    step = step or oos_bars
    fold = 0
    start = 0

    while start + is_bars + oos_bars <= len(bars):
        is_slice = bars[start : start + is_bars]
        oos_slice = bars[start : start + is_bars + oos_bars]  # OOS는 워밍업 포함해 이어서 평가

        # --- IS에서만 전략 선택 ---
        best, best_score = None, float("-inf")
        for preset in candidates:
            try:
                r = run_fn(symbol, is_slice, preset)
            except Exception:
                continue
            if not r or r["trades"] < min_trades:
                continue
            if r[score_key] > best_score:
                best, best_score = preset, r[score_key]
        if best is None:
            start += step
            fold += 1
            continue

        # --- OOS에서 측정 (선택에 쓰이지 않은 구간) ---
        try:
            full = run_fn(symbol, oos_slice, best)
            is_only = run_fn(symbol, is_slice, best)
        except Exception:
            start += step
            fold += 1
            continue
        if not full or not is_only:
            start += step
            fold += 1
            continue

        # 전체(IS+OOS) 수익에서 IS 수익을 제거해 OOS 구간 기여만 추출
        is_ret = is_only[score_key]
        full_ret = full[score_key]
        oos_ret = ((1 + full_ret / 100) / (1 + is_ret / 100) - 1) * 100
        result.folds.append(FoldResult(
            fold=fold,
            selected=best,
            is_score=round(best_score, 2),
            oos_score=round(oos_ret, 2),
            oos_trades=max(full["trades"] - is_only["trades"], 0),
        ))
        start += step
        fold += 1

    return result


def aggregate(results: list[WalkForwardResult]) -> dict:
    """여러 종목의 워크포워드 결과 집계."""
    summaries = [r.summary() for r in results if r.folds]
    if not summaries:
        return {}
    oos = [s["oos_median"] for s in summaries]
    picks: dict[str, int] = {}
    for s in summaries:
        picks[s["top_pick"]] = picks.get(s["top_pick"], 0) + 1
    return {
        "symbols": len(summaries),
        "oos_median": round(statistics.median(oos), 2),
        "oos_positive": sum(1 for v in oos if v > 0),
        "is_median": round(statistics.median(s["is_median"] for s in summaries), 2),
        "degradation": round(statistics.median(s["degradation"] for s in summaries), 2),
        "pick_stability": round(statistics.mean(s["pick_stability"] for s in summaries), 0),
        "pick_distribution": dict(sorted(picks.items(), key=lambda x: -x[1])),
        "oos_trades": sum(s["oos_trades"] for s in summaries),
    }
