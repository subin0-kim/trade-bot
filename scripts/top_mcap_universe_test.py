"""시가총액 상위 10 알트 유니버스 vs 기존 24종 유니버스 — 위성 돌파 비교.

사용자 지시(2026-07-28): 알트 대상을 시총 10위 이내로 축소.
시총 순위는 업비트 API에 없으므로 정적 리스트로 고정 (외부 시세 기준, 수동 갱신):
  ETH, XRP, SOL, DOGE, ADA, TRX, LINK, AVAX, SUI, XLM

비교 (앙상블 + bull_age≥5 동일 적용):
  A. 기존 유니버스 (거래대금 상위 24종)
  B. 시총 상위 10종
각각 위성 단독 + 코어50:위성50 결합, 자산곡선 분할 포함.

  uv run python scripts/top_mcap_universe_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest_upbit import load_5m, to_timeframe
from crypto_ensemble_verify import (CACHE_5M, btc_core_curve, curve_stats,
                                    ensemble_flags, portfolio_curve)
from crypto_regime import to_daily

TOP_MCAP_ALTS = ["KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA",
                 "KRW-TRX", "KRW-LINK", "KRW-AVAX", "KRW-SUI", "KRW-XLM"]


def delayed_states(ens):
    out, age = {}, 0
    for d in sorted(ens):
        age = age + 1 if ens[d] else 0
        out[d] = "bull" if age >= 5 else "off"
    return out


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    states = delayed_states(ens)
    btc_rets = btc_core_curve(btc_daily, ens)

    all_syms = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    newly = {"KRW-ADA", "KRW-TRX", "KRW-LINK", "KRW-AVAX", "KRW-SUI"}  # 이번에 수집한 시총용
    universes = {
        "A. 기존 24종": [s for s in all_syms if s != "KRW-BTC" and s not in newly],
        "B. 시총 10종": TOP_MCAP_ALTS,
    }

    for label, syms in universes.items():
        data = {}
        for s in syms:
            if not (CACHE_5M / f"{s}.jsonl").exists():
                print(f"  ({s} 캐시 없음 — 제외)")
                continue
            bars = to_timeframe(load_5m(s), "240m")
            if len(bars) > 600:
                data[s] = bars
        print(f"\n=== {label} ({len(data)}종목) ===")
        alt = portfolio_curve(states, data)
        curve_stats(f"{label} 위성 단독", alt)
        common = sorted(set(alt) & set(btc_rets))
        combo = {d: 0.5 * alt[d] + 0.5 * btc_rets[d] for d in common}
        curve_stats(f"{label} 코어50+위성50", combo)


if __name__ == "__main__":
    main()
