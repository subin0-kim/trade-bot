"""백테스트 엔진.

현실성 규칙:
- 판단은 i번째 봉 '종가 확정 후' → 체결은 i+1번째 봉 '시가' (look-ahead 방지)
- 상위 TF는 완성봉만 노출 (timeframe.resample_progressive)
- 비용: 수수료(왕복) + 매도 거래세 + 슬리피지
- 현물 매수 전용, 심볼당 1포지션
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from strategy_kit import CompositeStrategy, MarketView, OpenPosition
from trading_core.models import Candle, OrderSide

from .timeframe import resample_progressive


@dataclass
class Trade:
    symbol: str
    entry_ts: datetime
    entry_price: Decimal
    quantity: Decimal
    exit_ts: datetime | None = None
    exit_price: Decimal | None = None
    exit_reason: str = ""
    entry_reason: str = ""
    pnl: Decimal = Decimal(0)          # 비용 차감 후
    pnl_pct: float = 0.0
    bars_held: int = 0


@dataclass
class BacktestResult:
    strategy: str
    symbol: str
    initial_cash: Decimal
    final_equity: Decimal
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[datetime, Decimal]] = field(default_factory=list)
    buy_hold_return_pct: float = 0.0     # 동일 기간 바이앤홀드 (벤치마크)
    buy_hold_mdd_pct: float = 0.0
    exposure_pct: float = 0.0            # 포지션 보유 봉 비율
    avg_weight_pct: float = 0.0          # 보유 시 평균 자산 대비 포지션 비중

    @property
    def closed_trades(self) -> list[Trade]:
        return [t for t in self.trades if t.exit_ts is not None]

    def summary(self) -> dict:
        closed = self.closed_trades
        wins = [t for t in closed if t.pnl > 0]
        total_return = float(
            (self.final_equity - self.initial_cash) / self.initial_cash * 100
        )
        gross_profit = sum((t.pnl for t in wins), Decimal(0))
        gross_loss = -sum((t.pnl for t in closed if t.pnl <= 0), Decimal(0))

        # 최대 낙폭
        peak = self.initial_cash
        mdd = 0.0
        for _, eq in self.equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                mdd = max(mdd, float((peak - eq) / peak * 100))

        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "trades": len(closed),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "total_return_pct": round(total_return, 2),
            "buy_hold_return_pct": round(self.buy_hold_return_pct, 2),
            "buy_hold_mdd_pct": round(self.buy_hold_mdd_pct, 2),
            "exposure_pct": round(self.exposure_pct, 1),
            "avg_weight_pct": round(self.avg_weight_pct, 1),
            "avg_pnl_pct": round(sum(t.pnl_pct for t in closed) / len(closed), 3) if closed else 0.0,
            "profit_factor": round(float(gross_profit / gross_loss), 2) if gross_loss > 0 else None,
            "max_drawdown_pct": round(mdd, 2),
            "avg_bars_held": round(sum(t.bars_held for t in closed) / len(closed), 1) if closed else 0.0,
            "open_position": len(self.trades) != len(closed),
        }


class Backtester:
    def __init__(
        self,
        strategy: CompositeStrategy,
        *,
        primary_tf: str = "D",
        higher_tfs: list[str] | None = None,
        initial_cash: Decimal = Decimal(10_000_000),
        fee_rate: Decimal = Decimal("0.00015"),
        sell_tax_rate: Decimal = Decimal("0.0018"),
        slippage_rate: Decimal = Decimal("0.0005"),
        warmup: int = 130,
        view_window: int = 320,  # 최장 룩백 모듈(52주 돌파=250봉)+워밍업 여유
        quantity_step: Decimal = Decimal(1),   # 주식 1주 / 코인 1e-8
        min_order_value: Decimal = Decimal(0),
    ):
        self.strategy = strategy
        self.primary_tf = primary_tf
        self.higher_tfs = higher_tfs or []
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self.sell_tax_rate = sell_tax_rate
        self.slippage_rate = slippage_rate
        self.warmup = warmup
        # 전략에 노출할 최근 봉 개수 — 지표 재계산이 O(전체길이)가 되는 것을 방지.
        # 최장 워밍업 모듈(price_above_ma 120)보다 충분히 크게 유지할 것.
        self.view_window = view_window
        self.quantity_step = quantity_step
        self.min_order_value = min_order_value

    def run(self, symbol: str, candles: list[Candle]) -> BacktestResult:
        if len(candles) <= self.warmup + 1:
            raise ValueError(f"캔들 부족: {len(candles)}개 (워밍업 {self.warmup} 필요)")

        higher: dict[str, tuple[list[Candle], list[int]]] = {
            tf: resample_progressive(candles, tf) for tf in self.higher_tfs
        }

        cash = self.initial_cash
        position: OpenPosition | None = None
        current_trade: Trade | None = None
        bars_in_market = 0
        weight_sum = 0.0
        result = BacktestResult(
            strategy=self.strategy.name, symbol=symbol,
            initial_cash=self.initial_cash, final_equity=self.initial_cash,
        )
        # (판단 결과를 다음 봉 시가에 체결하기 위한 보류 큐)
        pending: dict | None = None

        for i in range(self.warmup, len(candles)):
            bar = candles[i]

            # --- 1) 직전 봉에서 보류된 주문을 이번 봉 시가에 체결 ---
            if pending is not None:
                fill_price = bar.open
                if pending["action"] == "enter":
                    fill_price *= 1 + self.slippage_rate  # 매수는 불리하게
                    qty = pending["quantity"]
                    cost = fill_price * qty
                    fee = cost * self.fee_rate
                    if cost + fee <= cash:
                        cash -= cost + fee
                        position = OpenPosition(
                            side=OrderSide.BUY, quantity=qty,
                            entry_price=fill_price, entry_ts=bar.ts,
                            highest_close=bar.close,
                        )
                        current_trade = Trade(
                            symbol=symbol, entry_ts=bar.ts,
                            entry_price=fill_price, quantity=qty,
                            entry_reason=pending["reason"],
                        )
                        result.trades.append(current_trade)
                elif pending["action"] == "exit" and position is not None:
                    fill_price *= 1 - self.slippage_rate  # 매도는 불리하게
                    proceeds = fill_price * position.quantity
                    fee = proceeds * self.fee_rate
                    tax = proceeds * self.sell_tax_rate
                    cash += proceeds - fee - tax
                    entry_cost = position.entry_price * position.quantity
                    current_trade.exit_ts = bar.ts
                    current_trade.exit_price = fill_price
                    current_trade.exit_reason = pending["reason"]
                    current_trade.bars_held = position.bars_held
                    current_trade.pnl = (proceeds - fee - tax) - entry_cost * (
                        1 + self.fee_rate
                    )
                    current_trade.pnl_pct = float(
                        current_trade.pnl / (entry_cost if entry_cost else 1) * 100
                    )
                    position = None
                    current_trade = None
                pending = None

            # --- 2) 포지션 상태 갱신 + 노출도 집계 ---
            if position is not None:
                position.update_on_bar(bar)
                bars_in_market += 1
                eq_now = cash + position.quantity * bar.close
                if eq_now > 0:
                    weight_sum += float(position.quantity * bar.close / eq_now)

            # --- 3) 이번 봉 종가 기준 전략 판단 → 다음 봉 시가 체결 예약 ---
            view = MarketView(
                symbol=symbol,
                primary_tf=self.primary_tf,
                candles={
                    self.primary_tf: candles[max(0, i + 1 - self.view_window) : i + 1],
                    **{
                        tf: bars[max(0, counts[i] - self.view_window) : counts[i]]
                        for tf, (bars, counts) in higher.items()
                    },
                },
                quantity_step=self.quantity_step,
                min_order_value=self.min_order_value,
            )
            equity = cash + (
                position.quantity * bar.close if position else Decimal(0)
            )
            decision = self.strategy.evaluate(view, position, equity)
            if decision.action == "enter" and position is None:
                pending = {
                    "action": "enter",
                    "quantity": decision.quantity,
                    "reason": " / ".join(decision.reasons),
                }
            elif decision.action == "exit" and position is not None:
                pending = {
                    "action": "exit",
                    "reason": " / ".join(decision.reasons),
                }

            result.equity_curve.append((bar.ts, equity))

        # 미청산 포지션은 마지막 종가로 평가만 (강제 청산하지 않고 open으로 표시)
        last_close = candles[-1].close
        result.final_equity = cash + (
            position.quantity * last_close if position else Decimal(0)
        )

        # --- 벤치마크(바이앤홀드)와 노출도: 동일 시작점(워밍업 직후 시가) 기준 ---
        bh_entry = float(candles[self.warmup].open)
        result.buy_hold_return_pct = (float(last_close) / bh_entry - 1) * 100
        peak, bh_mdd = 0.0, 0.0
        for c in candles[self.warmup:]:
            px = float(c.close)
            peak = max(peak, px)
            bh_mdd = max(bh_mdd, (peak - px) / peak * 100)
        result.buy_hold_mdd_pct = bh_mdd

        total_bars = len(candles) - self.warmup
        result.exposure_pct = bars_in_market / total_bars * 100 if total_bars else 0.0
        result.avg_weight_pct = (
            weight_sum / bars_in_market * 100 if bars_in_market else 0.0
        )
        return result
