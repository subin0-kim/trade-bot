"""급락 반전 매수 — 'BTC 동반 급락이면 매수 중지' 필터의 효과 실측.

가설: 개별 코인 급락(그 코인만의 유동성 공백)은 회복이 우세하지만, BTC까지 동시에
급락하는 순간은 시장 전체 이벤트(계엄·청산 캐스케이드)라 칼날 위험이 집중된다.
→ 이벤트 시점의 BTC 5분 수익률이 임계 이하면 매수를 걸렀을 때 성과 변화를 잰다.

  uv run python scripts/flash_dip_btc_filter.py
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
BTC_FILTER = -0.015          # BTC 5분 수익률이 이 이하면 '시장 전체 급락' → 매수 중지
HORIZONS = [15, 60, 240]


def collect_events():
    daily_5m = {c.ts.date(): c for c in to_daily(load_5m("KRW-BTC"))}
    daily_1m = {c.ts.date(): c for c in to_daily(load_1m("KRW-BTC"))}
    merged = {**daily_5m, **daily_1m}
    ens = ensemble_flags([merged[d] for d in sorted(merged)])

    btc_bars = load_1m("KRW-BTC")
    btc_close = {b.ts: float(b.close) for b in btc_bars}
    btc_r5 = {}
    for b in btc_bars:
        prev = btc_close.get(b.ts - timedelta(minutes=5))
        if prev:
            btc_r5[b.ts] = float(b.close) / prev - 1

    all_last = max(b[-1].ts for p in CACHE_1M.glob("*.jsonl") if (b := load_1m(p.stem)))
    boundary = all_last - timedelta(days=365)

    events = []
    for path in sorted(CACHE_1M.glob("*.jsonl")):
        if path.stem == "KRW-BTC":
            continue  # BTC 자신은 대상 외 (동반 급락 정의상 항상 걸러짐)
        bars = load_1m(path.stem)
        if len(bars) < 2000:
            continue
        closes = [float(b.close) for b in bars]
        lows = [float(b.low) for b in bars]
        last_evt = -COOLDOWN
        for i in range(5, len(bars) - HORIZONS[-1] - 1):
            r5 = closes[i] / closes[i - 5] - 1
            if r5 > -THRESH or i - last_evt < COOLDOWN:
                continue
            last_evt = i
            ts = bars[i].ts
            events.append({
                "symbol": path.stem, "ts": ts, "r5": r5 * 100,
                "half": "상승년" if ts < boundary else "하락년",
                "regime": "bull" if ens.get(ts.date(), False) else "off",
                "btc_r5": btc_r5.get(ts),
                **{f"f{h}": (closes[i + h] / closes[i] - 1) * 100 for h in HORIZONS},
                "knife": (min(lows[i + 1 : i + 61]) / closes[i] - 1) * 100,
            })
    return events


def report(label, evts):
    if not evts:
        print(f"  {label}: 0건")
        return
    f60 = [e["f60"] for e in evts]
    knives = sorted(e["knife"] for e in evts)
    k10 = knives[max(0, len(knives) // 10 - 1)]
    pos = sum(1 for v in f60 if v > 0) / len(f60) * 100
    print(f"  {label:<22} n={len(evts):>4} | +60분 중앙 {statistics.median(f60):+.2f}% "
          f"(평균 {statistics.mean(f60):+.2f}%, 양수 {pos:.0f}%) | "
          f"칼날 하위10% {k10:+.2f}% / 최악 {knives[0]:+.2f}%")


def main():
    events = collect_events()
    known_btc = [e for e in events if e["btc_r5"] is not None]
    print(f"급락 이벤트 {len(events)}건 (BTC 제외 16종목 × 2년, BTC r5 매칭 {len(known_btc)}건)\n")

    print(f"[전체 → BTC 필터({BTC_FILTER*100:.1f}%) 적용 비교]")
    for half in ("상승년", "하락년"):
        for regime in ("bull", "off"):
            cell = [e for e in known_btc if e["half"] == half and e["regime"] == regime]
            kept = [e for e in cell if e["btc_r5"] > BTC_FILTER]
            print(f"[{half} × {regime}]")
            report("필터 없음", cell)
            report("BTC 동반 제외", kept)
    print()

    excluded = [e for e in known_btc if e["btc_r5"] <= BTC_FILTER]
    print(f"[걸러진 이벤트 {len(excluded)}건의 성격]")
    report("제외분 전체", excluded)
    days = {}
    for e in excluded:
        days.setdefault(e["ts"].date(), []).append(e)
    top = sorted(days.items(), key=lambda kv: -len(kv[1]))[:5]
    for d, es in top:
        print(f"    {d}: {len(es)}건 (칼날 최악 {min(x['knife'] for x in es):+.1f}%)")
    print()

    print("[민감도: BTC 임계 바꿔도 결론이 유지되는가 — 전체 표본 +60분 중앙]")
    for th in (-0.01, -0.015, -0.02, -0.03):
        kept = [e for e in known_btc if e["btc_r5"] > th]
        report(f"임계 {th*100:.1f}%", kept)
    print()

    print("[설명용 예시]")
    typical = min((e for e in known_btc if e["half"] == "하락년" and e["regime"] == "off"
                   and e["btc_r5"] > BTC_FILTER),
                  key=lambda e: abs(e["f60"] - 2.0))
    knife = min(known_btc, key=lambda e: e["knife"])
    for tag, e in (("전형적 회복", typical), ("최악 칼날", knife)):
        print(f"  [{tag}] {e['symbol']} {e['ts']} | 5분 {e['r5']:+.2f}% (BTC {e['btc_r5']*100:+.2f}%)"
              f" | +15분 {e['f15']:+.2f}% / +60분 {e['f60']:+.2f}% / +240분 {e['f240']:+.2f}%"
              f" | 60분 내 저점 {e['knife']:+.2f}%")


if __name__ == "__main__":
    main()
