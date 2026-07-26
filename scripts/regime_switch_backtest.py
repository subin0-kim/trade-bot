"""레짐 스위칭 포트폴리오 백테스트 (사후 라벨 = 상한선 측정).

스케줄: 하락장 → 현금 / 횡보·회복 → 평균회귀 / 상승장 → 모멘텀
사후 라벨을 쓰므로 '실시간으로 이만큼 번다'가 아니라
'레짐 판별이 완벽하다면 이 구조로 얼마까지 가능한가'를 재는 것.

  uv run python scripts/regime_switch_backtest.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "scripts")

from backtest import PortfolioBacktester
from strategy_kit import ScheduledStrategy, build_preset
from universe_backtest import SEGMENTS, UNIVERSE, WARMUP, fetch_daily

# (레짐 이름 → 전략 프리셋) 매핑. None = 현금
VARIANTS: dict[str, dict[str, str | None]] = {
    "switch_bb_breakout": {"하락장": None, "횡보·회복": "bb_meanrev", "상승장": "breakout_momo"},
    "switch_bb_macd": {"하락장": None, "횡보·회복": "bb_meanrev", "상승장": "macd_trend_mtf"},
    "switch_cash_only_bear": {"하락장": None, "횡보·회복": "breakout_momo", "상승장": "breakout_momo"},
}


def build_scheduled(name: str, mapping: dict[str, str | None]) -> tuple[ScheduledStrategy, list[str]]:
    schedule = []
    higher_tfs: set[str] = set()
    for seg_name, start, end in SEGMENTS:
        preset = mapping[seg_name]
        if preset is None:
            schedule.append((start, end, None))
        else:
            from strategy_kit import preset_meta
            schedule.append((start, end, build_preset(preset)))
            higher_tfs.update(preset_meta(preset)["higher_tfs"])
    return ScheduledStrategy(name, schedule), sorted(higher_tfs)


def main():
    data = {}
    for symbol in UNIVERSE:
        try:
            candles = fetch_daily(symbol)
            if len(candles) > WARMUP + 100:
                data[symbol] = candles
        except Exception:
            continue
    if not data:
        raise SystemExit("캐시 없음 — 먼저 universe_backtest.py를 실행하세요")

    print(f"레짐 스위칭 백테스트: {len(data)}종목, 최대 8포지션 (사후 라벨 = 상한선)\n")
    header = (f"{'변형':<22}{'거래':>5}{'승률%':>7}{'수익%':>8}{'벤치%':>8}"
              f"{'MDD%':>7}{'벤치MDD%':>9}{'노출%':>7}{'PF':>6}")
    print(header)
    print("-" * len(header))
    bench = None
    for name, mapping in VARIANTS.items():
        strategy, higher_tfs = build_scheduled(name, mapping)
        pbt = PortfolioBacktester(
            strategy, higher_tfs=higher_tfs, max_positions=8, warmup=WARMUP,
        )
        s = pbt.run(data).summary()
        bench = (s["bench_return_pct"], s["bench_mdd_pct"])
        pf = s["profit_factor"] if s["profit_factor"] is not None else "-"
        print(
            f"{s['strategy']:<22}{s['trades']:>5}{s['win_rate']:>7.1f}"
            f"{s['total_return_pct']:>8.2f}{s['bench_return_pct']:>8.2f}"
            f"{s['max_drawdown_pct']:>7.2f}{s['bench_mdd_pct']:>9.2f}"
            f"{s['exposure_pct']:>7.1f}{pf!s:>6}"
        )
    if bench:
        print(f"\n벤치마크 = 동일가중 B&H 전 기간: {bench[0]:.1f}% (MDD {bench[1]:.1f}%)")
    print("참고(상시 가동): macd_trend_mtf +7.0 / ma_trend -2.2 / breakout_momo -13.5")


if __name__ == "__main__":
    main()
