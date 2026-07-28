"""종가 손절 vs 장중 손절 — 5분봉 침투 재생 검증.

배경: 백테스트·코인봇 모두 손절을 '완성된 240분봉 종가'로 판정한다 (알려진 낙관 편향).
이 스크립트는 앙상블+breakout_momo 백테스트의 실제 거래를 하나씩 5분봉으로 재생해,
"만약 장중(5분 저가)에 손절선 터치 시 즉시 체결했다면" 결과가 어떻게 달라지는지 잰다.

손절선 (breakout_momo, 봉 시작 시점에 확정된 정보만 사용):
  - 고정: 진입가 × 0.96
  - ATR 트레일링: (직전 완성봉까지의 최고 종가) − 2.5 × ATR14(직전 완성봉까지)
  둘 중 높은 값. 진입봉에서는 고정 손절만 활성.

한계: 거래별 독립 재생 — 조기 청산으로 풀린 슬롯의 재진입 효과는 반영 안 됨.

  uv run python scripts/intrabar_stop_check.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from backtest_upbit import COIN_FEE, COIN_SLIPPAGE, COIN_TAX, load_5m, to_timeframe
from crypto_ensemble_verify import CACHE_5M, ensemble_flags
from crypto_regime import to_daily
from indicators import atr
from strategy_kit import RegimeMappedStrategy, build_preset

STOP_PCT = 4.0
TRAIL_PERIOD, TRAIL_MULT = 14, 2.5
SLIP = 0.0005
FEE = 0.0005
BAR_MIN = 240


def replay_trade(trade, bars240, bars5):
    """한 거래를 5분봉으로 재생. (장중손절 pnl_pct, 바뀌었나, 휩쏘 봉 수) 반환."""
    idx = {b.ts: i for i, b in enumerate(bars240)}
    i0 = idx.get(trade.entry_ts)
    i1 = idx.get(trade.exit_ts) if trade.exit_ts else None
    if i0 is None or i1 is None:
        return None
    entry = float(trade.entry_price)
    stop_fixed = entry * (1 - STOP_PCT / 100)

    # 5분봉을 240분 구간별로 묶는다
    by_period: dict = {}
    for b in bars5:
        anchor = b.ts.replace(minute=0, second=0, microsecond=0)
        anchor = anchor.replace(hour=(anchor.hour // 4) * 4)
        by_period.setdefault(anchor, []).append(b)

    highest = None  # 직전 완성봉까지의 최고 종가 (진입봉 완성 후부터)
    pierce_recover = 0
    for j in range(i0, i1 + 1):
        bar = bars240[j]
        stop = stop_fixed
        if highest is not None:
            a = atr(bars240[: j], TRAIL_PERIOD)  # 직전 완성봉까지
            if a and a[-1] is not None:
                stop = max(stop, highest - a[-1] * TRAIL_MULT)
        fills = sorted(by_period.get(bar.ts, []), key=lambda b: b.ts)
        hit = None
        for f in fills:
            # 진입봉에서는 시가(체결) 이후부터만 유효
            if j == i0 and f.ts < trade.entry_ts:
                continue
            if float(f.low) <= stop:
                hit = stop
                break
        if hit is not None:
            # 실제(종가 방식)에서는 이 봉에서 안 나갔는데 장중이면 나감
            pnl = ((hit * (1 - SLIP) * (1 - FEE)) / (entry * (1 + FEE)) - 1) * 100
            actually_exited_here = (j == i1)
            return pnl, not actually_exited_here or pnl != trade.pnl_pct, pierce_recover
        # 이 봉에서 장중 침투 없이 생존 — 종가 기준 상태 갱신
        if float(bar.low) <= stop:
            pierce_recover += 1  # (5m 누락으로 240m 저가만 침투한 경우)
        highest = float(bar.close) if highest is None else max(highest, float(bar.close))
    return trade.pnl_pct, False, pierce_recover


def main():
    btc_daily = to_daily(load_5m("KRW-BTC"))
    ens = ensemble_flags(btc_daily)
    states = {d: ("bull" if f else "off") for d, f in ens.items()}

    symbols = sorted(p.stem for p in CACHE_5M.glob("*.jsonl"))
    raw5 = {s: load_5m(s) for s in symbols}
    data = {s: to_timeframe(b, "240m") for s, b in raw5.items()}
    data = {s: b for s, b in data.items() if len(b) > 600}

    strat = RegimeMappedStrategy("ens", states, {"bull": build_preset("breakout_momo"), "off": None})
    pbt = PortfolioBacktester(
        strat, max_positions=8, warmup=300, view_window=400,
        fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
        initial_cash=Decimal(50_000_000),
    )
    result = pbt.run(data)
    closed = [t for t in result.trades if t.exit_ts is not None]
    print(f"대상 거래 {len(closed)}건 (앙상블+breakout_momo, 종가 손절 방식)\n")

    changed, whipsaw, protected, same = [], [], [], []
    for t in closed:
        r = replay_trade(t, data[t.symbol], raw5[t.symbol])
        if r is None:
            continue
        pnl_intra, was_changed, _ = r
        if not was_changed:
            same.append(t)
            continue
        diff = pnl_intra - t.pnl_pct
        changed.append((t, pnl_intra, diff))
        (whipsaw if diff < 0 else protected).append((t, pnl_intra, diff))

    n = len(changed) + len(same)
    print(f"장중 손절이었다면 결과가 바뀌는 거래: {len(changed)}/{n}건 ({len(changed)/n*100:.0f}%)")
    print(f"  휩쏘 (장중 손절이 더 나쁨 — 종가엔 회복): {len(whipsaw)}건, "
          f"평균 {sum(d for _, _, d in whipsaw)/max(len(whipsaw),1):+.2f}%p")
    print(f"  보호 (장중 손절이 더 좋음 — 더 빠지기 전 탈출): {len(protected)}건, "
          f"평균 {sum(d for _, _, d in protected)/max(len(protected),1):+.2f}%p")

    pnl_close = [t.pnl_pct for t in closed]
    pnl_intra = {id(t): t.pnl_pct for t in closed}
    for t, pi, _ in changed:
        pnl_intra[id(t)] = pi
    pnl_intra = list(pnl_intra.values())

    def agg(pnls, label):
        wins = sum(1 for p in pnls if p > 0)
        cum = 1.0
        for p in pnls:
            cum *= 1 + (p / 100) / 8  # 슬롯 비중 1/8 근사 복리
        print(f"{label:<14} 평균 {sum(pnls)/len(pnls):+.3f}%/건 | 승률 {wins/len(pnls)*100:.1f}% | "
              f"포트폴리오 근사 {(cum-1)*100:+.1f}%")

    print()
    agg(pnl_close, "종가 손절(현재)")
    agg(pnl_intra, "장중 손절")


if __name__ == "__main__":
    main()
