"""스윙봇 장중 -8% 모니터 vs 종가 백테스트 — 1분봉 실측.

배경: bot-swing-monitor는 장중 30분 간격으로 현재가를 보고 진입가 대비 -8% 이하면
즉시 매도한다. 그러나 챔피언 백테스트(현금/connors_rsi2/macd_trend_mtf + US필터)는
청산을 일봉 종가로만 판정했다 — 실전과 백테스트의 실존 괴리.

방법: 챔피언 백테스트를 재현해 거래를 뽑고, 1분봉 아카이브(37종목 × 242영업일)와
겹치는 거래마다 모니터를 재생한다 — 보유일마다 09:00~15:20 30분 체크포인트의
1분봉 종가가 진입가 × 0.92 이하면 그 가격에 매도(실전 모니터 동작).

코인 실측(`intrabar_stop_check.py`)과 같은 질문, 반대 맥락: 코인은 "장중화가 개악"
이었다. 주식 -8%는 전략 손절보다 느슨한 재해선이라 결과가 다를 수 있다.

  uv run python scripts/swing_monitor_check.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from regime_eval import (REGIME_MAPPING, UNIVERSE, WARMUP, build_us_blocked_dates,
                         fetch_daily, fetch_index_daily)
from regime import Regime, RegimeClassifier
from strategy_kit import EntryBlockedDatesStrategy, RegimeMappedStrategy, build_preset, preset_meta
from strategy_kit.sizing import FixedFractionSizer

MINUTE_DIR = Path("data/cache/minute")
THRESHOLD = -8.0
CHECKPOINTS = [(9, 0), (9, 30), (10, 0), (10, 30), (11, 0), (11, 30), (12, 0),
               (12, 30), (13, 0), (13, 30), (14, 0), (14, 30), (15, 0), (15, 20)]
FEE, TAX, SLIP = 0.00015, 0.0023, 0.0005
MAX_POSITIONS = 4


def load_minute_checkpoints(symbol: str) -> dict[date, list[tuple[datetime, float]]]:
    """종목의 1분봉에서 30분 체크포인트 가격만 추출 (일자별, 시간순)."""
    path = MINUTE_DIR / f"{symbol}.jsonl"
    if not path.exists():
        return {}
    wanted = {f"{h:02d}{m:02d}" for h, m in CHECKPOINTS}
    out: dict[date, list[tuple[datetime, float]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        ts = r["ts"]
        if ts[9:13] not in wanted:
            continue
        dt = datetime.strptime(ts, "%Y%m%dT%H%M%S")
        out.setdefault(dt.date(), []).append((dt, float(r["c"])))
    for d in out:
        out[d].sort()
    return out


def run_champion():
    """챔피언 구성 재현: 현금/connors_rsi2/macd_trend_mtf + US both + 100만/4슬롯."""
    REGIME_MAPPING[Regime.SIDEWAYS.value] = "connors_rsi2"
    data = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
        except Exception:
            continue
    mapping = {r: (build_preset(p) if p else None) for r, p in REGIME_MAPPING.items()}
    for s in mapping.values():
        if s is not None:
            s.sizer = FixedFractionSizer(fraction=0.9 / MAX_POSITIONS)
    higher_tfs: set[str] = set()
    for p in REGIME_MAPPING.values():
        if p:
            higher_tfs.update(preset_meta(p)["higher_tfs"])
    series = RegimeClassifier(confirm_days=5).classify_series(fetch_index_daily())
    strategy = RegimeMappedStrategy("champ", {d: r.value for d, r in series.items()}, mapping)
    strategy = EntryBlockedDatesStrategy("champ+us", strategy,
                                         build_us_blocked_dates("both"), reason="US쇼크")
    pbt = PortfolioBacktester(strategy, higher_tfs=sorted(higher_tfs),
                              initial_cash=Decimal(1_000_000),
                              max_positions=MAX_POSITIONS, warmup=WARMUP)
    return pbt.run(data)


def main():
    result = run_champion()
    closed = [t for t in result.trades if t.exit_ts is not None]
    print(f"챔피언 백테스트 거래 {len(closed)}건 (수익 {result.summary()['total_return_pct']}%)")

    minute_cache: dict[str, dict] = {}
    in_window, changed, whipsaw, protected = [], [], [], []
    for t in closed:
        cps = minute_cache.setdefault(t.symbol, load_minute_checkpoints(t.symbol))
        if not cps:
            continue
        # 보유 기간이 1분봉 커버리지에 완전히 들어오는 거래만
        days = [d for d in sorted(cps) if t.entry_ts.date() <= d < t.exit_ts.date()]
        if not days or days[0] > t.entry_ts.date():
            continue
        in_window.append(t)
        entry = float(t.entry_price)
        stop_price = None
        for d in days:
            for dt, price in cps[d]:
                if (price / entry - 1) * 100 <= THRESHOLD:
                    stop_price = price
                    break
            if stop_price is not None:
                break
        if stop_price is None:
            continue
        pnl_intra = ((stop_price * (1 - SLIP) * (1 - FEE - TAX)) / (entry * (1 + FEE)) - 1) * 100
        diff = pnl_intra - t.pnl_pct
        changed.append((t, pnl_intra, diff))
        (whipsaw if diff < 0 else protected).append((t, pnl_intra, diff))

    n = len(in_window)
    print(f"1분봉 커버리지 내 거래: {n}건 (2025-07-28 ~ 2026-07-24)")
    if n == 0:
        return
    print(f"\n장중 -8% 모니터가 발동했을 거래: {len(changed)}/{n}건 ({len(changed)/n*100:.0f}%)")
    print(f"  휩쏘 (모니터가 더 나쁨 — 종가/전략청산이 나았음): {len(whipsaw)}건, "
          f"평균 {sum(d for _, _, d in whipsaw)/max(len(whipsaw),1):+.2f}%p")
    print(f"  보호 (모니터가 더 좋음 — 추가 하락 회피): {len(protected)}건, "
          f"평균 {sum(d for _, _, d in protected)/max(len(protected),1):+.2f}%p")

    pnl_bt = [t.pnl_pct for t in in_window]
    intra_map = {id(t): t.pnl_pct for t in in_window}
    for t, pi, _ in changed:
        intra_map[id(t)] = pi
    pnl_mon = list(intra_map.values())

    def agg(pnls, label):
        wins = sum(1 for p in pnls if p > 0)
        cum = 1.0
        for p in pnls:
            cum *= 1 + (p / 100) / MAX_POSITIONS
        print(f"{label:<18} 평균 {sum(pnls)/len(pnls):+.3f}%/건 | 승률 {wins/len(pnls)*100:.1f}% | "
              f"포트폴리오 근사 {(cum-1)*100:+.2f}%")

    print()
    agg(pnl_bt, "백테스트(종가만)")
    agg(pnl_mon, "모니터 오버레이")


if __name__ == "__main__":
    main()
