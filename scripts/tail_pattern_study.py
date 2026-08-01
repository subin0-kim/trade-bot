"""아래꼬리 날의 지문 분석 — "회복하는 -3%와 계속 빠지는 -3%는 무엇이 다른가".

이벤트: 장중 시가 대비 -3% 첫 터치 (심볼-일당 1회).
전략형 결과: 터치가 매수 → **+3% 지정가 목표** (고가 터치 체결 ≈ 시가 복귀) →
미도달 시 당일 종가 청산. 비용 0.2% 차감. (참고로 240분 타임아웃 변형도 병기)

터치 '순간'에 관측 가능한 특징별로 목표 도달률·기대값을 비교해
일반 하락과 기술적 하락의 분리 가능성을 잰다:
  급락 속도(직전 5분 수익률) / 거래량 배율(1분/20분평균) / BTC 동반(-1%↓) /
  시간대 / 전일 수익률 / 레짐(bull·off)

  uv run python scripts/tail_pattern_study.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from backtest_upbit import load_5m
from bot_coin.main import TOP_MCAP_ALTS
from crypto_ensemble_verify import ensemble_flags
from crypto_regime import to_daily
from minute1_backtest import load_1m

UNIVERSE = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})
COST = 0.2
TARGET = 0.03


def main():
    daily_5m = {c.ts.date(): c for c in to_daily(load_5m("KRW-BTC"))}
    daily_1m = {c.ts.date(): c for c in to_daily(load_1m("KRW-BTC"))}
    merged = {**daily_5m, **daily_1m}
    ens = ensemble_flags([merged[d] for d in sorted(merged)])

    btc_bars = load_1m("KRW-BTC")
    btc_close = {b.ts: float(b.close) for b in btc_bars}
    btc_r5 = {}
    for b in btc_bars:
        prev = btc_close.get(b.ts - timedelta(minutes=5))
        if prev:
            btc_r5[b.ts] = float(b.close) / prev - 1

    events = []
    for sym in UNIVERSE:
        bars = load_1m(sym)
        if len(bars) < 2000:
            continue
        by_day: dict = {}
        for b in bars:
            by_day.setdefault(b.ts.date(), []).append(b)
        days_sorted = sorted(by_day)
        prev_ret = {}
        for k in range(1, len(days_sorted)):
            d0, d1 = days_sorted[k - 1], days_sorted[k]
            c0 = float(by_day[d0][-1].close)
            c1 = float(by_day[d1][-1].close)
            prev_ret[d1] = (c1 / c0 - 1) * 100  # d1의 '전일 수익률'로는 c0 대비 d0... 아래에서 사용 주의
        for d, day_bars in by_day.items():
            if len(day_bars) < 600:
                continue
            o = float(day_bars[0].open)
            level = o * 0.97
            vols = [float(b.volume) for b in day_bars]
            closes = [float(b.close) for b in day_bars]
            for i, b in enumerate(day_bars):
                if float(b.low) > level:
                    continue
                # --- 터치 순간의 특징 ---
                r5 = (closes[i] / closes[i - 5] - 1) * 100 if i >= 5 else 0.0
                vma = statistics.mean(vols[max(0, i - 20):i]) if i >= 5 else 0.0
                vr = vols[i] / vma if vma > 0 else 0.0
                brc = btc_r5.get(b.ts)
                # 전일 수익률 (전일 종가 대비 전전일 종가)
                idx = days_sorted.index(d)
                pr = prev_ret.get(days_sorted[idx - 1]) if idx >= 1 else None
                regime = "bull" if ens.get(d - timedelta(days=1), False) else "off"
                # --- 전략 결과: +3% 목표 / 종가 폴백 + 240분 타임아웃 변형 ---
                tgt = level * (1 + TARGET)
                out_close = (closes[-1] / level - 1) * 100 - COST
                hit = None
                for j in range(i + 1, len(day_bars)):
                    if float(day_bars[j].high) >= tgt:
                        hit = j
                        break
                net = (TARGET * 100 - COST) if hit is not None else out_close
                # 240분 변형
                j240 = min(i + 240, len(day_bars) - 1)
                if hit is not None and hit <= j240:
                    net240 = TARGET * 100 - COST
                else:
                    net240 = (closes[j240] / level - 1) * 100 - COST
                events.append({
                    "ts": b.ts, "d": d, "sym": sym, "net": net, "net240": net240,
                    "win": hit is not None, "r5": r5, "vr": vr, "brc": brc,
                    "hour": b.ts.hour, "prev": pr, "regime": regime,
                })
                break

    def show(tag, sel):
        if len(sel) < 30:
            print(f"  {tag:<24} n={len(sel)} (표본 부족)")
            return
        nets = [e["net"] for e in sel]
        wins = sum(1 for e in sel if e["win"]) / len(sel) * 100
        n240 = [e["net240"] for e in sel]
        print(f"  {tag:<24} n={len(sel):>5} | 목표도달 {wins:.0f}% | 기대값 {statistics.mean(nets):+.3f}% "
              f"(240분 변형 {statistics.mean(n240):+.3f}%)")

    print(f"이벤트 {len(events)}건 (장중 -3% 터치, 청산 +3% 목표/종가 폴백, 비용 차감)\n")
    show("전체", events)
    print("\n== 특징별 분리 (터치 순간 관측 가능) ==")
    print("[급락 속도 — 직전 5분]")
    show("5분 ≤ -2% (급락형)", [e for e in events if e["r5"] <= -2])
    show("5분 -2~-1%", [e for e in events if -2 < e["r5"] <= -1])
    show("5분 > -1% (완만형)", [e for e in events if e["r5"] > -1])
    print("[거래량 배율 — 1분/20분평균]")
    show("≥3배 (투매)", [e for e in events if e["vr"] >= 3])
    show("<3배 (조용)", [e for e in events if e["vr"] < 3])
    print("[BTC 동반 — 같은 순간 BTC 5분]")
    show("BTC ≤ -1% (시장 전체)", [e for e in events if e["brc"] is not None and e["brc"] <= -0.01])
    show("BTC > -1% (개별 코인)", [e for e in events if e["brc"] is not None and e["brc"] > -0.01])
    print("[레짐 (전일 기준)]")
    show("bull", [e for e in events if e["regime"] == "bull"])
    show("off", [e for e in events if e["regime"] == "off"])
    print("[전일 수익률]")
    show("전일 ≤ -5%", [e for e in events if e["prev"] is not None and e["prev"] <= -5])
    show("전일 -5~0%", [e for e in events if e["prev"] is not None and -5 < e["prev"] <= 0])
    show("전일 > 0%", [e for e in events if e["prev"] is not None and e["prev"] > 0])
    print("[시간대 (KST)]")
    show("00~08시", [e for e in events if e["hour"] < 9])
    show("09~16시", [e for e in events if 9 <= e["hour"] < 17])
    show("17~23시", [e for e in events if e["hour"] >= 17])
    print("\n== 복합 필터 (급락형 + 투매 거래량) ==")
    show("5분≤-2% AND 거래량≥3배", [e for e in events if e["r5"] <= -2 and e["vr"] >= 3])
    show("그 외 전부", [e for e in events if not (e["r5"] <= -2 and e["vr"] >= 3)])


if __name__ == "__main__":
    main()
