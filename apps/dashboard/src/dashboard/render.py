"""성과 대시보드 HTML 렌더러 — self-contained (외부 의존 없음).

시각화 규칙 (dataviz 방법론):
- 시리즈 색은 검증된 카테고리 팔레트 슬롯 1~3 고정 순서
- 수익/손실 극성은 diverging 페어(빨강/파랑)를 한국 관례로 배치 (빨강=수익)
- 상태색·시리즈색을 텍스트에 쓰지 않음 (텍스트는 잉크 토큰)
- 라이트/다크 모두 지원, 호버 툴팁 기본 탑재, 표 뷰 병행
"""

from __future__ import annotations

import html
import json
from datetime import datetime

from .metrics import BotMetrics

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]          # 카테고리 슬롯 1~3 (라이트)
SERIES_DARK = ["#3987e5", "#d95926", "#199e70"]
POS, NEG = "#e34948", "#2a78d6"                     # 수익=빨강, 손실=파랑 (KR 관례)
POS_DARK, NEG_DARK = "#e66767", "#3987e5"

CSS = """
:root { color-scheme: light dark; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page); color: var(--ink); }
.viz-root {
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --pos:#e34948; --neg:#2a78d6; --up-text:#a01f1f; --down-text:#1c5cab;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .viz-root {
    --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
    --pos:#e66767; --neg:#3987e5; --up-text:#e66767; --down-text:#86b6ef;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70;
  }
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 24px 20px 48px; }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 28px 0 10px; color: var(--ink); }
.sub { color: var(--muted); font-size: 12px; margin-bottom: 20px; }
.tiles { display:flex; flex-wrap:wrap; gap:12px; }
.tile { flex:1 1 150px; background:var(--surface); border:1px solid var(--border);
  border-radius:10px; padding:14px 16px; min-width:140px; }
.tile .label { font-size:12px; color:var(--ink2); margin-bottom:6px; }
.tile .value { font-size:26px; font-weight:650; line-height:1.1; }
.tile .note { font-size:11px; color:var(--muted); margin-top:4px; }
.up { color: var(--up-text); } .down { color: var(--down-text); }
.card { background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:16px; margin-top:12px; overflow-x:auto; position:relative; }
svg text { font-family: inherit; }
table { border-collapse: collapse; width:100%; font-size:12.5px; }
th { text-align:left; color:var(--ink2); font-weight:600; border-bottom:1px solid var(--axis);
  padding:6px 8px; white-space:nowrap; }
td { padding:6px 8px; border-bottom:1px solid var(--grid); vertical-align:top; }
td.num, th.num { text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap; }
.chip { display:inline-block; font-size:11px; font-weight:650; padding:1px 7px;
  border-radius:9px; border:1px solid var(--border); }
.chip.w { color:var(--up-text); } .chip.l { color:var(--down-text); }
.reason { color:var(--ink2); font-size:11.5px; max-width:420px; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }
.tooltip { position:absolute; pointer-events:none; background:var(--surface);
  border:1px solid var(--border); border-radius:8px; padding:8px 10px; font-size:12px;
  box-shadow:0 4px 14px rgba(0,0,0,0.12); display:none; z-index:10; white-space:nowrap; }
.legend { display:flex; gap:14px; font-size:12px; color:var(--ink2); margin-bottom:8px; }
.legend .sw { display:inline-block; width:10px; height:10px; border-radius:2px;
  margin-right:5px; vertical-align:-1px; }
.grid2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }
"""


def fmt_pct(v: float, decimals: int = 2) -> str:
    cls = "up" if v > 0 else ("down" if v < 0 else "")
    return f'<span class="{cls}">{v:+.{decimals}f}%</span>'


def fmt_krw(v: float) -> str:
    return f"{v:,.0f}원"


def fmt_price(v: float) -> str:
    """체결가 표기 — 1,000원 미만은 소수점 유지 (SHIB 등 1원 미만 코인이 0으로 뭉개짐 방지)."""
    if v >= 1000:
        return f"{v:,.0f}"
    return f"{v:.8f}".rstrip("0").rstrip(".") or "0"


