"""원리 기반 신규 코인 전략 — 이벤트 스터디 + 비용 반영 시뮬레이션.

유튜브 노하우에서 추출한 원리를 우리 실측과 결합해 설계한 전략 2종:

A. btc_shock_alt_follow (커플링 원리 × 실측 U자형 신호)
   BTC 09~10시(업비트 오픈 첫 시간) |수익률| ≥ 임계 → 10시에 알트 매수 → 익일 09시 청산
   근거: 실측 +0.744%(하락쇼크)/+1.011%(상승쇼크) vs 평시 0 이하

B. surge_continuation (대시세 익일 연속성 원리 — 우모)
   전일(09시 기준) 수익률 ≥ 임계% → 익일 09시 매수 → 1일 보유 후 청산
   근거 검증부터: 급등 후 D+1 수익률 분포 측정

공통: 비용 왕복 0.2% 반영, 전/후반 분할로 강건성 확인 (IS/OOS 정신)

  uv run python scripts/crypto_event_strategies.py
"""

from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")

from crypto_regime import load_5m

CACHE_5M = Path("data/cache/upbit/5m")
COST = 0.20  # 왕복 % (수수료 0.05×2 + 슬리피지 0.05×2)


def day_key(ts):
    d = ts.date()
    return d - timedelta(days=1) if ts.hour < 9 else d


def load_all(min_bars: int = 50_000):
    out = {}
    for p in sorted(CACHE_5M.glob("*.jsonl")):
        bars = load_5m(p.stem)
        if len(bars) >= min_bars:
            out[p.stem] = bars
    return out


def split_report(label: str, by_date: dict[date, list[float]], cost: float = COST) -> None:
    """이벤트일별 수익 리스트 → 전/후반 분할 리포트 (거래당 = 이벤트일의 종목 평균)."""
    days = sorted(by_date)
    if len(days) < 8:
        print(f"  {label}: 이벤트 {len(days)}일 — 표본 부족")
        return
    halves = {"전반": days[: len(days) // 2], "후반": days[len(days) // 2 :]}
    print(f"  {label} (이벤트 {len(days)}일):")
    for name, ds in halves.items():
        daily_means = [statistics.mean(by_date[d]) for d in ds]
        net = [m - cost for m in daily_means]
        win = sum(1 for v in net if v > 0) / len(net) * 100
        cum = 1.0
        for v in net:
            cum *= 1 + v / 100
        print(f"    {name}: 이벤트일 {len(ds):>3}, 순평균 {statistics.mean(net):+.3f}%/일, "
              f"승률 {win:.0f}%, 누적 {(cum-1)*100:+.1f}%")


# ---------------------------------------------------------------- 전략 A
def strategy_a(data: dict) -> None:
    print("=== A. btc_shock_alt_follow — BTC 오픈쇼크 → 알트 추종 ===")
    btc = data["KRW-BTC"]
    by_day_btc = defaultdict(list)
    for b in btc:
        by_day_btc[day_key(b.ts)].append(b)

    btc_first: dict[date, float] = {}
    for d, bars in by_day_btc.items():
        first = sorted([b for b in bars if b.ts.hour == 9], key=lambda b: b.ts)
        if len(first) >= 10:
            o, c = float(first[0].open), float(first[-1].close)
            if o > 0:
                btc_first[d] = (c / o - 1) * 100

    for threshold in (1.0, 1.5):
        by_date: dict[date, list[float]] = defaultdict(list)
        for symbol, bars in data.items():
            if symbol == "KRW-BTC":
                continue
            alt_by_day = defaultdict(list)
            for b in bars:
                alt_by_day[day_key(b.ts)].append(b)
            for d, day_bars in alt_by_day.items():
                sig = btc_first.get(d)
                if sig is None or abs(sig) < threshold:
                    continue
                # 진입 10:00 시가 → 청산 익일 09:00 직전 종가
                rest = sorted(
                    [b for b in day_bars if b.ts.hour >= 10 or b.ts.hour < 9],
                    key=lambda b: b.ts,
                )
                rest = [b for b in rest if not (b.ts.hour == 9)]
                if len(rest) < 100:
                    continue
                o, c = float(rest[0].open), float(rest[-1].close)
                if o > 0:
                    by_date[d].append((c / o - 1) * 100)
        split_report(f"|BTC 첫시간| ≥ {threshold}%", by_date)


# ---------------------------------------------------------------- 전략 B
def strategy_b(data: dict) -> None:
    print("\n=== B. surge_continuation — 대시세 익일 연속성 (우모 원리) ===")
    # 종목별 09시 기준 일봉 구성
    daily_by_symbol: dict[str, dict[date, tuple]] = {}
    for symbol, bars in data.items():
        by_day = defaultdict(list)
        for b in bars:
            by_day[day_key(b.ts)].append(b)
        days = {}
        for d, group in by_day.items():
            group.sort(key=lambda b: b.ts)
            days[d] = (float(group[0].open), float(group[-1].close))
        daily_by_symbol[symbol] = days

    for threshold in (10.0, 20.0, 30.0):
        by_date: dict[date, list[float]] = defaultdict(list)
        n_events = 0
        for symbol, days in daily_by_symbol.items():
            if symbol == "KRW-BTC":
                continue
            ordered = sorted(days)
            for i in range(1, len(ordered) - 1):
                d_prev, d_cur = ordered[i - 1], ordered[i]
                o0, c0 = days[d_prev]
                if o0 <= 0:
                    continue
                surge = (c0 / o0 - 1) * 100
                if surge < threshold:
                    continue
                if (d_cur - d_prev).days > 3:
                    continue
                n_events += 1
                o1, c1 = days[d_cur]
                if o1 > 0:
                    by_date[d_cur].append((c1 / o1 - 1) * 100)
        split_report(f"전일 +{threshold:.0f}% 이상 급등 (이벤트 {n_events}건)", by_date)


def main():
    data = load_all()
    print(f"로드: {len(data)}종목, 비용 왕복 {COST}%\n")
    strategy_a(data)
    strategy_b(data)


if __name__ == "__main__":
    main()
