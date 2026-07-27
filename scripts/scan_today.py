"""오늘의 매수 후보 스캔 — 검증된 구성을 '지금' 돌리면 뭘 사는가.

백테스트와 동일한 판단 구조:
  1. 직전 완성봉(전 거래일 종가)까지의 데이터로 판단
  2. 레짐 판별 (KOSPI) → 활성 전략 결정
  3. 미국장 쇼크일 필터 (나스닥 야간 |수익률| ≥ 2% → 오늘 진입 금지)
  4. 활성 전략으로 유니버스 전 종목 진입 신호 스캔

  uv run python scripts/scan_today.py            # 캐시 데이터 기준
  uv run python scripts/scan_today.py --refresh  # 최신 데이터 재수집
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, "scripts")

from regime import Regime, RegimeClassifier
from regime_eval import fetch_index_daily
from strategy_kit import MarketView, build_preset, preset_meta
from us_lead_analysis import build_us_overnight_returns, fetch_us_index
from universe_backtest import UNIVERSE, fetch_daily

REGIME_MAPPING = {
    Regime.BEAR: None,
    Regime.SIDEWAYS: "connors_rsi2",
    Regime.BULL: "macd_trend_mtf",
}
US_SHOCK_PCT = 2.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    today = date.today()
    print(f"=== 오늘의 스캔 ({today}) ===\n")

    # --- 1. 레짐 판별 (오늘 진행 중인 봉은 제외 — 완성봉만) ---
    kospi = fetch_index_daily(refresh=args.refresh)
    kospi_done = [c for c in kospi if c.ts.date() < today]
    classifier = RegimeClassifier()
    series = classifier.classify_series(kospi_done)
    last_day = kospi_done[-1].ts.date()
    regime = series[last_day]
    print(f"[레짐] 기준일 {last_day} (KOSPI {kospi_done[-1].close:,}) → **{regime.value.upper()}**")

    preset_name = REGIME_MAPPING[regime]
    if preset_name is None:
        print("→ 하락 레짐: 오늘은 신규 매수 없음 (현금 유지)")
        return
    print(f"→ 활성 전략: {preset_name}")

    # --- 2. 미국장 쇼크 필터 ---
    us = fetch_us_index("COMP", refresh=args.refresh)
    us_returns = build_us_overnight_returns(us)
    recent = sorted(d for d in us_returns if d < today)
    us_day = recent[-1]
    us_ret = us_returns[us_day]
    print(f"[US 필터] 나스닥 {us_day} 야간 수익률 {us_ret:+.2f}%", end=" ")
    if abs(us_ret) >= US_SHOCK_PCT:
        print(f"→ **쇼크일 (|{us_ret:.1f}|≥{US_SHOCK_PCT}%)** — 오늘 신규 진입 차단")
        return
    print("→ 정상 (진입 허용)")

    # --- 3. 유니버스 스캔 ---
    strategy = build_preset(preset_name)
    meta = preset_meta(preset_name)
    equity = Decimal(10_000_000)  # 사이징 표시는 모의계좌 기준

    print(f"\n[스캔] {len(UNIVERSE)}종목 × {strategy.name}")
    candidates = []
    for symbol, name in UNIVERSE.items():
        try:
            candles = [c for c in fetch_daily(symbol, refresh=args.refresh) if c.ts.date() < today]
        except Exception as e:
            print(f"  {symbol} {name}: 데이터 오류 — {e}")
            continue
        if len(candles) < 260:
            continue
        view_candles = {"D": candles[-320:]}
        for tf in meta["higher_tfs"]:
            from backtest import resample
            # 라이브 뷰: 마지막(진행 중일 수 있는) 상위 봉 제외 = 완성봉만
            bars = resample(candles, tf)
            view_candles[tf] = bars[:-1]
        view = MarketView(symbol=symbol, primary_tf="D", candles=view_candles)
        decision = strategy.evaluate(view, None, equity)
        if decision.action == "enter":
            candidates.append((symbol, name, decision))

    if not candidates:
        print("\n→ 오늘 매수 신호 없음 (레짐·필터는 통과했으나 진입 조건 충족 종목 없음)")
        return

    print(f"\n→ 매수 후보 {len(candidates)}종목 (체결 가정: 오늘 시가):\n")
    for symbol, name, decision in candidates:
        print(f"  ● {symbol} {name} — {decision.quantity}주 (1천만원 계좌 기준)")
        for reason in decision.reasons:
            print(f"      {reason}")


if __name__ == "__main__":
    main()
