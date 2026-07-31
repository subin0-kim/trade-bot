"""이벤트 로그(data/events/*.jsonl) → 성과 지표 계산.

대시보드는 봇에 직접 붙지 않는다 — 이벤트 파일만 읽는다 (아키텍처 원칙 5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class BotMetrics:
    name: str
    entries: list[dict] = field(default_factory=list)
    exits: list[dict] = field(default_factory=list)
    equity_curve: list[tuple[date, float]] = field(default_factory=list)

    # --- 전적 ---
    @property
    def wins(self) -> int:
        return sum(1 for e in self.exits if e.get("win"))

    @property
    def losses(self) -> int:
        return len(self.exits) - self.wins

    @property
    def win_rate(self) -> float:
        return self.wins / len(self.exits) * 100 if self.exits else 0.0

    @property
    def realized_pnl(self) -> float:
        return sum(float(e.get("pnl", 0)) for e in self.exits)

    # --- 수익률 ---
    @property
    def total_return_pct(self) -> float:
        if len(self.equity_curve) < 2 or self.equity_curve[0][1] == 0:
            return 0.0
        return (self.equity_curve[-1][1] / self.equity_curve[0][1] - 1) * 100

    @property
    def max_drawdown_pct(self) -> float:
        peak, mdd = 0.0, 0.0
        for _, eq in self.equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                mdd = max(mdd, (peak - eq) / peak * 100)
        return mdd

    @property
    def cagr_pct(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        days = (self.equity_curve[-1][0] - self.equity_curve[0][0]).days
        if days < 30 or self.equity_curve[0][1] <= 0:
            return 0.0
        ratio = self.equity_curve[-1][1] / self.equity_curve[0][1]
        return (ratio ** (365.25 / days) - 1) * 100

    def period_returns(self, key_fn) -> list[tuple[str, float]]:
        """기간별 수익률: 각 기간 마지막 자산 vs 직전 기간 마지막 자산."""
        if not self.equity_curve:
            return []
        last_by_period: dict[str, float] = {}
        for d, eq in self.equity_curve:
            last_by_period[key_fn(d)] = eq
        keys = sorted(last_by_period)
        out = []
        for i, k in enumerate(keys):
            base = last_by_period[keys[i - 1]] if i > 0 else self.equity_curve[0][1]
            if base > 0:
                out.append((k, (last_by_period[k] / base - 1) * 100))
        return out

    def weekly_returns(self) -> list[tuple[str, float]]:
        return self.period_returns(lambda d: f"{d.isocalendar().year}-W{d.isocalendar().week:02d}")

    def monthly_returns(self) -> list[tuple[str, float]]:
        return self.period_returns(lambda d: f"{d.year}-{d.month:02d}")

    def yearly_returns(self) -> list[tuple[str, float]]:
        return self.period_returns(lambda d: str(d.year))

    def open_positions(self) -> list[dict]:
        """청산 이벤트가 없는 진입 = 보유 중."""
        closed: dict[str, int] = {}
        for e in self.exits:
            closed[e["symbol"]] = closed.get(e["symbol"], 0) + 1
        opened: list[dict] = []
        for e in self.entries:
            if closed.get(e["symbol"], 0) > 0:
                closed[e["symbol"]] -= 1
            else:
                opened.append(e)
        return opened


def load_bots(events_dir: Path) -> list[BotMetrics]:
    bots: dict[str, BotMetrics] = {}
    for path in sorted(events_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            source = e.get("source", path.stem)
            bot = bots.setdefault(source, BotMetrics(name=source))
            etype = e.get("type")
            if etype == "entry":
                bot.entries.append(e)
            elif etype == "exit":
                bot.exits.append(e)
            elif etype == "equity":
                try:
                    ts = datetime.fromisoformat(e["ts"])
                    bot.equity_curve.append((ts.date(), float(e["equity"])))
                except (KeyError, ValueError):
                    continue
    for bot in bots.values():
        # 날짜만 키로 안정 정렬 — 튜플 통짜 정렬은 같은 날 스냅샷을 '값 오름차순'으로
        # 재배열해 마지막 값이 최신이 아닌 그날의 최댓값이 됨 (수익률 낙관 왜곡)
        bot.equity_curve.sort(key=lambda x: x[0])
        bot.entries.sort(key=lambda e: e.get("ts", ""))
        bot.exits.sort(key=lambda e: e.get("ts", ""))
    # 이벤트가 있는 봇만
    return [b for b in bots.values() if b.entries or b.equity_curve]
