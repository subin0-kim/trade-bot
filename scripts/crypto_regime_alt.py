"""코인 레짐 — 대안 입력 탐색.

MA 기반 판별이 코인에서 역전 작동([[crypto-regime-findings]])하므로,
다른 입력이 알트 수익률을 더 잘 분리하는지 비교한다.

평가 기준: 레짐별 알트 '다음날' 수익률의 분리도
  - 방향 정합: bull(또는 risk-on) 평균 > bear(risk-off) 평균
  - 분리 폭: 두 그룹 평균의 차이 (클수록 유용)
  ※ 판별은 t시점 정보만 사용, 수익률은 t+1 → look-ahead 없음

  uv run python scripts/crypto_regime_alt.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "scripts")

from crypto_regime import load_5m, to_daily
from indicators import atr, closes, roc, sma

CACHE_5M = Path("data/cache/upbit/5m")


def build_alt_returns() -> dict[date, list[float]]:
    """일자 → 알트 종목들의 그날 수익률(%)."""
    by_date: dict[date, list[float]] = {}
    for path in sorted(CACHE_5M.glob("*.jsonl")):
        daily = to_daily(load_5m(path.stem))
        if len(daily) < 100:
            continue
        for i in range(1, len(daily)):
            prev_close, cur_close = daily[i - 1].close, daily[i].close
            if prev_close <= 0:
                continue
            by_date.setdefault(daily[i].ts.date(), []).append(
                float(cur_close / prev_close - 1) * 100
            )
    return by_date


# --------------------------------------------------------------- 레짐 정의들
def regime_ma(btc, i) -> str:
    xs = closes(btc[: i + 1])
    s, m, l = sma(xs, 20), sma(xs, 60), sma(xs, 120)
    if l[-1] is None or s[-1] is None or m[-1] is None:
        return "neutral"
    if xs[-1] > l[-1] and s[-1] > m[-1]:
        return "risk_on"
    if xs[-1] < l[-1] and s[-1] < m[-1]:
        return "risk_off"
    return "neutral"


def regime_momentum(btc, i, period: int = 20) -> str:
    xs = closes(btc[: i + 1])
    r = roc(xs, period)
    if r[-1] is None:
        return "neutral"
    if r[-1] > 5:
        return "risk_on"
    if r[-1] < -5:
        return "risk_off"
    return "neutral"


def regime_volatility(btc, i, period: int = 14, lookback: int = 120) -> str:
    """변동성 레짐 — ATR%가 과거 분포의 하위/상위이면 저변동/고변동.

    가설: 코인은 '고변동 = 하락 위험'이라 저변동 구간이 매수에 유리.
    """
    window = btc[: i + 1]
    a = atr(window, period)
    if a[-1] is None:
        return "neutral"
    price = float(window[-1].close)
    if price <= 0:
        return "neutral"
    cur = a[-1] / price * 100
    hist = [v / float(window[j].close) * 100
            for j, v in enumerate(a[-lookback:], start=max(0, len(window) - lookback))
            if v is not None and float(window[j].close) > 0]
    if len(hist) < 30:
        return "neutral"
    lo, hi = statistics.quantiles(hist, n=4)[0], statistics.quantiles(hist, n=4)[2]
    if cur <= lo:
        return "risk_on"      # 저변동 = 매수 우호 가설
    if cur >= hi:
        return "risk_off"     # 고변동 = 위험
    return "neutral"


def regime_ma_fast(btc, i) -> str:
    """코인 스윕에서 방향 분리에 성공한 단기 조합 (MA10/30/60)."""
    xs = closes(btc[: i + 1])
    s, m, l = sma(xs, 10), sma(xs, 30), sma(xs, 60)
    if l[-1] is None or s[-1] is None or m[-1] is None:
        return "neutral"
    if xs[-1] > l[-1] and s[-1] > m[-1]:
        return "risk_on"
    if xs[-1] < l[-1] and s[-1] < m[-1]:
        return "risk_off"
    return "neutral"


DEFINITIONS = {
    "MA20/60/120 (주식 기본)": regime_ma,
    "MA10/30/60 (코인 스윕)": regime_ma_fast,
    "모멘텀 ROC20 ±5%": regime_momentum,
    "변동성 ATR% 사분위": regime_volatility,
}


def main():
    btc = to_daily(load_5m("KRW-BTC"))
    alt_returns = build_alt_returns()
    print(f"BTC 일봉 {len(btc)}개, 알트 수익률 {len(alt_returns)}일치\n")

    header = f"{'레짐 정의':<24}{'risk_on':>10}{'risk_off':>10}{'중립':>9}{'분리폭':>9}  판정"
    print(header)
    print("-" * len(header))

    for label, fn in DEFINITIONS.items():
        buckets: dict[str, list[float]] = {"risk_on": [], "risk_off": [], "neutral": []}
        for i in range(120, len(btc) - 1):
            r = fn(btc, i)
            # t시점 판별 → t+1 수익률 (look-ahead 없음)
            nxt = btc[i + 1].ts.date()
            buckets[r].extend(alt_returns.get(nxt, []))
        stats = {k: (sum(v) / len(v) if v else 0.0) for k, v in buckets.items()}
        spread = stats["risk_on"] - stats["risk_off"]
        verdict = "정상" if spread > 0 else "역전!"
        if spread > 0.15:
            verdict = "정상 (분리 뚜렷)"
        print(f"{label:<24}{stats['risk_on']:>+10.3f}{stats['risk_off']:>+10.3f}"
              f"{stats['neutral']:>+9.3f}{spread:>+9.3f}  {verdict}")

    print("\n(수치 = 알트 26종목 다음날 일평균 수익률 %. 분리폭 = risk_on - risk_off)")


if __name__ == "__main__":
    main()
