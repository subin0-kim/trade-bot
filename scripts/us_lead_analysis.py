"""미국장 야간 수익률 → 다음 날 한국장 선행성 분석.

가설: 미국장(새벽 마감)이 좋으면/나쁘면 당일 한국장도 같은 방향.
핵심 질문: 그 효과가 '갭'(못 먹는 수익)에 그치는가, '장중'(먹을 수 있는 수익)까지 이어지는가.

시간 구조 (look-ahead 없음):
  미국 d일 세션 마감 = KST d+1 새벽 05~06시 → 한국 d+1일 09시 개장 전에 확정 정보

  uv run python scripts/us_lead_analysis.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from trading_core.models import Candle
from universe_backtest import UNIVERSE, fetch_daily

INDEX_CACHE_DIR = Path("data/cache/index")
FETCH_START = date(2021, 1, 1)

BUCKETS = [
    ("≤-2%", -99.0, -2.0),
    ("-2~-1%", -2.0, -1.0),
    ("-1~-0.3%", -1.0, -0.3),
    ("-0.3~+0.3%", -0.3, 0.3),
    ("+0.3~1%", 0.3, 1.0),
    ("+1~2%", 1.0, 2.0),
    ("≥+2%", 2.0, 99.0),
]


def fetch_us_index(code: str, refresh: bool = False) -> list[Candle]:
    """해외지수 일봉 (FHKST03030100, 시장구분 N). 65일 윈도 분할 + 캐시."""
    cache = INDEX_CACHE_DIR / f"us_{code}.jsonl"
    if cache.exists() and not refresh:
        out = []
        for line in cache.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            out.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        return out

    from broker_kis import KISBroker
    broker = KISBroker(env="real")
    candles = []
    cursor = FETCH_START
    end = date.today()
    while cursor <= end:
        window_end = min(cursor + timedelta(days=65), end)
        data = broker.client.get(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
            "FHKST03030100",
            {
                "FID_COND_MRKT_DIV_CODE": "N",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": cursor.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": window_end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
            },
        )
        for row in data.get("output2", []):
            if not row.get("stck_bsop_date"):
                continue
            candles.append(Candle(
                ts=datetime.strptime(row["stck_bsop_date"], "%Y%m%d"),
                open=Decimal(row["ovrs_nmix_oprc"]),
                high=Decimal(row["ovrs_nmix_hgpr"]),
                low=Decimal(row["ovrs_nmix_lwpr"]),
                close=Decimal(row["ovrs_nmix_prpr"]),
                volume=Decimal(row.get("acml_vol") or "0"),
            ))
        cursor = window_end + timedelta(days=1)
    unique = {c.ts: c for c in candles}
    ordered = [unique[ts] for ts in sorted(unique)]
    INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8") as f:
        for c in ordered:
            f.write(json.dumps({
                "ts": c.ts.isoformat(), "o": str(c.open), "h": str(c.high),
                "l": str(c.low), "c": str(c.close), "v": str(c.volume),
            }) + "\n")
    return ordered


def load_kospi() -> list[Candle]:
    cache = INDEX_CACHE_DIR / "0001.jsonl"
    out = []
    for line in cache.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        out.append(Candle(
            ts=datetime.fromisoformat(d["ts"]),
            open=Decimal(d["o"]), high=Decimal(d["h"]),
            low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
        ))
    return out


def build_us_overnight_returns(us: list[Candle]) -> dict[date, float]:
    """us_date d의 야간 수익률(%). 한국 d 이후 첫 거래일에 사용 가능."""
    returns = {}
    for i in range(1, len(us)):
        prev, cur = float(us[i - 1].close), float(us[i].close)
        if prev > 0:
            returns[us[i].ts.date()] = (cur / prev - 1) * 100
    return returns


def latest_us_return_for(kr_day: date, us_dates: list[date], us_returns: dict[date, float]) -> float | None:
    """한국 kr_day 개장 전 확정된 가장 최근 미국 야간 수익률."""
    import bisect

    idx = bisect.bisect_left(us_dates, kr_day) - 1  # us_date < kr_day
    if idx < 0:
        return None
    return us_returns.get(us_dates[idx])


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def main():
    print("나스닥 종합(COMP) 일봉 수집...")
    us = fetch_us_index("COMP")
    print(f"  {len(us)}봉 ({us[0].ts.date()} ~ {us[-1].ts.date()})")
    us_returns = build_us_overnight_returns(us)
    us_dates = sorted(us_returns)

    kospi = load_kospi()
    print(f"KOSPI {len(kospi)}봉 로드")

    # 유니버스 종목별 (일자 → 캔들) 매핑
    stock_by_date: dict[str, dict[date, Candle]] = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            stock_by_date[symbol] = {c.ts.date(): c for c in candles}
        except Exception:
            continue
    print(f"유니버스 {len(stock_by_date)}종목 로드\n")

    # 한국 거래일별 관측치 구성
    rows = []  # (us_ret, kospi_gap, kospi_intraday, universe_median_intraday)
    for i in range(1, len(kospi)):
        day = kospi[i].ts.date()
        us_ret = latest_us_return_for(day, us_dates, us_returns)
        if us_ret is None:
            continue
        prev_close = float(kospi[i - 1].close)
        o, c = float(kospi[i].open), float(kospi[i].close)
        if prev_close <= 0 or o <= 0:
            continue
        gap = (o / prev_close - 1) * 100
        intraday = (c / o - 1) * 100

        stock_intras = []
        for by_date in stock_by_date.values():
            sc = by_date.get(day)
            if sc and float(sc.open) > 0:
                stock_intras.append((float(sc.close) / float(sc.open) - 1) * 100)
        universe_intra = statistics.median(stock_intras) if stock_intras else None
        rows.append((us_ret, gap, intraday, universe_intra))

    print(f"관측치 {len(rows)}일 (2021~2026)\n")

    # 상관계수
    us_all = [r[0] for r in rows]
    print(f"상관계수 (나스닥 야간수익률 vs):")
    print(f"  KOSPI 갭(시가):        r = {pearson(us_all, [r[1] for r in rows]):+.3f}")
    print(f"  KOSPI 장중(시가→종가):  r = {pearson(us_all, [r[2] for r in rows]):+.3f}")
    uni_rows = [(r[0], r[3]) for r in rows if r[3] is not None]
    print(f"  유니버스 중앙 장중:      r = {pearson([r[0] for r in uni_rows], [r[1] for r in uni_rows]):+.3f}\n")

    # 버킷 분석
    header = (f"{'나스닥 야간':<12}{'일수':>5}{'갭 평균':>8}{'장중 평균':>9}{'장중>0':>7}"
              f"{'유니버스 장중':>11}")
    print(header)
    print("-" * len(header))
    for label, lo, hi in BUCKETS:
        bucket = [r for r in rows if lo <= r[0] < hi]
        if not bucket:
            continue
        gaps = [r[1] for r in bucket]
        intras = [r[2] for r in bucket]
        unis = [r[3] for r in bucket if r[3] is not None]
        win = sum(1 for v in intras if v > 0) / len(intras) * 100
        uni_med = statistics.median(unis) if unis else 0.0
        print(f"{label:<12}{len(bucket):>5}{statistics.mean(gaps):>+8.2f}"
              f"{statistics.mean(intras):>+9.3f}{win:>6.0f}%{uni_med:>+11.3f}")

    print("\n(갭 = 전일종가→시가, 장중 = 시가→종가. 단위 %. '먹을 수 있는' 것은 장중뿐)")


if __name__ == "__main__":
    main()
