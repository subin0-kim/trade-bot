"""급락 반전 봇 가상 운용 — "1년 전에 1,000만원으로 시작했다면 지금 얼마?"

전략 (2026-07-31 확정 초안):
  진입: 5분 수익률 ≤ -3% 확인 순간의 1분봉 종가 매수 (60분 쿨다운, 심볼당 1포지션)
  청산: 급락 직전가(5분 전 종가) 지정가 매도, 240분 내 미도달 시 그 시점 종가
  비용: 왕복 0.2% | 유니버스: 시총15+ETH (BTC 제외) | 레짐 필터 없음

사이징 3안 비교 (칼날 방어 = 사이징이라는 결론의 정량화):
  보수: 자산 5% × 최대 10슬롯 | 중간: 10% × 5 | 공격: 25% × 4

한계: 진입 체결 = 이벤트 봉 종가 가정 (지정가 대기 실전과 다를 수 있음),
      MDD는 일 단위 마크 (장중 최저점은 이보다 깊음 — 계엄류 순간낙폭 미반영)

  uv run python scripts/flash_dip_portfolio_sim.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, "scripts")

from minute1_backtest import CACHE_1M, load_1m

THRESH = 0.03
COOLDOWN = 60
TIMEOUT = 240
COST = 0.002               # 왕복
BUDGET = 10_000_000


def build_events_and_marks():
    events = []
    day_close: dict[str, dict[date, float]] = {}
    all_last = None
    for path in sorted(CACHE_1M.glob("*.jsonl")):
        if path.stem == "KRW-BTC":
            continue
        bars = load_1m(path.stem)
        if len(bars) < 2000:
            continue
        all_last = max(all_last, bars[-1].ts) if all_last else bars[-1].ts
        closes = [float(b.close) for b in bars]
        highs = [float(b.high) for b in bars]
        dc = day_close.setdefault(path.stem, {})
        for b in bars:
            dc[b.ts.date()] = float(b.close)

        last_evt = -COOLDOWN
        for i in range(5, len(bars) - TIMEOUT - 1):
            r5 = closes[i] / closes[i - 5] - 1
            if r5 > -THRESH or i - last_evt < COOLDOWN:
                continue
            last_evt = i
            level = closes[i - 5]
            exit_off, exit_px = TIMEOUT, closes[i + TIMEOUT]
            for j in range(i + 1, i + TIMEOUT + 1):
                if highs[j] >= level:
                    exit_off, exit_px = j - i, level
                    break
            events.append({
                "symbol": path.stem, "ts": bars[i].ts, "entry": closes[i],
                "exit_ts": bars[min(i + exit_off, len(bars) - 1)].ts, "exit": exit_px,
            })
    events.sort(key=lambda e: e["ts"])
    return events, day_close, all_last


def simulate(events, day_close, start, end, slot_frac, max_pos):
    """이벤트 순서대로 단일 패스 시뮬 + 일 단위 자산 마크."""
    cash = float(BUDGET)
    live: list[dict] = []
    closed: list[float] = []
    skipped = 0
    curve: list[float] = []
    idx = 0

    def close_due(now):
        nonlocal cash
        for p in [p for p in live if p["exit_ts"] <= now]:
            proceeds = p["size"] * (p["exit"] / p["entry"]) * (1 - COST)
            cash += proceeds
            closed.append(proceeds - p["size"])
            live.remove(p)

    d = start
    from datetime import datetime as _dt
    while d <= end:
        day_end = _dt.combine(d + timedelta(days=1), _dt.min.time())
        while idx < len(events) and events[idx]["ts"] < day_end:
            e = events[idx]; idx += 1
            if e["ts"].date() < start:
                continue
            close_due(e["ts"])
            if len(live) >= max_pos or any(p["symbol"] == e["symbol"] for p in live):
                skipped += 1
                continue
            equity = cash + sum(p["size"] for p in live)
            size = slot_frac * equity
            if size > cash or size < 5000:
                skipped += 1
                continue
            cash -= size
            live.append({**e, "size": size})
        close_due(day_end)
        mark = cash
        for p in live:
            px = day_close[p["symbol"]].get(d)
            mark += p["size"] * (px / p["entry"]) if px else p["size"]
        curve.append(mark)
        d += timedelta(days=1)
    close_due(events[-1]["exit_ts"] + timedelta(days=1))
    final = cash if not live else curve[-1]
    peak, mdd = 0.0, 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak * 100)
    wins = sum(1 for p in closed if p > 0)
    return {
        "final": final, "ret": (final / BUDGET - 1) * 100, "mdd": mdd,
        "trades": len(closed), "win": wins / len(closed) * 100 if closed else 0,
        "skipped": skipped,
        "avg": statistics.mean(p for p in closed) if closed else 0,
    }


def main():
    events, day_close, all_last = build_events_and_marks()
    end = all_last.date()
    boundary = end - timedelta(days=365)
    btc = load_1m("KRW-BTC")
    btc_daily = {b.ts.date(): float(b.close) for b in btc}

    for period, (start, stop) in (("상승년 2024-08~2025-07", (boundary - timedelta(days=365), boundary)),
                                  ("하락년 2025-08~현재", (boundary + timedelta(days=1), end))):
        n_evt = sum(1 for e in events if start <= e["ts"].date() <= stop)
        print(f"[{period}] 이벤트 {n_evt}건 | 시작 {BUDGET:,}원")
        for label, frac, mx in (("보수 (5%×10슬롯)", 0.05, 10),
                                ("중간 (10%×5슬롯)", 0.10, 5),
                                ("공격 (25%×4슬롯)", 0.25, 4)):
            r = simulate(events, day_close, start, stop, frac, mx)
            print(f"  {label:<16} 최종 {r['final']:>12,.0f}원 ({r['ret']:+.1f}%) | MDD {r['mdd']:.1f}% | "
                  f"거래 {r['trades']} (승률 {r['win']:.0f}%, 평균 {r['avg']:+,.0f}원) | 슬롯부족 스킵 {r['skipped']}")
        b0 = next(btc_daily[d] for d in sorted(btc_daily) if d >= start)
        b1 = max(btc_daily[d] for d in [max(d for d in btc_daily if d <= stop)])
        print(f"  참고 — 같은 기간 BTC 보유: {(b1/b0-1)*100:+.1f}%\n")


if __name__ == "__main__":
    main()
