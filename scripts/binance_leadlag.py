"""바이낸스 → 업비트 선행-지연(lead-lag) 검증.

가설: 글로벌 가격 발견은 바이낸스에서 먼저 일어나고 업비트가 따라온다.
성립하면 "바이낸스 t분 급변 → 업비트 t+1분 추격"이 엣지가 된다.

방법 (심볼별로 두 거래소 1분봉을 분 단위 정렬 후):
  1. 교차상관: corr(바이낸스 수익률[t], 업비트 수익률[t+k]) k=-3..+3
     — 선행이 실재하면 k=+1이 역방향(업비트[t]→바이낸스[t+1])보다 커야 함
  2. 이벤트 추종: 바이낸스 1분 ±0.3/0.5/1.0% 급변 후 업비트의 다음 1/3/5분 수익률
     (순수익 = 왕복 비용 0.2% 차감, 매수 방향만 — 업비트 현물은 숏 불가)
  3. '아직 안 따라감' 조건부: 같은 t분의 업비트 동반 이동이 바이낸스의 절반 미만인
     경우만 — 이미 반영됐으면 추격할 게 없다

  uv run python scripts/binance_leadlag.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, "scripts")

from minute1_backtest import CACHE_1M, load_1m

CACHE_BN = Path("data/cache/binance/1m")
COST = 0.2               # 왕복 %
LAGS = range(-3, 4)
JUMPS = [0.003, 0.005, 0.010]


def load_binance_closes(pair: str) -> dict:
    path = CACHE_BN / f"{pair}.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            out[d["ts"]] = float(d["c"])
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return out


def align(upbit_bars, bn_closes):
    """공통 분(minute)만 남긴 (ts리스트, 업비트 종가, 바이낸스 종가). 결측 분은 건너뜀."""
    ts_list, up, bn = [], [], []
    for b in upbit_bars:
        key = b.ts.strftime("%Y-%m-%dT%H:%M:%S")
        c = bn_closes.get(key)
        if c is not None:
            ts_list.append(b.ts)
            up.append(float(b.close))
            bn.append(c)
    return ts_list, up, bn


def rets(xs, ts):
    """연속 분(60초 간격)에서만 수익률 계산, 아니면 None."""
    out = [None] * len(xs)
    for i in range(1, len(xs)):
        if (ts[i] - ts[i - 1]).total_seconds() == 60:
            out[i] = xs[i] / xs[i - 1] - 1
    return out


def corr(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 100:
        return None
    xs, ys = zip(*pairs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.stdev(xs), statistics.stdev(ys)
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / ((len(pairs) - 1) * sx * sy)


def main():
    pair_map = {
        "KRW-ETH": "ETHUSDT", "KRW-XRP": "XRPUSDT", "KRW-SOL": "SOLUSDT",
        "KRW-TRX": "TRXUSDT", "KRW-DOGE": "DOGEUSDT", "KRW-LINK": "LINKUSDT",
        "KRW-XLM": "XLMUSDT", "KRW-ADA": "ADAUSDT", "KRW-BCH": "BCHUSDT",
        "KRW-HBAR": "HBARUSDT", "KRW-AVAX": "AVAXUSDT", "KRW-SUI": "SUIUSDT",
        "KRW-SHIB": "SHIBUSDT", "KRW-UNI": "UNIUSDT", "KRW-NEAR": "NEARUSDT",
    }
    lag_corrs: dict[int, list[float]] = {k: [] for k in LAGS}
    rev_corrs: list[float] = []
    events: dict[tuple[float, str, int], list[float]] = {}

    for krw, pair in pair_map.items():
        bn_closes = load_binance_closes(pair)
        if not bn_closes:
            print(f"  {pair}: 바이낸스 데이터 없음 — 스킵", flush=True)
            continue
        bars = load_1m(krw)
        ts_list, up, bn = align(bars, bn_closes)
        if len(ts_list) < 10_000:
            print(f"  {pair}: 정렬 표본 부족 ({len(ts_list)}) — 스킵", flush=True)
            continue
        r_up = rets(up, ts_list)
        r_bn = rets(bn, ts_list)

        for k in LAGS:
            if k >= 0:
                c = corr(r_bn[: len(r_bn) - k or None], r_up[k:])
            else:
                c = corr(r_bn[-k:], r_up[: len(r_up) + k])
            if c is not None:
                lag_corrs[k].append(c)
        c = corr(r_up[:-1], r_bn[1:])
        if c is not None:
            rev_corrs.append(c)

        # 이벤트 추종 (양방향 트리거, 업비트 매수만)
        for i in range(2, len(ts_list) - 16):
            rb, ru = r_bn[i], r_up[i]
            if rb is None or ru is None:
                continue
            for j in JUMPS:
                if rb >= j:
                    lagging = ru < rb / 2
                    for h in (1, 3, 5, 15):
                        if all((ts_list[i + m] - ts_list[i + m - 1]).total_seconds() == 60
                               for m in range(1, h + 1)):
                            fwd = (up[i + h] / up[i] - 1) * 100 - COST
                            events.setdefault((j, "지연" if lagging else "동반", h), []).append(fwd)
                    break
        print(f"  {pair}: 정렬 {len(ts_list):,}분", flush=True)

    print("\n== 1) 교차상관 (15종 평균): 바이낸스[t] → 업비트[t+k] ==")
    for k in LAGS:
        vals = lag_corrs[k]
        print(f"  k={k:+d}: {statistics.mean(vals):+.4f}" if vals else f"  k={k:+d}: -")
    print(f"  역방향 (업비트[t]→바이낸스[t+1]): {statistics.mean(rev_corrs):+.4f}")

    print("\n== 2) 바이낸스 급등 → 업비트 추격 매수 (순수익, 비용 0.2% 차감) ==")
    for j in JUMPS:
        for cond in ("지연", "동반"):
            row = []
            for h in (1, 3, 5, 15):
                vals = events.get((j, cond, h), [])
                if vals:
                    pos = sum(1 for v in vals if v > 0) / len(vals) * 100
                    row.append(f"+{h}분 {statistics.median(vals):+.3f}%({pos:.0f}%)")
            n = len(events.get((j, cond, 1), []))
            if n:
                print(f"  ≥+{j*100:.1f}% [{cond}] n={n:,}: {' | '.join(row)}")


if __name__ == "__main__":
    main()
