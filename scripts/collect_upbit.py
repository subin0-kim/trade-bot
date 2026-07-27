"""업비트 분봉 수집기 — 유니버스 선정 + 캔들 아카이브.

주식과 달리 24시간 거래이므로 데이터량이 크다:
  5분봉 1년 = 365×288 ≈ 105,120봉/코인 (1콜 200봉 → ~526콜, 코인당 약 1분)
  1분봉 1년 = 525,600봉/코인 (~2,628콜, 코인당 약 5분)

기본은 5분봉 (단타 백테스트에 충분하고 15/30/60분으로 리샘플 가능).

  uv run python scripts/collect_upbit.py --list-universe      # 유니버스 후보만 출력
  uv run python scripts/collect_upbit.py                      # 상위 20종목 × 5분봉 1년
  uv run python scripts/collect_upbit.py --unit 1 --top 5     # 1분봉, 상위 5종목
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from broker_upbit import UpbitApiError, UpbitBroker

CACHE_ROOT = Path("data/cache/upbit")

# 스테이블코인·원화연동은 단타 대상에서 제외 (변동성 없음)
EXCLUDE = {"KRW-USDT", "KRW-USDC", "KRW-DAI", "KRW-USD1", "KRW-BUSD", "KRW-TUSD"}


def select_universe(broker: UpbitBroker, top: int, min_days: int = 300) -> list[tuple[str, float]]:
    """24시간 거래대금 상위 N종목 — 단, 상장 이력이 min_days 이상인 종목만.

    거래대금 상위에는 상장 직후 급등 코인이 대거 포함된다(예: 2026-07 기준 1위 EUL은 상장 1일차).
    이력이 없으면 백테스트가 불가능할뿐더러, '오늘 뜨거운 코인'으로 과거를 검증하는 건
    생존 편향이다. 따라서 이력 필터를 건 뒤 상위를 취한다.
    """
    markets = [m for m in broker.list_krw_markets() if m not in EXCLUDE]
    rows = []
    for i in range(0, len(markets), 100):  # /v1/ticker는 다중 마켓 조회 지원
        chunk = markets[i : i + 100]
        rows.extend(broker.client.get("/v1/ticker", {"markets": ",".join(chunk)}))
    ranked = sorted(rows, key=lambda r: r.get("acc_trade_price_24h", 0), reverse=True)

    selected: list[tuple[str, float]] = []
    skipped: list[tuple[str, int]] = []
    for r in ranked:
        if len(selected) >= top:
            break
        symbol = r["market"]
        # 일봉 개수로 상장 이력 확인 (1콜)
        days_available = len(broker.client.get(
            "/v1/candles/days", {"market": symbol, "count": 200}
        ))
        if days_available >= min(min_days, 200):
            selected.append((symbol, r.get("acc_trade_price_24h", 0)))
        else:
            skipped.append((symbol, days_available))

    if skipped:
        preview = ", ".join(f"{s}({d}일)" for s, d in skipped[:8])
        print(f"이력 부족으로 제외 {len(skipped)}종목: {preview}"
              f"{' …' if len(skipped) > 8 else ''}\n")
    return selected


def collect_symbol(broker: UpbitBroker, symbol: str, unit: int, days: int) -> int:
    """지정 심볼의 분봉을 과거 방향으로 수집. 이미 받은 구간은 건너뛴다."""
    out_dir = CACHE_ROOT / f"{unit}m"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}.jsonl"

    existing: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                existing[row["ts"]] = row
            except json.JSONDecodeError:
                continue

    target_start = datetime.now() - timedelta(days=days)
    # 이어받기 최적화: 기존 데이터가 있으면 그 시작점부터 과거로 이어간다
    # (매번 현재부터 다시 훑으면 이미 받은 구간을 재조회해 콜을 두 배로 낭비)
    cursor: str | None = min(existing) if existing else None
    added = 0

    while True:
        try:
            candles = broker.get_minute_candles(symbol, to_time=cursor, unit=unit, count=200)
        except UpbitApiError as e:
            print(f"    조회 실패({str(e)[:60]}) — 중단, 재실행 시 이어받음")
            break
        if not candles:
            break

        for c in candles:
            key = c.ts.strftime("%Y-%m-%dT%H:%M:%S")
            if key not in existing:
                existing[key] = {
                    "ts": key, "o": str(c.open), "h": str(c.high),
                    "l": str(c.low), "c": str(c.close), "v": str(c.volume),
                }
                added += 1

        oldest = candles[0].ts
        if oldest <= target_start:
            break
        next_cursor = oldest.strftime("%Y-%m-%dT%H:%M:%S")
        # 상장 시점에 도달하면 API가 같은 구간을 반복 반환한다 → 커서 정지 시 종료
        # (이 가드가 없으면 신규 상장 코인에서 무한 루프)
        if next_cursor == cursor:
            break
        cursor = next_cursor

    with path.open("w", encoding="utf-8") as f:
        for key in sorted(existing):
            f.write(json.dumps(existing[key]) + "\n")
    return added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=20, help="거래대금 상위 N종목")
    parser.add_argument("--unit", type=int, default=5, help="분봉 단위 (1/3/5/15/30/60/240)")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--list-universe", action="store_true", help="유니버스만 출력하고 종료")
    parser.add_argument("--symbols", default=None, help="쉼표 구분 (지정 시 유니버스 선정 생략)")
    args = parser.parse_args()

    broker = UpbitBroker()

    if args.symbols:
        universe = [(s.strip(), 0.0) for s in args.symbols.split(",")]
    else:
        universe = select_universe(broker, args.top)
        print(f"유니버스 (24h 거래대금 상위 {args.top}, 스테이블 제외):")
        for i, (symbol, value) in enumerate(universe, 1):
            print(f"  {i:2d}. {symbol:<14} {value/1e8:>10,.0f}억원")
        if args.list_universe:
            return

    print(f"\n{args.unit}분봉 {args.days}일치 수집 시작 ({len(universe)}종목)")
    universe_file = CACHE_ROOT / "universe.json"
    universe_file.parent.mkdir(parents=True, exist_ok=True)
    universe_file.write_text(
        json.dumps([s for s, _ in universe], ensure_ascii=False, indent=1), encoding="utf-8"
    )

    for i, (symbol, _) in enumerate(universe, 1):
        added = collect_symbol(broker, symbol, args.unit, args.days)
        path = CACHE_ROOT / f"{args.unit}m" / f"{symbol}.jsonl"
        total = sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0
        print(f"  [{i}/{len(universe)}] {symbol}: +{added:,}봉 (누적 {total:,})", flush=True)

    print(f"\n수집 완료 → {CACHE_ROOT / f'{args.unit}m'}")


if __name__ == "__main__":
    main()
