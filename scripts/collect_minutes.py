"""1분봉 수집기 — 유니버스 전 종목 × 최대 1년 (KIS 보관 한도).

- API: 주식일별분봉조회 (FHKST03010230), 1콜 30건, 과거 최대 1년
- 재개(resume) 가능: 종목별 진행 상태를 data/cache/minute/_progress.json에 기록,
  중단 후 재실행하면 이어서 수집한다 (밤샘 작업 안전장치)
- 산출물: data/cache/minute/{symbol}.jsonl (오름차순 정렬은 로드 시)

  uv run python scripts/collect_minutes.py                # 전체 유니버스
  uv run python scripts/collect_minutes.py --symbols 005930,000660
  uv run python scripts/collect_minutes.py --days 180     # 기간 축소
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")

from broker_kis import KISApiError, KISBroker
from universe_backtest import UNIVERSE, fetch_daily

MINUTE_DIR = Path("data/cache/minute")
PROGRESS_FILE = MINUTE_DIR / "_progress.json"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=1), encoding="utf-8")


def trading_days_for(symbol: str, days: int) -> list[date]:
    """일봉 캐시에서 거래일 목록 추출 (휴장일 스킵 목적)."""
    cutoff = date.today() - timedelta(days=days)
    return [c.ts.date() for c in fetch_daily(symbol)
            if cutoff <= c.ts.date() < date.today()]


def collect_day(broker: KISBroker, symbol: str, day: date) -> list[dict]:
    """하루치 1분봉 전체 수집 (뒤에서 앞으로 30건씩)."""
    rows: dict[str, dict] = {}
    cursor = "153000"
    day_str = day.strftime("%Y%m%d")
    for _ in range(20):  # 하루 최대 ~381봉 / 30 = 13콜 + 여유
        data = broker.client.get(
            "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice",
            "FHKST03010230",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": cursor,
                "FID_INPUT_DATE_1": day_str,
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_FAKE_TICK_INCU_YN": "N",
            },
        )
        batch = [r for r in data.get("output2", [])
                 if r.get("stck_bsop_date") == day_str and r.get("stck_cntg_hour")]
        if not batch:
            break
        for r in batch:
            rows[r["stck_cntg_hour"]] = {
                "ts": f"{day_str}T{r['stck_cntg_hour']}",
                "o": r["stck_oprc"], "h": r["stck_hgpr"],
                "l": r["stck_lwpr"], "c": r["stck_prpr"], "v": r["cntg_vol"],
            }
        earliest = min(r["stck_cntg_hour"] for r in batch)
        if earliest <= "090100":
            break
        prev_minute = datetime.strptime(earliest, "%H%M%S") - timedelta(minutes=1)
        cursor = prev_minute.strftime("%H%M%S")
    return [rows[k] for k in sorted(rows)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default=None, help="쉼표 구분 (기본: 전체 유니버스)")
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    symbols = ([s.strip() for s in args.symbols.split(",")] if args.symbols
               else list(UNIVERSE))
    MINUTE_DIR.mkdir(parents=True, exist_ok=True)
    progress = load_progress()
    broker = KISBroker(env="real")

    total_calls = 0
    for symbol in symbols:
        name = UNIVERSE.get(symbol, symbol)
        done_days = set(progress.get(symbol, []))
        days = [d for d in trading_days_for(symbol, args.days) if d.isoformat() not in done_days]
        if not days:
            print(f"{symbol} {name}: 완료 상태 (스킵)")
            continue
        print(f"{symbol} {name}: {len(days)}일 수집 시작", flush=True)

        out_file = MINUTE_DIR / f"{symbol}.jsonl"
        collected = 0
        for i, day in enumerate(days):
            try:
                bars = collect_day(broker, symbol, day)
            except KISApiError as e:
                print(f"  {day} 실패: {str(e)[:80]} — 종목 중단, 다음 재실행 시 재개", flush=True)
                break
            with out_file.open("a", encoding="utf-8") as f:
                for bar in bars:
                    f.write(json.dumps(bar) + "\n")
            collected += len(bars)
            total_calls += 13
            done_days.add(day.isoformat())
            if (i + 1) % 20 == 0 or i == len(days) - 1:
                progress[symbol] = sorted(done_days)
                save_progress(progress)
                print(f"  진행 {i+1}/{len(days)}일, {collected}봉", flush=True)
        progress[symbol] = sorted(done_days)
        save_progress(progress)

    print(f"\n수집 종료 (추정 콜 수 ~{total_calls:,})")


if __name__ == "__main__":
    main()
