"""단타봇(급락 반전) 게이트 스윕 — 임계 × 체결 지연 × 연도 분할.

전략: 5분 수익률 ≤ -X% 감지 → 매수 → 급락 직전가 지정가 매도 + 240분 타임아웃.
사이징은 검증된 보수안 (자산 5% × 10슬롯) 고정.

  1. 임계 스윕: -2.0 / -2.5 / -3.0 / -4.0% — 빈도 ↔ 엣지 강도, 연도별 분할 판정
  2. 체결 지연: 감지봉 종가(즉시) vs 다음 1분봉 종가(1분 폴링 지연) — 지연 민감도
  3. 워크포워드 관점: 상승년 성적으로 골랐을 때 하락년이 배신하는지 확인

  uv run python scripts/scalper_gate_sweep.py
"""

from __future__ import annotations

import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from flash_dip_portfolio_sim import BUDGET, simulate
from minute1_backtest import CACHE_1M, load_1m

COOLDOWN = 60
TIMEOUT = 240
THRESHOLDS = [0.02, 0.025, 0.03, 0.04]


def build():
    """한 패스로 전 임계의 이벤트 생성. (임계, 지연여부) → 이벤트 리스트."""
    events: dict[tuple[float, bool], list[dict]] = {(t, d): [] for t in THRESHOLDS for d in (False, True)}
    day_close: dict[str, dict] = {}
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

        last_evt = {t: -COOLDOWN for t in THRESHOLDS}
        for i in range(5, len(bars) - TIMEOUT - 2):
            r5 = closes[i] / closes[i - 5] - 1
            for th in THRESHOLDS:
                if r5 > -th or i - last_evt[th] < COOLDOWN:
                    continue
                last_evt[th] = i
                level = closes[i - 5]
                for delayed in (False, True):
                    i0 = i + 1 if delayed else i          # 체결봉
                    entry = closes[i0]
                    exit_off, exit_px = TIMEOUT, closes[i0 + TIMEOUT]
                    for j in range(i0 + 1, i0 + TIMEOUT + 1):
                        if highs[j] >= level:
                            exit_off, exit_px = j - i0, level
                            break
                    events[(th, delayed)].append({
                        "symbol": path.stem, "ts": bars[i0].ts, "entry": entry,
                        "exit_ts": bars[i0 + exit_off].ts, "exit": exit_px,
                    })
    for k in events:
        events[k].sort(key=lambda e: e["ts"])
    return events, day_close, all_last


def main():
    events, day_close, all_last = build()
    end = all_last.date()
    boundary = end - timedelta(days=365)
    periods = (("상승년", boundary - timedelta(days=365), boundary),
               ("하락년", boundary + timedelta(days=1), end))

    print(f"보수 사이징 (자산 5% × 10슬롯) | 시작 {BUDGET:,}원 | 비용 왕복 0.2%\n")
    print("== 1) 임계 스윕 (즉시 체결) ==")
    for th in THRESHOLDS:
        evts = events[(th, False)]
        row = []
        for label, s, e in periods:
            n = sum(1 for x in evts if s <= x["ts"].date() <= e)
            r = simulate(evts, day_close, s, e, 0.05, 10)
            row.append(f"{label} {r['ret']:+5.1f}% (MDD {r['mdd']:.1f}, 거래 {r['trades']}, 승률 {r['win']:.0f}%)")
        both = " | ".join(row)
        print(f"  -{th*100:.1f}%: {both}")

    print("\n== 2) 체결 지연 민감도 (1분 폴링 지연, 즉시 대비) ==")
    for th in (0.025, 0.03):
        for delayed in (False, True):
            evts = events[(th, delayed)]
            rets = []
            for label, s, e in periods:
                r = simulate(evts, day_close, s, e, 0.05, 10)
                rets.append(f"{label} {r['ret']:+5.1f}%")
            print(f"  -{th*100:.1f}% {'1분지연' if delayed else '즉시  '}: {' | '.join(rets)}")


if __name__ == "__main__":
    main()
