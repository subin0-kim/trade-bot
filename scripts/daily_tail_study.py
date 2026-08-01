"""일봉 꼬리 연구 — "아래꼬리 3%가 얼마나 흔하고, 장중 -3% 터치는 기회인가".

정의 (시가 기준 %):
  아래꼬리 = (min(시,종) - 저가) / 시가 ≥ 3%
  윗꼬리   = (고가 - max(시,종)) / 시가 ≥ 3%
  대상: 하루 등락폭 (고가-저가)/시가 ≥ 5%인 날

빈도: 심볼-일 단위와 달력일 단위(16종 중 하나라도) 집계.
감지 가능성: 1분봉으로 "장중 시가 대비 -3% 터치" 순간을 잡고, 그 뒤 종가까지의
결과 분포를 잰다 — 터치 시 매수 → 종가 매도(비용 0.2% 차감)의 기대값·승률.
(= 아래꼬리가 '완성된 뒤'가 아니라 '만들어지는 중'에 잡을 수 있는가)

  uv run python scripts/daily_tail_study.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from bot_coin.main import TOP_MCAP_ALTS
from minute1_backtest import CACHE_1M, load_1m

UNIVERSE = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})
COST = 0.2


def main():
    sym_days = {"아래꼬리≥3%": set(), "윗꼬리≥3%": set(), "양쪽 다": set(), "등락≥5%": set()}
    cal_days = {k: set() for k in sym_days}
    touch_trades = []          # (ts.date, symbol, 터치→종가 순수익%)
    all_days = set()
    all_last = None

    for sym in UNIVERSE:
        bars = load_1m(sym)
        if len(bars) < 2000:
            continue
        all_last = max(all_last, bars[-1].ts) if all_last else bars[-1].ts
        # 일 단위(자정 경계)로 그룹
        by_day: dict = {}
        for b in bars:
            by_day.setdefault(b.ts.date(), []).append(b)
        for d, day_bars in by_day.items():
            if len(day_bars) < 600:      # 결측 심한 날 제외
                continue
            all_days.add(d)
            o = float(day_bars[0].open)
            c = float(day_bars[-1].close)
            h = max(float(b.high) for b in day_bars)
            low = min(float(b.low) for b in day_bars)
            rng = (h - low) / o * 100
            lower = (min(o, c) - low) / o * 100
            upper = (h - max(o, c)) / o * 100
            if rng < 5:
                continue
            sym_days["등락≥5%"].add((sym, d)); cal_days["등락≥5%"].add(d)
            if lower >= 3:
                sym_days["아래꼬리≥3%"].add((sym, d)); cal_days["아래꼬리≥3%"].add(d)
            if upper >= 3:
                sym_days["윗꼬리≥3%"].add((sym, d)); cal_days["윗꼬리≥3%"].add(d)
            if lower >= 3 and upper >= 3:
                sym_days["양쪽 다"].add((sym, d)); cal_days["양쪽 다"].add(d)

            # 장중 -3% 터치 → 종가 결과 (터치가로 매수 가정)
            level = o * 0.97
            for b in day_bars:
                if float(b.low) <= level:
                    net = (c / level - 1) * 100 - COST
                    touch_trades.append((d, sym, net))
                    break

    n_days = len(all_days)
    print(f"유니버스 {len(UNIVERSE)}종 × {n_days}일 (유효 심볼-일 표본)\n")
    print("== 빈도 (등락 5% 이상인 날 기준) ==")
    for k in ("등락≥5%", "아래꼬리≥3%", "윗꼬리≥3%", "양쪽 다"):
        sd, cd = len(sym_days[k]), len(cal_days[k])
        print(f"  {k:<10}: 심볼-일 {sd:,}건 | 달력일 {cd}일 ({cd/n_days*100:.0f}%) "
              f"| 주당 {cd/n_days*7:.1f}일꼴")

    print("\n== '장중 시가 대비 -3% 터치' → 종가까지 (터치가 매수, 비용 차감) ==")
    boundary = all_last.date() - timedelta(days=365)
    for label, trades in (("전체", touch_trades),
                          ("상승년", [t for t in touch_trades if t[0] < boundary]),
                          ("하락년", [t for t in touch_trades if t[0] >= boundary])):
        vals = [v for _, _, v in trades]
        if not vals:
            continue
        pos = sum(1 for v in vals if v > 0) / len(vals) * 100
        print(f"  {label}: n={len(vals):,} | 기대값 {statistics.mean(vals):+.3f}% | "
              f"중앙 {statistics.median(vals):+.2f}% | 승률 {pos:.0f}% | "
              f"최악 {min(vals):+.1f}%")


if __name__ == "__main__":
    main()