# ------------------------------------------------------------------ 차트
def equity_chart_svg(bots: list[BotMetrics], width: int = 1020, height: int = 260) -> str:
    """자산 곡선 (봇별 시리즈, 크로스헤어 툴팁)."""
    pad_l, pad_r, pad_t, pad_b = 56, 12, 12, 24
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b

    series = []
    all_dates: set = set()
    for bot in bots[:3]:
        if len(bot.equity_curve) < 2:
            continue
        base = bot.equity_curve[0][1]
        pts = [(d, eq / base * 100 - 100) for d, eq in bot.equity_curve]  # 수익률 %
        series.append((bot.name, pts))
        all_dates.update(d for d, _ in pts)
    if not series:
        return "<p class='sub'>자산 데이터 없음</p>"

    dates = sorted(all_dates)
    d0, d1 = dates[0], dates[-1]
    span = max((d1 - d0).days, 1)
    ys = [v for _, pts in series for _, v in pts]
    y_min, y_max = min(ys + [0]), max(ys + [0])
    y_range = max(y_max - y_min, 1e-9)

    def x_of(d): return pad_l + (d - d0).days / span * plot_w
    def y_of(v): return pad_t + (y_max - v) / y_range * plot_h

    # 그리드 (수평 4단)
    grid, labels = [], []
    for i in range(5):
        v = y_max - y_range * i / 4
        y = y_of(v)
        grid.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width-pad_r}" y2="{y:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        labels.append(f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{v:+.0f}%</text>')
    # 0선 강조
    if y_min < 0 < y_max:
        y0 = y_of(0)
        grid.append(f'<line x1="{pad_l}" y1="{y0:.1f}" x2="{width-pad_r}" y2="{y0:.1f}" stroke="var(--axis)" stroke-width="1"/>')
    # x 라벨 (연도)
    seen_years = set()
    for d in dates:
        if d.year not in seen_years and d.month <= 2:
            seen_years.add(d.year)
            labels.append(f'<text x="{x_of(d):.1f}" y="{height-6}" font-size="11" fill="var(--muted)">{d.year}</text>')

    paths = []
    for idx, (name, pts) in enumerate(series):
        d_attr = "M" + " L".join(f"{x_of(d):.1f},{y_of(v):.1f}" for d, v in pts)
        paths.append(f'<path d="{d_attr}" fill="none" stroke="var(--s{idx+1})" stroke-width="2" stroke-linejoin="round"/>')

    data_json = json.dumps([
        {"name": name, "pts": [[d.isoformat(), round(v, 2)] for d, v in pts]}
        for name, pts in series
    ])
    legend = "".join(
        f'<span><span class="sw" style="background:var(--s{i+1})"></span>{html.escape(name)}</span>'
        for i, (name, _) in enumerate(series)
    )
    return f"""
<div class="legend">{legend}</div>
<div style="position:relative">
<svg id="eqchart" viewBox="0 0 {width} {height}" style="width:100%;display:block" data-series='{html.escape(data_json)}'
     data-d0="{d0.isoformat()}" data-span="{span}" data-padl="{pad_l}" data-plotw="{plot_w}">
  {''.join(grid)}{''.join(labels)}{''.join(paths)}
  <line id="xhair" x1="0" y1="{pad_t}" x2="0" y2="{height-pad_b}" stroke="var(--axis)" stroke-width="1" visibility="hidden"/>
</svg>
<div class="tooltip" id="eqtip"></div>
</div>"""


def monthly_bar_svg(monthly: list[tuple[str, float]], width: int = 1020, height: int = 200) -> str:
    """월간 수익률 바 (수익=빨강, 손실=파랑, 2px 갭, 4px 라운드 데이터엔드)."""
    monthly = monthly[-24:]
    if not monthly:
        return "<p class='sub'>월간 데이터 없음</p>"
    pad_l, pad_r, pad_t, pad_b = 56, 12, 12, 26
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    v_max = max(max(v for _, v in monthly), 0.0)
    v_min = min(min(v for _, v in monthly), 0.0)
    v_range = max(v_max - v_min, 1e-9)
    y_zero = pad_t + v_max / v_range * plot_h
    bar_w = plot_w / len(monthly) - 2  # 2px 갭

    bars, labels = [], []
    extremes = {max(monthly, key=lambda x: x[1])[0], min(monthly, key=lambda x: x[1])[0]}
    for i, (label, v) in enumerate(monthly):
        x = pad_l + i * (plot_w / len(monthly)) + 1
        h = abs(v) / v_range * plot_h
        y = y_zero - h if v >= 0 else y_zero
        color = "var(--pos)" if v >= 0 else "var(--neg)"
        rx = min(4.0, bar_w / 2, h)
        # 데이터 끝만 라운드: 위(양수)/아래(음수) 모서리만
        if v >= 0:
            d = (f"M{x:.1f},{y+h:.1f} L{x:.1f},{y+rx:.1f} Q{x:.1f},{y:.1f} {x+rx:.1f},{y:.1f} "
                 f"L{x+bar_w-rx:.1f},{y:.1f} Q{x+bar_w:.1f},{y:.1f} {x+bar_w:.1f},{y+rx:.1f} "
                 f"L{x+bar_w:.1f},{y+h:.1f} Z")
        else:
            d = (f"M{x:.1f},{y:.1f} L{x:.1f},{y+h-rx:.1f} Q{x:.1f},{y+h:.1f} {x+rx:.1f},{y+h:.1f} "
                 f"L{x+bar_w-rx:.1f},{y+h:.1f} Q{x+bar_w:.1f},{y+h:.1f} {x+bar_w:.1f},{y+h-rx:.1f} "
                 f"L{x+bar_w:.1f},{y:.1f} Z")
        bars.append(f'<path d="{d}" fill="{color}"><title>{label}: {v:+.2f}%</title></path>')
        if label in extremes:
            ly = y - 5 if v >= 0 else y + h + 13
            labels.append(f'<text x="{x+bar_w/2:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="10.5" fill="var(--ink2)">{v:+.1f}%</text>')
        if label.endswith("-01") or i == 0:
            labels.append(f'<text x="{x:.1f}" y="{height-6}" font-size="10.5" fill="var(--muted)">{label[:4]}</text>')

    axis = (f'<line x1="{pad_l}" y1="{y_zero:.1f}" x2="{width-pad_r}" y2="{y_zero:.1f}" '
            f'stroke="var(--axis)" stroke-width="1"/>')
    return (f'<svg viewBox="0 0 {width} {height}" style="width:100%;display:block">'
            f'{axis}{"".join(bars)}{"".join(labels)}</svg>')


TOOLTIP_JS = """
<script>
(function(){
  const svg = document.getElementById('eqchart');
  if (!svg) return;
  const tip = document.getElementById('eqtip');
  const xhair = document.getElementById('xhair');
  const series = JSON.parse(svg.dataset.series);
  const d0 = new Date(svg.dataset.d0);
  const span = +svg.dataset.span, padl = +svg.dataset.padl, plotw = +svg.dataset.plotw;
  svg.addEventListener('mousemove', ev => {
    const rect = svg.getBoundingClientRect();
    const scale = rect.width / svg.viewBox.baseVal.width;
    const vx = (ev.clientX - rect.left) / scale;
    const days = Math.round((vx - padl) / plotw * span);
    if (days < 0 || days > span) { tip.style.display='none'; xhair.setAttribute('visibility','hidden'); return; }
    const target = new Date(d0.getTime() + days * 86400000);
    let rows = [];
    for (const s of series) {
      let best = null, bd = 1e18;
      for (const [ds, v] of s.pts) {
        const diff = Math.abs(new Date(ds) - target);
        if (diff < bd) { bd = diff; best = [ds, v]; }
      }
      if (best) rows.push(`<b>${s.name}</b>: ${best[1] >= 0 ? '+' : ''}${best[1].toFixed(2)}% <span style="color:var(--muted)">(${best[0]})</span>`);
    }
    tip.innerHTML = rows.join('<br>');
    tip.style.display = 'block';
    const tx = Math.min(ev.clientX - rect.left + 14, rect.width - tip.offsetWidth - 4);
    tip.style.left = tx + 'px';
    tip.style.top = (ev.clientY - rect.top - 10) + 'px';
    xhair.setAttribute('x1', vx); xhair.setAttribute('x2', vx);
    xhair.setAttribute('visibility', 'visible');
  });
  svg.addEventListener('mouseleave', () => { tip.style.display='none'; xhair.setAttribute('visibility','hidden'); });
})();
</script>
"""


# ------------------------------------------------------------------ 테이블
def period_table(title: str, rows: list[tuple[str, float]], limit: int) -> str:
    rows = rows[-limit:]
    body = "".join(
        f"<tr><td>{html.escape(k)}</td><td class='num'>{fmt_pct(v)}</td></tr>"
        for k, v in reversed(rows)
    )
    return (f'<div class="card"><h2 style="margin-top:0">{title}</h2>'
            f'<table><thead><tr><th>기간</th><th class="num">수익률</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def trades_table(bot: BotMetrics, limit: int = 14) -> str:
    rows = []
    for e in reversed(bot.exits[-limit:]):
        win = e.get("win")
        chip = '<span class="chip w">승</span>' if win else '<span class="chip l">패</span>'
        reasons_full = html.escape(" / ".join(e.get("reasons", [])))
        rows.append(
            f"<tr><td>{e['ts'][:10]}</td>"
            f"<td>{html.escape(e.get('name', e['symbol']))}</td>"
            f"<td>{html.escape(e.get('strategy', ''))}</td>"
            f"<td class='num'>{fmt_price(float(e['entry_price']))} → {fmt_price(float(e['exit_price']))}</td>"
            f"<td class='num'>{fmt_pct(e.get('pnl_pct', 0.0))}</td>"
            f"<td>{chip}</td>"
            f"<td class='reason' title='{reasons_full}'>{reasons_full}</td></tr>"
        )
    open_rows = []
    for e in bot.open_positions():
        reasons_full = html.escape(" / ".join(e.get("reasons", [])))
        open_rows.append(
            f"<tr><td>{e['ts'][:10]}</td>"
            f"<td>{html.escape(e.get('name', e['symbol']))}</td>"
            f"<td>{html.escape(e.get('strategy', ''))}</td>"
            f"<td class='num'>{fmt_price(float(e['price']))} (보유중)</td>"
            f"<td class='num'>—</td><td><span class='chip'>보유</span></td>"
            f"<td class='reason' title='{reasons_full}'>{reasons_full}</td></tr>"
        )
    return (f'<table><thead><tr><th>청산일</th><th>종목</th><th>전략</th>'
            f'<th class="num">진입 → 청산</th><th class="num">손익</th><th>결과</th>'
            f'<th>사유 (진입/청산)</th></tr></thead>'
            f'<tbody>{"".join(open_rows)}{"".join(rows)}</tbody></table>')


# ------------------------------------------------------------------ 페이지
def render_page(bots: list[BotMetrics]) -> str:
    total_realized = sum(b.realized_pnl for b in bots)
    total_wins = sum(b.wins for b in bots)
    total_closed = sum(len(b.exits) for b in bots)
    total_rate = total_wins / total_closed * 100 if total_closed else 0.0

    sections = []
    for bot in bots:
        # 가동 초기: 데이터가 쌓이기 전이라는 것을 명시 (빈 차트를 고장으로 오인하지 않게)
        if len(bot.equity_curve) < 2:
            days = len(bot.equity_curve)
            notice = (f'<div class="card" style="border-style:dashed"><b>가동 초기</b><br>'
                      f'<span class="sub">사이클 {days}회 기록됨. 거래가 발생하고 자산 스냅샷이 '
                      f'2일 이상 쌓이면 곡선·기간별 수익률이 표시됩니다.</span></div>')
        else:
            notice = ""
        tiles = notice + f"""
<div class="tiles">
  <div class="tile"><div class="label">총 수익률</div>
    <div class="value">{fmt_pct(bot.total_return_pct)}</div>
    <div class="note">연환산 {bot.cagr_pct:+.1f}%</div></div>
  <div class="tile"><div class="label">전적 (승률)</div>
    <div class="value">{bot.wins}승 {bot.losses}패</div>
    <div class="note">승률 {bot.win_rate:.1f}%</div></div>
  <div class="tile"><div class="label">실현 손익</div>
    <div class="value">{fmt_pct(bot.realized_pnl / bot.equity_curve[0][1] * 100 if bot.equity_curve else 0)}</div>
    <div class="note">{fmt_krw(bot.realized_pnl)}</div></div>
  <div class="tile"><div class="label">최대 낙폭</div>
    <div class="value">-{bot.max_drawdown_pct:.1f}%</div>
    <div class="note">자산 곡선 기준</div></div>
</div>"""
        sections.append(f"""
<h2>🤖 {html.escape(bot.name)}</h2>
{tiles}
<div class="card">
  <h2 style="margin-top:0">자산 곡선 (수익률 기준)</h2>
  {equity_chart_svg([bot])}
</div>
<div class="card">
  <h2 style="margin-top:0">월간 수익률</h2>
  {monthly_bar_svg(bot.monthly_returns())}
</div>
<div class="grid2">
  {period_table("주간 수익률", bot.weekly_returns(), 8)}
  {period_table("월간 수익률", bot.monthly_returns(), 12)}
  {period_table("연간 수익률", bot.yearly_returns(), 6)}
</div>
<div class="card">
  <h2 style="margin-top:0">최근 거래 (사유 포함)</h2>
  {trades_table(bot)}
</div>""")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>트레이딩 대시보드</title>
<style>{CSS}</style></head>
<body><div class="viz-root"><div class="wrap">
<h1>트레이딩 대시보드</h1>
<div class="sub">생성 {now} · 데이터 소스: data/events/*.jsonl · 봇 {len(bots)}개 ·
전체 전적 {total_wins}승 {total_closed - total_wins}패 (승률 {total_rate:.1f}%) ·
실현손익 합계 {fmt_krw(total_realized)}</div>
{''.join(sections)}
</div></div>
{TOOLTIP_JS}
</body></html>"""
