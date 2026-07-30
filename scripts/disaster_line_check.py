"""장중 재해선(-8/-10/-12/-15%) 실측 — 종가 손절은 유지하고 재해선만 추가하면?

배경: 2026-07-28 실측(`intrabar_stop_check.py`)은 '동일 손절선(-4%)의 장중화'를 기각했다
(휩쏘 비용이 보호 이득을 압도, +92%→+25%). 그때 남긴 미검증 항목이 이것이다:
전략 손절(종가 -4% + ATR 트레일)은 그대로 두고, 그보다 훨씬 느슨한 **장중 재해선**
(진입가 대비 -X%, 주식 스윙봇 monitor와 동일 개념)을 별도로 얹으면 어떻게 되는가.

전방 검증에서 KAITO가 240분봉 갭으로 -14%에 청산된 것이 계기 — 재해선이 있었다면
-10%쯤에서 끊었을 것. 문제는 그 재해선이 '회복해서 수익이 될 거래'를 몇 건이나 자르느냐.

체결 가정 2종:
  A. 저가 터치 = 5분봉 저가가 재해선 터치 시 재해선 가격에 즉시 체결 (재해선에 최선 가정)
  B. 30분 점검 = 매 30분 정각의 5분봉 종가가 재해선 이하이면 그 종가에 체결 (실제 monitor 방식)

한계: 거래별 독립 재생 — 조기 청산으로 풀린 슬롯의 재진입 효과는 반영 안 됨.

  uv run python scripts/disaster_line_check.py
"""

from __future__ import annotations

import sys
from bisect import bisect_left
from decimal import Decimal

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from crypto_ensemble_verify import CACHE_5M, ensemble_flags
from crypto_regime import to_daily
from strategy_kit import RegimeMappedStrategy, build_preset

SLIP = 0.0005
FEE = 0.0005
THRESHOLDS = [8.0, 10.0, 12.0, 15.0]


def exit_pnl(entry: float, price: float) -> float:
    """재해선 체결 손익%. 진입·청산 수수료 + 청산 슬리피지 반영."""
    return ((price * (1 - SLIP) * (1 - FEE)) / (entry * (1 + FEE)) - 1) * 100


def replay(trade, bars240_ts, bars5, bars5_ts, threshold_pct: float):
    """한 거래에 재해선을 얹어 재생. (A안 pnl | None, B안 pnl | None) 반환.

    None = 재해선 미발동 (실제 결과 그대로).
    실제 청산은 exit_ts 봉 시가에서 일어나므로, 그 이전 5분봉까지만 본다.
    """
    entry = float(trade.entry_price)
    level = entry * (1 - threshold_pct / 100)

    lo = bisect_left(bars5_ts, trade.entry_ts)
    hi = bisect_left(bars5_ts, trade.exit_ts)  # exit 봉 시가 체결 전까지

    pnl_a = pnl_b = None
    for k in range(lo, hi):
        b = bars5[k]
        if pnl_a is None and float(b.low) <= level:
            pnl_a = exit_pnl(entry, level)
        if pnl_b is None and b.ts.minute % 30 == 25 and float(b.close) <= level:
            # :25/:55에 끝나는 5분봉 종가 = :30/:00 정각 점검 시점의 직전 가격
            pnl_b = exit_pnl(entry, float(b.close))
        if pnl_a is not None and pnl_b is not None:
            break
    return pnl_a, pnl_b


def agg(pnls: list[float], label: str) -> None:
    wins = sum(1 for p in pnls if p > 0)
    cum = 1.0
    for p in pnls:
        cum *= 1 + (p / 100) / 8  # 슬롯 비중 1/8 근사 복리
    print(f"  {label:<26} 평균 {sum(pnls)/len(pnls):+.3f}%/건 | 승률 {wins/len(pnls)*100:.1f}% | "
          f"포트폴리오 근사 {(cum-1)*100:+.1f}%")


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    states = {d: ("bull" if f else "off") for d, f in ens.items()}

    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    raw5 = {s: load_5m(s) for s in symbols}
    data = {s: to_timeframe(b, "240m") for s, b in raw5.items()}
    data = {s: b for s, b in data.items() if len(b) > 600}
    raw5_ts = {s: [b.ts for b in bars] for s, bars in raw5.items()}

    strat = RegimeMappedStrategy("ens", states, {"bull": build_preset("breakout_momo"), "off": None})
    pbt = PortfolioBacktester(
        strat, max_positions=8, warmup=300, view_window=400,
        fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
        initial_cash=Decimal(50_000_000),
    )
    result = pbt.run(data)
    closed = [t for t in result.trades if t.exit_ts is not None]
    bars240_ts = {s: [b.ts for b in bars] for s, bars in data.items()}
    print(f"대상 거래 {len(closed)}건 (앙상블+breakout_momo, 전략 손절은 종가 -4% 유지)\n")

    base = [t.pnl_pct for t in closed]
    agg(base, "재해선 없음 (현재)")
    print()

    for th in THRESHOLDS:
        for variant, tag in ((0, "A 저가터치"), (1, "B 30분점검")):
            fired = []          # (trade, 재해선 pnl, diff)
            pnls = []
            for t in closed:
                r = replay(t, bars240_ts[t.symbol], raw5[t.symbol], raw5_ts[t.symbol], th)
                p = r[variant]
                if p is None:
                    pnls.append(t.pnl_pct)
                else:
                    pnls.append(p)
                    fired.append((t, p, p - t.pnl_pct))
            whip = [d for _, _, d in fired if d < 0]
            prot = [d for _, _, d in fired if d >= 0]
            agg(pnls, f"-{th:.0f}% {tag}")
            print(f"    발동 {len(fired)}건 | 휩쏘 {len(whip)}건 (평균 {sum(whip)/max(len(whip),1):+.2f}%p) | "
                  f"보호 {len(prot)}건 (평균 {sum(prot)/max(len(prot),1):+.2f}%p)")
            if variant == 0 and fired:
                worst = sorted(fired, key=lambda x: x[2])[:3]
                best = sorted(fired, key=lambda x: -x[2])[:3]
                fmt = lambda x: f"{x[0].symbol.replace('KRW-','')} {x[0].entry_ts:%y-%m-%d} ({x[2]:+.1f}%p)"
                print(f"    최악 휩쏘: {', '.join(fmt(x) for x in worst)}")
                print(f"    최대 보호: {', '.join(fmt(x) for x in best)}")
        print()


if __name__ == "__main__":
    main()
