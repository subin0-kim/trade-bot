"""바이낸스 1분봉 수집기 — 선행-지연(lead-lag) 연구용.

공개 API(키 불필요) /api/v3/klines, 콜당 1000봉, 과거 방향 무제한.
캐시 스키마는 업비트와 동일({ts,o,h,l,c,v})이되 **ts를 KST로 변환 저장** —
업비트 1분봉과 분 단위 정렬을 바로 할 수 있게 하기 위함.

  uv run python scripts/collect_binance.py --days 730
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

CACHE = Path("data/cache/binance/1m")
BASE = "https://api.binance.com/api/v3/klines"
KST = timezone(timedelta(hours=9))

# 업비트 유니버스 → 바이낸스 USDT 페어 (CRO는 바이낸스 스팟 미상장 가능 — 404 시 스킵)
PAIRS = {
    "KRW-ETH": "ETHUSDT", "KRW-XRP": "XRPUSDT", "KRW-SOL": "SOLUSDT",
    "KRW-TRX": "TRXUSDT", "KRW-DOGE": "DOGEUSDT", "KRW-LINK": "LINKUSDT",
    "KRW-XLM": "XLMUSDT", "KRW-ADA": "ADAUSDT", "KRW-BCH": "BCHUSDT",
    "KRW-HBAR": "HBARUSDT", "KRW-AVAX": "AVAXUSDT", "KRW-SUI": "SUIUSDT",
    "KRW-SHIB": "SHIBUSDT", "KRW-CRO": "CROUSDT", "KRW-UNI": "UNIUSDT",
    "KRW-NEAR": "NEARUSDT", "KRW-BTC": "BTCUSDT",
}


def collect(session: requests.Session, pair: str, days: int) -> int:
    path = CACHE / f"{pair}.jsonl"
    start_ms = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines:
            last_kst = datetime.fromisoformat(json.loads(lines[-1])["ts"])
            start_ms = int(last_kst.replace(tzinfo=KST).timestamp() * 1000) + 60_000

    added = 0
    with path.open("a", encoding="utf-8") as f:
        while True:
            for attempt in range(4):
                try:
                    res = session.get(BASE, params={
                        "symbol": pair, "interval": "1m",
                        "startTime": start_ms, "limit": 1000,
                    }, timeout=15)
                    break
                except requests.RequestException:
                    time.sleep(2.0 * (attempt + 1))
            else:
                print(f"    네트워크 실패 — 중단 (재실행 시 이어받음)", flush=True)
                return added
            if res.status_code == 400 and "Invalid symbol" in res.text:
                print(f"    미상장 심볼 — 스킵", flush=True)
                return added
            if res.status_code in (418, 429):
                time.sleep(30)
                continue
            res.raise_for_status()
            rows = res.json()
            if not rows:
                return added
            for r in rows:
                ts = datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).astimezone(KST)
                f.write(json.dumps({
                    "ts": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                    "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": r[5],
                }) + "\n")
                added += 1
            start_ms = rows[-1][0] + 60_000
            if len(rows) < 1000:
                return added
            time.sleep(0.12)  # ~8콜/초 — weight 한도(6000/분) 대비 넉넉


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=730)
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    for i, (krw, pair) in enumerate(PAIRS.items(), 1):
        added = collect(session, pair, args.days)
        print(f"[{i}/{len(PAIRS)}] {pair}: +{added:,}봉", flush=True)
    print(f"수집 완료 → {CACHE}")


if __name__ == "__main__":
    main()
