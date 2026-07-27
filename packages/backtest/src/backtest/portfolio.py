"""포트폴리오 백테스터 — 하나의 전략을 유니버스 전체에 공유 자본으로 운용.

단일종목 엔진과의 차이:
- 자본 풀 하나, 동시 보유 최대 max_positions
- 매 봉마다 전 종목 평가 → 청산 먼저, 진입은 신호 강도순으로 남은 슬롯만
- 종목당 배분 상한 = 자산/max_positions (분산 강제)
동일한 현실성 규칙: 판단은 종가, 체결은 다음 봉 시가+슬리피지, 상위TF 완성봉만.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from strategy_kit import CompositeStrategy, MarketView, OpenPosition
from trading_core.models import Candle, OrderSide

from .engine import Trade
from .timeframe import resample_progressive


@dataclass
class PortfolioResult:
    strategy: str
    initial_cash: Decimal
    final_equity: Decimal
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[datetime, Decimal]] = field(default_factory=list)
    bench_return_pct: float = 0.0     # 동일가중 바이앤홀드
    bench_mdd_pct: float = 0.0
    exposure_pct: float = 0.0         # 자산 대비 포지션 총비중의 기간 평균

    def summary(self) -> dict:
        closed = [t for t in self.trades if t.exit_ts is not None]
        wins = [t for t in closed if t.pnl > 0]
        gross_profit = sum((t.pnl for t in wins), Decimal(0))
        gross_loss = -sum((t.pnl for t in closed if t.pnl <= 0), Decimal(0))

        peak = self.initial_cash
        mdd = 0.0
        for _, eq in self.equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                mdd = max(mdd, float((peak - eq) / peak * 100))

        return {
            "strategy": self.strategy,
            "trades": len(closed),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "total_return_pct": round(
                float((self.final_equity - self.initial_cash) / self.initial_cash * 100), 2
            ),
            "bench_return_pct": round(self.bench_return_pct, 2),
            "bench_mdd_pct": round(self.bench_mdd_pct, 2),
            "max_drawdown_pct": round(mdd, 2),
            "exposure_pct": round(self.exposure_pct, 1),
            "profit_factor": round(float(gross_profit / gross_loss), 2) if gross_loss > 0 else None,
        }


@dataclass
class _SymbolState:
    candles: list[Candle]
    higher: dict[str, tuple[list[Candle], list[int]]]
    idx_by_date: dict[date, int]
    position: OpenPosition | None = None
    trade: Trade | None = None
    pending: dict | None = None


class PortfolioBacktester:
    def __init__(
        self,
        strategy: CompositeStrategy,
        *,
        primary_tf: str = "D",
        higher_tfs: list[str] | None = None,
        initial_cash: Decimal = Decimal(50_000_000),
        max_positions: int = 8,
        fee_rate: Decimal = Decimal("0.00015"),
        sell_tax_rate: Decimal = Decimal("0.0018"),
        slippage_rate: Decimal = Decimal("0.0005"),
        warmup: int = 130,
        view_window: int = 320,
    ):
        self.strategy = strategy
        self.primary_tf = primary_tf
        self.higher_tfs = higher_tfs or []
        self.initial_cash = initial_cash
        self.max_positions = max_positions
        self.fee_rate = fee_rate
        self.sell_tax_rate = sell_tax_rate
        self.slippage_rate = slippage_rate
        self.warmup = warmup
        self.view_window = view_window

    def run(self, data: dict[str, list[Candle]]) -> PortfolioResult:
        states: dict[str, _SymbolState] = {}
        for symbol, candles in data.items():
            if len(candles) <= self.warmup + 1:
                continue
            states[symbol] = _SymbolState(
                candles=candles,
                higher={tf: resample_progressive(candles, tf) for tf in self.higher_tfs},
                idx_by_date={c.ts.date(): i for i, c in enumerate(candles)},
            )

        all_dates = sorted({c.ts.date() for st in states.values() for c in st.candles})
        result = PortfolioResult(
            strategy=self.strategy.name,
            initial_cash=self.initial_cash,
            final_equity=self.initial_cash,
        )
        cash = self.initial_cash
        weight_samples: list[float] = []

        def equity_at(d: date) -> Decimal:
            total = cash
            for st in states.values():
                if st.position is None:
                    continue
                i = st.idx_by_date.get(d)
                price = st.candles[i].close if i is not None else st.candles[-1].close
                total += st.position.quantity * price
            return total

        for d in all_dates:
            # --- 1) 보류 주문 체결 (오늘 봉 시가) ---
            for symbol, st in states.items():
                if st.pending is None:
                    continue
                i = st.idx_by_date.get(d)
                if i is None:
                    continue  # 오늘 이 종목 휴장/거래정지 → 다음 거래일에 체결
                bar = st.candles[i]
                pending, st.pending = st.pending, None
                if pending["action"] == "enter" and st.position is None:
                    fill = bar.open * (1 + self.slippage_rate)
                    # 분산 강제: 종목당 자산/max_positions 상한
                    cap = equity_at(d) / self.max_positions
                    qty = min(pending["quantity"], Decimal(int(cap / fill)))
                    cost = fill * qty
                    fee = cost * self.fee_rate
                    if qty >= 1 and cost + fee <= cash:
                        cash -= cost + fee
                        st.position = OpenPosition(
                            side=OrderSide.BUY, quantity=qty,
                            entry_price=fill, entry_ts=bar.ts, highest_close=bar.close,
                        )
                        st.trade = Trade(
                            symbol=symbol, entry_ts=bar.ts, entry_price=fill,
                            quantity=qty, entry_reason=pending["reason"],
                        )
                        result.trades.append(st.trade)
                elif pending["action"] == "exit" and st.position is not None:
                    fill = bar.open * (1 - self.slippage_rate)
                    proceeds = fill * st.position.quantity
                    fee = proceeds * self.fee_rate
                    tax = proceeds * self.sell_tax_rate
                    cash += proceeds - fee - tax
                    entry_cost = st.position.entry_price * st.position.quantity
                    st.trade.exit_ts = bar.ts
                    st.trade.exit_price = fill
                    st.trade.exit_reason = pending["reason"]
                    st.trade.bars_held = st.position.bars_held
                    st.trade.pnl = (proceeds - fee - tax) - entry_cost * (1 + self.fee_rate)
                    st.trade.pnl_pct = float(st.trade.pnl / entry_cost * 100)
                    st.position = None
                    st.trade = None

            # --- 2) 포지션 갱신 + 판단 ---
            n_open = sum(1 for st in states.values() if st.position is not None)
            n_pending_enter = 0
            candidates: list[tuple[float, str, dict]] = []

            for symbol, st in states.items():
                i = st.idx_by_date.get(d)
                if i is None or i < self.warmup:
                    continue
                bar = st.candles[i]
                if st.position is not None:
                    st.position.update_on_bar(bar)

                view = MarketView(
                    symbol=symbol,
                    primary_tf=self.primary_tf,
                    candles={
                        self.primary_tf: st.candles[max(0, i + 1 - self.view_window) : i + 1],
                        **{
                            tf: bars[max(0, counts[i] - self.view_window) : counts[i]]
                            for tf, (bars, counts) in st.higher.items()
                        },
                    },
                )
                decision = self.strategy.evaluate(view, st.position, equity_at(d))
                if decision.action == "exit" and st.position is not None:
                    st.pending = {"action": "exit", "reason": " / ".join(decision.reasons)}
                elif decision.action == "enter" and st.position is None:
                    candidates.append((
                        decision.score,
                        symbol,
                        {"action": "enter", "quantity": decision.quantity,
                         "reason": " / ".join(decision.reasons)},
                    ))

            # --- 3) 슬롯 남는 만큼만, 신호 품질 순으로 진입 예약 ---
            # 점수 의미는 전략별로 다르나 한 시점에 한 전략만 가동되므로 비교 가능
            # (평균회귀=과매도 깊이, 추세·돌파=모멘텀 강도). 동점은 심볼코드 순으로 결정적 처리.
            candidates.sort(key=lambda c: (-c[0], c[1]))
            slots = self.max_positions - n_open - n_pending_enter
            for _, symbol, pending in candidates[: max(slots, 0)]:
                states[symbol].pending = pending

            eq = equity_at(d)
            result.equity_curve.append((datetime.combine(d, datetime.min.time()), eq))
            if eq > 0:
                weight_samples.append(float((eq - cash) / eq * 100))

        result.final_equity = equity_at(all_dates[-1])
        result.exposure_pct = (
            sum(weight_samples) / len(weight_samples) if weight_samples else 0.0
        )

        # 벤치마크: 동일가중 바이앤홀드 (각 종목 워밍업 직후 시가 매수, 기간 끝까지)
        bench_rets, bench_curves = [], []
        for st in states.values():
            entry = float(st.candles[self.warmup].open)
            bench_rets.append((float(st.candles[-1].close) / entry - 1) * 100)
            bench_curves.append(
                {c.ts.date(): float(c.close) / entry for c in st.candles[self.warmup:]}
            )
        if bench_rets:
            result.bench_return_pct = sum(bench_rets) / len(bench_rets)
            # 동일가중 곡선의 MDD
            peak, mdd = 0.0, 0.0
            for d in all_dates:
                vals = [curve[d] for curve in bench_curves if d in curve]
                if not vals:
                    continue
                level = sum(vals) / len(vals)
                peak = max(peak, level)
                mdd = max(mdd, (peak - level) / peak * 100)
            result.bench_mdd_pct = mdd
        return result
