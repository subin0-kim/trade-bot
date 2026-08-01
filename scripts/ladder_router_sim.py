"""지정가 사다리 주문 라우터 시뮬 — "주문을 k개만 유지하면 몇 %를 놓치는가".

실물 제약: 업비트 지정가는 KRW 잠금 → 16종×2단 전부에 깔 수 없음.
사용자 제안: 기준가는 15분 경계 종가로 고정, 매 1분마다 각 종목-단의
근접도(현재가 vs 트리거가)를 계산해 가장 가까운 k개에만 주문 유지 (순위 바뀌면 이동).
모델링: t-1분 데이터로 주문 배치 → t분 저가가 트리거 터치 시 체결 (1분 반응 지연).
플래시 급락(1분 내 원거리→관통)은 주문이 없던 종목이면 놓침 — 이게 포착률 손실.

비교: 전량 커버리지(이상) vs 라우터 k=4/8/14 | 사이징 7%×14, 25%×4.

  uv run python scripts/ladder_router_sim.py
"""

from __future__ import annotations

import statistics
import sys
from datetime import timedelta

sys.path.insert(0, "scripts")

from flash_dip_portfolio_sim import simulate
from minute1_backtest import load_1m
from bot_coin.main import TOP_MCAP_ALTS

UNI = sorted(set(TOP_MCAP_ALTS) | {"KRW-ETH"})
DEPTHS = [2.0, 5.0]
TIMEOUT = 240
REF_N = 5           # 기준가 재산정 주기(분) — 챔피언 의미론 (15분 고정은 열화 실측)


def load_all():
    data = {}
    for sym in UNI:
        bars = load_1m(sym)
        if len(bars) < 5000:
            continue
        data[sym] = {
            "bars": bars,
            "close": [float(b.close) for b in bars],
            "high": [float(b.high) for b in bars],
            "low": [float(b.low) for b in bars],
            "idx": {b.ts: i for i, b in enumerate(bars)},
        }
    return data


def run_events(data, k_orders):
    """k_orders=None → 전량 커버리지. 아니면 매분 근접도 상위 k개만 주문."""
    all_ts = sorted({b.ts for d in data.values() for b in d["bars"]})
    # 상태: (sym, X) → {'ref':기준가, 'pos':청산예정 정보 or None}
    state = {(s, X): {"pos_until": -1} for s in data for X in DEPTHS}
    ref = {}          # (sym, X) → level (15분 경계마다 갱신)
    events = []
    day_close = {}
    for sym, d in data.items():
        dc = day_close.setdefault(sym, {})
        for b in d["bars"]:
            dc[b.ts.date()] = float(b.close)

    active_orders = set()
    for t_i, ts in enumerate(all_ts):
        # REF_N분 경계: 기준가 갱신 (직전 완성 1분봉 종가 기준 -X%)
        if ts.minute % REF_N == 0:
            for sym, d in data.items():
                i = d["idx"].get(ts)
                if i is None or i == 0:
                    continue
                for X in DEPTHS:
                    ref[(sym, X)] = d["close"][i - 1] * (1 - X / 100)
        # 주문 배치 (t-1 데이터 기준 근접도)
        if k_orders is not None:
            ranks = []
            for (sym, X), lv in ref.items():
                d = data[sym]
                i = d["idx"].get(ts)
                if i is None or i < 1 or lv is None:
                    continue
                st = state[(sym, X)]
                if i <= st["pos_until"]:
                    continue
                dist = d["close"][i - 1] / lv - 1     # 음수면 이미 관통
                ranks.append((dist, sym, X))
            ranks.sort()
            active_orders = {(s, X) for _, s, X in ranks[:k_orders]}
        # 체결 판정
        for sym, d in data.items():
            i = d["idx"].get(ts)
            if i is None or i < 1 or i >= len(d["bars"]) - TIMEOUT - 2:
                continue
            for X in DEPTHS:
                lv = ref.get((sym, X))
                if lv is None:
                    continue
                st = state[(sym, X)]
                if i <= st["pos_until"]:
                    continue
                if k_orders is not None and (sym, X) not in active_orders:
                    continue
                if d["low"][i] <= lv:
                    entry = min(lv, d["close"][i - 1])   # 관통 배치 시 직전가가 더 낮으면 그 가격
                    tgt = entry * (1 + 0.7 * X / 100)
                    end = min(i + TIMEOUT, len(d["bars"]) - 1)
                    px, off = d["close"][end], end - i
                    for j in range(i + 1, end + 1):
                        if d["high"][j] >= tgt:
                            px, off = tgt, j - i
                            break
                    events.append({"symbol": f"{sym}#{X}", "ts": ts, "entry": entry,
                                   "exit_ts": d["bars"][i + off].ts, "exit": px})
                    st["pos_until"] = i + off
    tagged = {}
    for key in {e["symbol"] for e in events}:
        tagged[key] = day_close[key.split("#")[0]]
    events.sort(key=lambda e: e["ts"])
    return events, tagged, all_ts[-1]


def main():
    data = load_all()
    base_events = None
    for k in (None, 14, 8, 4):
        events, dc, last = run_events(data, k)
        end = last.date()
        boundary = end - timedelta(days=365)
        tag = "전량(이상)" if k is None else f"라우터 k={k}"
        if base_events is None:
            base_events = len(events)
        cap = len(events) / base_events * 100
        line = [f"{tag:<10} 체결 {len(events):>5}건 (포착률 {cap:.0f}%)"]
        for frac, mx in ((0.07, 14), (0.25, 4)):
            out = []
            for label, s, e in (("상승년", boundary - timedelta(days=365), boundary),
                                ("하락년", boundary + timedelta(days=1), end)):
                r = simulate(events, dc, s, e, frac, mx)
                out.append(f"{label} {r['ret']:+6.1f}% (MDD {r['mdd']:4.1f})")
            line.append(f"[{frac*100:.0f}%×{mx}] " + " / ".join(out))
        print(" | ".join(line), flush=True)


if __name__ == "__main__":
    main()
