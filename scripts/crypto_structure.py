"""코인 시장 구조 분석 — 전략 설계의 기초 재료.

유튜브 노하우와 결합할 '검증 가능한 구조적 사실'을 우리 데이터에서 직접 측정한다:
  1. 시간대별 수익률·거래량 계절성 (KST) — 09시 업비트 일봉 리셋 효과 포함
  2. BTC 첫 1시간 → 알트 나머지 하루 선행성 (09시 기준일)
  3. 유동성 스윕 패턴 빈도 — 전일 저점 하향 이탈 후 회복 시 반등 확률

  uv run python scripts/crypto_structure.py
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


def load_all(min_bars: int = 50_000):
    out = {}
    for p in sorted(CACHE_5M.glob("*.jsonl")):
        bars = load_5m(p.stem)
        if len(bars) >= min_bars:
            out[p.stem] = bars
    return out


# ------------------------------------------------------- 1. 시간대 계절성
def hourly_seasonality(data: dict) -> None:
    ret_by_hour: dict[int, list[float]] = defaultdict(list)
    vol_by_hour: dict[int, list[float]] = defaultdict(list)

    for symbol, bars in data.items():
        # 시간별 수익률: 해당 시각의 12개 5분봉 누적
        by_key: dict[tuple, list] = defaultdict(list)
        for b in bars:
            by_key[(b.ts.date(), b.ts.hour)].append(b)
        daily_vol: dict[date, float] = defaultdict(float)
        for (d, h), group in by_key.items():
            daily_vol[d] += sum(float(b.volume) * float(b.close) for b in group)
        for (d, h), group in sorted(by_key.items()):
            group.sort(key=lambda b: b.ts)
            o, c = float(group[0].open), float(group[-1].close)
            if o > 0:
                ret_by_hour[h].append((c / o - 1) * 100)
            if daily_vol[d] > 0:
                hour_val = sum(float(b.volume) * float(b.close) for b in group)
                vol_by_hour[h].append(hour_val / daily_vol[d] * 100)

    print("=== 1. 시간대별 계절성 (KST, 26종목 합산) ===")
    print(f"{'시각':>4} {'평균수익%':>9} {'수익>0':>7} {'거래대금비중%':>12}")
    for h in range(24):
        rets = ret_by_hour[h]
        vols = vol_by_hour[h]
        if not rets:
            continue
        win = sum(1 for r in rets if r > 0) / len(rets) * 100
        marker = " ★" if h == 9 else ""
        print(f"{h:>3}시 {statistics.mean(rets):>+9.4f} {win:>6.1f}% "
              f"{statistics.mean(vols):>11.2f}{marker}")


# ------------------------------------------------------- 2. BTC → 알트 선행성
def btc_lead_alt(data: dict) -> None:
    """업비트 기준일(09시~익일 09시)에서 BTC 첫 1시간이 알트 나머지를 예측하는가."""
    btc = data.get("KRW-BTC")
    if not btc:
        return

    def day_key(ts):
        # 09시 기준일: 09시 이전은 전날로 귀속
        d = ts.date()
        return d - timedelta(days=1) if ts.hour < 9 else d

    # BTC 첫 1시간 (09:00~10:00) 수익률
    btc_first: dict[date, float] = {}
    by_day = defaultdict(list)
    for b in btc:
        by_day[day_key(b.ts)].append(b)
    for d, bars in by_day.items():
        first = sorted([b for b in bars if b.ts.hour == 9], key=lambda b: b.ts)
        if len(first) >= 10:
            o, c = float(first[0].open), float(first[-1].close)
            if o > 0:
                btc_first[d] = (c / o - 1) * 100

    # 알트의 10:00~익일 09:00 수익률
    buckets = {"BTC첫시간 ≤-1%": [], "-1~0%": [], "0~+1%": [], "≥+1%": []}
    for symbol, bars in data.items():
        if symbol == "KRW-BTC":
            continue
        alt_by_day = defaultdict(list)
        for b in bars:
            alt_by_day[day_key(b.ts)].append(b)
        for d, day_bars in alt_by_day.items():
            sig = btc_first.get(d)
            if sig is None:
                continue
            rest = sorted([b for b in day_bars if not (b.ts.hour == 9 and day_key(b.ts) == d)],
                          key=lambda b: b.ts)
            rest = [b for b in rest if (b.ts.hour >= 10 and day_key(b.ts) == d) or b.ts.hour < 9]
            if len(rest) < 100:
                continue
            o, c = float(rest[0].open), float(rest[-1].close)
            if o <= 0:
                continue
            ret = (c / o - 1) * 100
            if sig <= -1:
                buckets["BTC첫시간 ≤-1%"].append(ret)
            elif sig <= 0:
                buckets["-1~0%"].append(ret)
            elif sig <= 1:
                buckets["0~+1%"].append(ret)
            else:
                buckets["≥+1%"].append(ret)

    print("\n=== 2. BTC 첫 1시간(09~10시) → 알트 나머지 하루 ===")
    print(f"{'BTC 신호':>14} {'알트 평균%':>10} {'수익>0':>8} {'표본':>7}")
    for label, rets in buckets.items():
        if not rets:
            continue
        win = sum(1 for r in rets if r > 0) / len(rets) * 100
        print(f"{label:>14} {statistics.mean(rets):>+10.3f} {win:>7.1f}% {len(rets):>7,}")


# ------------------------------------------------------- 3. 유동성 스윕
def liquidity_sweep(data: dict) -> None:
    """전일(09시 기준) 저점을 5분봉 저가가 이탈했다가 종가가 회복하면 → 이후 반등하는가."""
    def day_key(ts):
        d = ts.date()
        return d - timedelta(days=1) if ts.hour < 9 else d

    sweep_next: list[float] = []
    break_next: list[float] = []
    for symbol, bars in data.items():
        by_day = defaultdict(list)
        for b in bars:
            by_day[day_key(b.ts)].append(b)
        days = sorted(by_day)
        for i in range(1, len(days)):
            prev_bars = by_day[days[i - 1]]
            prev_low = min(float(b.low) for b in prev_bars)
            today = sorted(by_day[days[i]], key=lambda b: b.ts)
            for j, b in enumerate(today[:-24]):  # 마지막 2시간 제외 (이후 수익 측정 공간)
                lo, cl = float(b.low), float(b.close)
                if lo < prev_low:  # 전일 저점 이탈
                    fwd_close = float(today[j + 24].close)  # 2시간 후
                    ret = (fwd_close / cl - 1) * 100
                    if cl > prev_low:
                        sweep_next.append(ret)   # 이탈 후 즉시 회복 = 스윕
                    else:
                        break_next.append(ret)   # 이탈 유지 = 진짜 붕괴
                    break  # 하루 첫 이벤트만

    print("\n=== 3. 유동성 스윕 (전일 저점 이탈 → 2시간 후) ===")
    for label, rets in [("스윕(저점 이탈 후 즉시 회복)", sweep_next),
                        ("붕괴(이탈 유지)", break_next)]:
        if not rets:
            continue
        win = sum(1 for r in rets if r > 0) / len(rets) * 100
        print(f"  {label}: 평균 {statistics.mean(rets):+.3f}%, "
              f"수익>0 {win:.1f}%, 표본 {len(rets):,}")


def main():
    data = load_all()
    print(f"로드: {len(data)}종목\n")
    hourly_seasonality(data)
    btc_lead_alt(data)
    liquidity_sweep(data)


if __name__ == "__main__":
    main()
