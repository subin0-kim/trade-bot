"""업비트 코인 백테스트 — 타임프레임별 전략 검증.

주식과 다른 비용 모델 (이게 이 실험의 핵심):
  코인: 수수료 0.05%×2 + 슬리피지 0.05%×2 = 왕복 0.20%   (거래세 0%)
  주식: 수수료 0.015%×2 + 거래세 0.18% + 슬리피지 0.05%×2 = 왕복 0.31%
  → 약 35% 저렴. 주식에서 과다거래로 죽은 전략이 코인에선 살아남는지가 관건.

  uv run python scripts/backtest_upbit.py --tf 60m
  uv run python scripts/backtest_upbit.py --tf 15m,60m --coins KRW-BTC,KRW-ETH
  uv run python scripts/backtest_upbit.py --tf 60m --presets connors_rsi2,ma_trend
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from backtest import Backtester, resample
from strategy_kit import build_preset, preset_meta
from trading_core.models import Candle

CACHE_5M = Path("data/cache/upbit/5m")

# 코인 비용 모델
COIN_FEE = Decimal("0.0005")       # 0.05% (업비트 KRW 마켓)
COIN_TAX = Decimal(0)              # 거래세 없음 ★
COIN_SLIPPAGE = Decimal("0.0005")  # 0.05% (주식과 동일 가정 — 보수적)

DEFAULT_PRESETS = [
    "connors_rsi2",      # 주식 60분봉에서 붕괴했던 평균회귀 (핵심 비교 대상)
    "bb_meanrev",
    "ma_trend",
    "macd_trend_mtf",
    "ichimoku_tk",
    "breakout_momo",
]


def load_5m(symbol: str) -> list[Candle]:
    path = CACHE_5M / f"{symbol}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            out.append(Candle(
                ts=datetime.fromisoformat(d["ts"]),
                open=Decimal(d["o"]), high=Decimal(d["h"]),
                low=Decimal(d["l"]), close=Decimal(d["c"]), volume=Decimal(d["v"]),
            ))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return out


def to_timeframe(candles: list[Candle], tf: str) -> list[Candle]:
    if tf == "5m":
        return candles
    return resample(candles, tf)


def run_one(symbol: str, bars: list[Candle], preset: str, tf: str) -> dict | None:
    if len(bars) < 600:
        return None
    # 상위TF 필터가 있는 전략은 코인용으로 D(일봉)를 상위로 사용
    config_meta = preset_meta(preset)
    higher = ["D"] if config_meta["higher_tfs"] else []
    strategy = build_preset(preset)
    if higher:
        # 필터의 tf 파라미터도 함께 치환 (W→D). 안 하면 필터가 데이터를 못 찾아 전량 차단됨
        for f in strategy.filters:
            if hasattr(f, "tf"):
                f.tf = "D"
    bt = Backtester(
        strategy, primary_tf=tf, higher_tfs=higher,
        fee_rate=COIN_FEE, sell_tax_rate=COIN_TAX, slippage_rate=COIN_SLIPPAGE,
        warmup=300, view_window=400,
        quantity_step=Decimal("0.00000001"),  # 코인 소수점 8자리
        min_order_value=Decimal(5000),        # 업비트 최소 주문
    )
    return bt.run(symbol, bars).summary()


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return {
        "n": len(rows),
        "median_return": round(statistics.median(r["total_return_pct"] for r in rows), 2),
        "median_bh": round(statistics.median(r["buy_hold_return_pct"] for r in rows), 2),
        "positive": sum(1 for r in rows if r["total_return_pct"] > 0),
        "beat_bh": sum(1 for r in rows if r["total_return_pct"] > r["buy_hold_return_pct"]),
        "median_win": round(statistics.median(r["win_rate"] for r in rows), 1),
        "median_mdd": round(statistics.median(r["max_drawdown_pct"] for r in rows), 2),
        "trades": sum(r["trades"] for r in rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="60m", help="쉼표 구분 (5m,15m,30m,60m)")
    parser.add_argument("--coins", default=None, help="쉼표 구분 (기본: 캐시 전체)")
    parser.add_argument("--presets", default=None)
    args = parser.parse_args()

    timeframes = [t.strip() for t in args.tf.split(",")]
    presets = ([p.strip() for p in args.presets.split(",")] if args.presets else DEFAULT_PRESETS)
    symbols = ([c.strip() for c in args.coins.split(",")] if args.coins
               else sorted(p.stem for p in CACHE_5M.glob("*.jsonl")))

    data = {s: load_5m(s) for s in symbols}
    data = {s: c for s, c in data.items() if len(c) > 5000}
    if not data:
        raise SystemExit("캐시 없음 — collect_upbit.py 먼저 실행")

    sample = next(iter(data.values()))
    print(f"코인 백테스트: {len(data)}종목, {sample[0].ts.date()} ~ {sample[-1].ts.date()}")
    print(f"비용 모델: 수수료 {COIN_FEE*100}%×2 + 슬리피지 {COIN_SLIPPAGE*100}%×2 "
          f"= 왕복 {(COIN_FEE+COIN_SLIPPAGE)*200}% (거래세 0%)\n")

    for tf in timeframes:
        bars_by_symbol = {s: to_timeframe(c, tf) for s, c in data.items()}
        n_bars = len(next(iter(bars_by_symbol.values())))
        header = (f"{'전략':<18}{'종목':>4}{'중앙수익%':>10}{'중앙B&H%':>10}{'수익종목':>8}"
                  f"{'B&H승':>7}{'승률%':>7}{'MDD%':>7}{'총거래':>7}")
        print(f"━━━ {tf} ({n_bars:,}봉) " + "━" * 40)
        print(header)
        print("-" * len(header))
        for preset in presets:
            rows = []
            for symbol, bars in bars_by_symbol.items():
                try:
                    r = run_one(symbol, bars, preset, tf)
                except Exception as e:
                    print(f"    {symbol} 실패: {type(e).__name__}: {str(e)[:60]}")
                    continue
                if r:
                    rows.append(r)
            a = aggregate(rows)
            if not a:
                continue
            print(f"{preset:<18}{a['n']:>4}{a['median_return']:>10.2f}{a['median_bh']:>10.2f}"
                  f"{a['positive']:>6}/{a['n']:<2}{a['beat_bh']:>5}/{a['n']:<2}"
                  f"{a['median_win']:>7.1f}{a['median_mdd']:>7.2f}{a['trades']:>7}")
        print()


if __name__ == "__main__":
    main()
