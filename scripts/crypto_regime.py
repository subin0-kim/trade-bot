"""코인 레짐 판별 — BTC 일봉을 시장 대표 지수로 사용.

주식의 KOSPI 지수 역할을 BTC가 대신한다 (알트가 BTC를 따라 움직이는 구조 전제).
동일한 RegimeClassifier(MA 조합 + 히스테리시스, look-ahead 없음)를 사용한다.

  uv run python scripts/crypto_regime.py             # 레짐 타임라인
  uv run python scripts/crypto_regime.py --corr      # BTC-알트 동조성까지 확인
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from regime import Regime, RegimeClassifier
from trading_core.models import Candle

CACHE_5M = Path("data/cache/upbit/5m")


def load_5m(symbol: str) -> list[Candle]:
    path = CACHE_5M / f"{symbol}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            out.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return out


def to_daily(candles: list[Candle]) -> list[Candle]:
    from backtest import resample

    return resample(candles, "D")


def regime_series(symbol: str = "KRW-BTC") -> dict[date, Regime]:
    daily = to_daily(load_5m(symbol))
    if len(daily) < 130:
        raise SystemExit(f"{symbol} 일봉 부족 — 수집 먼저")
    series = RegimeClassifier().classify_series(daily)
    return series, daily


def print_timeline(series: dict[date, Regime], daily: list[Candle]) -> None:
    price_by_date = {c.ts.date(): c.close for c in daily}
    print(f"BTC 일봉 {len(daily)}개 ({daily[0].ts.date()} ~ {daily[-1].ts.date()})\n")
    print("레짐 전환 타임라인:")
    prev = None
    spans: list[tuple[Regime, date, date]] = []
    start = None
    for d in sorted(series):
        r = series[d]
        if r != prev:
            if prev is not None and start is not None:
                spans.append((prev, start, d))
            price = price_by_date.get(d, 0)
            print(f"  {d}  {prev.value if prev else '(시작)':>8} → {r.value:<8} (BTC {price:,.0f})")
            prev, start = r, d
    if prev is not None and start is not None:
        spans.append((prev, start, sorted(series)[-1]))

    print("\n레짐별 구간 요약:")
    totals: dict[Regime, int] = {}
    for r, s, e in spans:
        days = (e - s).days
        totals[r] = totals.get(r, 0) + days
        if days >= 20:  # 짧은 구간은 생략
            p0, p1 = price_by_date.get(s, 0), price_by_date.get(e, 0)
            change = (float(p1) / float(p0) - 1) * 100 if p0 else 0
            print(f"  {r.value:<8} {s} ~ {e} ({days:>3}일)  BTC {change:+7.1f}%")
    total_days = sum(totals.values())
    print("\n레짐 비중:", ", ".join(
        f"{r.value} {d/total_days*100:.0f}%" for r, d in sorted(totals.items(), key=lambda x: -x[1])
    ))


def check_correlation(series: dict[date, Regime]) -> None:
    """BTC 레짐이 알트 전체를 대표하는가 — 레짐별 알트 수익률 확인."""
    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    print(f"\nBTC 레짐 vs 알트 수익률 ({len(symbols)}종목):")
    by_regime: dict[Regime, list[float]] = {r: [] for r in Regime}
    for symbol in symbols:
        daily = to_daily(load_5m(symbol))
        if len(daily) < 100:
            continue
        for i in range(1, len(daily)):
            d = daily[i].ts.date()
            r = series.get(d)
            if r is None or daily[i - 1].close <= 0:
                continue
            ret = float(daily[i].close / daily[i - 1].close - 1) * 100
            by_regime[r].append(ret)
    for r, rets in by_regime.items():
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        win = sum(1 for x in rets if x > 0) / len(rets) * 100
        print(f"  {r.value:<8} 일평균 {avg:+.3f}%  상승일 {win:.1f}%  (표본 {len(rets):,}일)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corr", action="store_true")
    args = parser.parse_args()

    series, daily = regime_series()
    print_timeline(series, daily)
    if args.corr:
        check_correlation(series)


if __name__ == "__main__":
    main()
