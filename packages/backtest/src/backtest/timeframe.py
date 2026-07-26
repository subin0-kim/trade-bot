"""타임프레임 리샘플링 — 하위 TF 캔들을 상위 TF로 합성.

미래참조 방지의 핵심:
resample_progressive()는 "primary i번째 봉 시점에 완성돼 있는 상위 TF 봉 개수"를
함께 반환한다. 백테스터는 이 개수만큼만 잘라서 MarketView에 넣는다 —
진행 중인 상위 봉은 절대 노출되지 않는다.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trading_core.models import Candle


def _bucket_key(ts: datetime, rule: str):
    """캔들이 속하는 상위 TF 버킷 식별자."""
    if rule.endswith("m"):  # 분 단위 (예: "5m", "30m")
        minutes = int(rule[:-1])
        floored = ts.hour * 60 + ts.minute - (ts.hour * 60 + ts.minute) % minutes
        return (ts.date(), floored)
    if rule == "D":
        return ts.date()
    if rule == "W":
        iso = ts.isocalendar()
        return (iso.year, iso.week)
    if rule == "M":
        return (ts.year, ts.month)
    raise ValueError(f"지원하지 않는 타임프레임: {rule}")


def _merge(bucket: list[Candle]) -> Candle:
    return Candle(
        ts=bucket[0].ts,
        open=bucket[0].open,
        high=max(c.high for c in bucket),
        low=min(c.low for c in bucket),
        close=bucket[-1].close,
        volume=sum((c.volume for c in bucket), Decimal(0)),
    )


def resample(candles: list[Candle], rule: str) -> list[Candle]:
    """전체 합성 (마지막 봉은 미완성일 수 있음 — 라이브 조회용)."""
    bars: list[Candle] = []
    current_key = None
    bucket: list[Candle] = []
    for c in candles:
        key = _bucket_key(c.ts, rule)
        if key != current_key and bucket:
            bars.append(_merge(bucket))
            bucket = []
        current_key = key
        bucket.append(c)
    if bucket:
        bars.append(_merge(bucket))
    return bars


def resample_progressive(
    candles: list[Candle], rule: str
) -> tuple[list[Candle], list[int]]:
    """(완성봉 리스트, completed_counts) 반환.

    completed_counts[i] = primary i번째 봉 종료 시점에 완성된 상위 봉 개수.
    상위 봉은 '다음 버킷의 첫 캔들이 등장'해야 완성으로 간주한다.
    """
    bars: list[Candle] = []
    completed_counts: list[int] = []
    current_key = None
    bucket: list[Candle] = []

    for c in candles:
        key = _bucket_key(c.ts, rule)
        if key != current_key and bucket:
            bars.append(_merge(bucket))
            bucket = []
        current_key = key
        bucket.append(c)
        completed_counts.append(len(bars))

    return bars, completed_counts
