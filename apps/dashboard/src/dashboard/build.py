"""대시보드 빌드 엔트리포인트.

  uv run dashboard-build                          # data/events → data/reports/dashboard.html
  uv run dashboard-build --out 경로.html
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .metrics import load_bots
from .render import render_page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", default="data/events")
    parser.add_argument("--out", default="data/reports/dashboard.html")
    args = parser.parse_args()

    bots = load_bots(Path(args.events_dir))
    if not bots:
        raise SystemExit(f"이벤트 없음: {args.events_dir}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_page(bots), encoding="utf-8")
    for bot in bots:
        print(f"  {bot.name}: 거래 {len(bot.exits)}건 ({bot.wins}승 {bot.losses}패, "
              f"{bot.win_rate:.1f}%), 수익률 {bot.total_return_pct:+.2f}%")
    print(f"대시보드 생성: {out}")


if __name__ == "__main__":
    main()
