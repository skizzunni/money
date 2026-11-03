"""Replay MnqNoiseV38 (Funded growth's rules) on chosen days of a NinjaTrader MNQ export: the day's trades, and a chart.

    python research/replay_day.py <MNQ export .txt> [<another export>] <YYYY-MM-DD> [<YYYY-MM-DD> ...] [--out <folder>]

The export: NinjaTrader's Historical Data export of 1-minute MNQ bars ("yyyyMMdd HHmmss;open;high;low;close;volume",
UTC, each bar's end), as research/mnq_bars.py reads it. With two files (an old and a new contract) they are joined at
the roll, the older back-adjusted. It needs about 60 sessions before the first day asked for: the noise average (14
sessions), the calm-stretch rule (40) and the trend filter (50) read the sessions before.

The bot: Funded growth's rules on 5-minute bars in NinjaTrader's execution, at the starting size (1 MNQ, $187.50 max
loss, $250 after a loser, $900 a day, the 60-minute time stop). The account's later contracts multiply each trade's
P/L; the entries and exits are the same. For each day the script prints the trades and writes replay_<day>.html (a
candle chart with the noise lines at each check and every entry and exit), in --out (default: the current folder).
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
# Funded growth (docs/NINJATRADER_V38.md) at its starting size: no trailing floor or contract steps, so 1 MNQ a trade
GROWTH_1 = {"qty": 1, "max_loss_per_trade": 187.5, "after_loss_ml_mult": 250.0 / 187.5, "after_loss_qty_div": 1.0,
            "tighten_only": True, "take_profit": 2.0, "lock_at": 0.35, "lock_plus": 2.5, "stop_buffer": 0.24,
            "max_losers": 0, "last_entry_end": 900, "big_day_k": 1.5, "big_day_n": 10, "calm_k": 0.7,
            "calm_short": 10, "calm_long": 40, "daily_loss_limit": 900.0, "range_pos_min": 0.65, "trend_n": 50,
            "trend_side": -1, "squeeze_min": 20.0, "budget_actual": True, "time_stop": 60, "lookback": 14,
            "nt_execution": True, "round_prices": True, "target_on_fill_bar": True}


def stitch(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """The older contract through the first session both have a 15:59 bar for (the roll), the newer after it; the older
    back-adjusted by the difference of that 15:59 close (as research/mnq_bars.py's traded_series), so the roll is no
    price jump."""
    both = old.index.intersection(new.index)
    last = both[(both.hour == 15) & (both.minute == 59)]
    if not len(last):
        raise SystemExit("the two exports share no 15:59 bar: no day to roll on")
    roll = last[0]
    cut = roll.normalize() + pd.Timedelta(hours=18)  # the next session starts at 18:00
    a = old[old.index < cut].copy()
    a[["open", "high", "low", "close"]] += float(new.loc[roll, "close"] - old.loc[roll, "close"])
    return pd.concat([a, new[new.index >= cut]])


def load(paths: list[str]) -> pd.DataFrame:
    """The exports' 1-minute bars (oldest contract first, stitched at each roll), 09:30-16:00 New York and the 16:00
    bar, as 5-minute bars."""
    frames = sorted((M.load(p) for p in paths), key=lambda f: f.index[-1])
    one = frames[0]
    for f in frames[1:]:
        one = stitch(one, f)
    return resample(K.rth(one), "5min")


def replay(bars: pd.DataFrame, days: list[str]) -> dict[str, tuple[pd.DataFrame, pd.DataFrame, list]]:
    """Per day: its bars, its trades and its checks' noise lines (bar, upper, lower)."""
    res = run(bars, NoiseConfig(**GROWTH_1), minutes=5)
    tf = res.trades_frame()
    t = bars.index.tz_convert(NY)
    out = {}
    for d in days:
        on = t.strftime("%Y-%m-%d") == d
        if not on.any():
            raise SystemExit(f"{d}: no bars for that day in the export")
        first = int(on.argmax())
        sessions_before = len(set(t[:first].strftime("%Y-%m-%d")))
        if sessions_before < 60:
            print(f"WARNING {d}: only {sessions_before} sessions before it in the export (60 wanted); the noise, "
                  "calm and trend rules may differ from the live bot's")
        idx = [i for i in range(len(bars)) if on[i]]
        day_tf = tf[tf.entry_time.dt.tz_convert(NY).dt.strftime("%Y-%m-%d") == d]
        lines = [(i, u, lo) for i, u, lo in res.bands if on[i]]
        out[d] = (bars.iloc[idx], day_tf, lines)
    return out


def svg(day_bars: pd.DataFrame, trades: pd.DataFrame, lines: list, bars_index: pd.DatetimeIndex) -> str:
    """A candle chart: the bars, the noise lines from each check, entries (triangles) and exits (circles)."""
    w, h, pad = 1100, 520, 60
    lo = min(day_bars.low.min(), *(x[2] for x in lines)) if lines else day_bars.low.min()
    hi = max(day_bars.high.max(), *(x[1] for x in lines)) if lines else day_bars.high.max()
    span = max(hi - lo, 1.0)
    n = len(day_bars)
    pos = {ts: k for k, ts in enumerate(day_bars.index)}

    def x(k: float) -> float:
        return pad + (k + 0.5) * (w - 2 * pad) / n

    def y(p: float) -> float:
        return pad + (hi - p) * (h - 2 * pad) / span

    el = [f'<rect width="{w}" height="{h}" fill="#fff"/>']
    for k in range(5):
        p = lo + span * k / 4
        el.append(f'<line x1="{pad}" x2="{w - pad}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eee"/>'
                  f'<text x="{w - pad + 4}" y="{y(p) + 4:.1f}" font-size="11" fill="#666">{p:.2f}</text>')
    t = day_bars.index.tz_convert(NY)
    for k, (ts, r) in enumerate(zip(t, day_bars.itertuples(), strict=True)):
        c = "#2e7d32" if r.close >= r.open else "#c62828"
        el.append(f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="{y(r.high):.1f}" y2="{y(r.low):.1f}" stroke="{c}"/>')
        top, bot = y(max(r.open, r.close)), y(min(r.open, r.close))
        el.append(f'<rect x="{x(k) - 3:.1f}" y="{top:.1f}" width="6" height="{max(bot - top, 1):.1f}" fill="{c}"/>')
        if ts.minute == 0:
            el.append(f'<text x="{x(k) - 14:.1f}" y="{h - pad + 18}" font-size="11" fill="#666">'
                      f'{ts.hour}:00</text>')
    first = bars_index.get_loc(day_bars.index[0])
    for j, (i, u, lw) in enumerate(lines):  # each check's lines hold until the next check
        k0 = i - first
        k1 = (lines[j + 1][0] - first) if j + 1 < len(lines) else n
        for p, col in ((u, "#1565c0"), (lw, "#ef6c00")):
            el.append(f'<line x1="{x(k0):.1f}" x2="{x(k1 - 1):.1f}" y1="{y(p):.1f}" y2="{y(p):.1f}" '
                      f'stroke="{col}" stroke-dasharray="4 3"/>')
    for r in trades.itertuples():
        if r.entry_time in pos:
            k = pos[r.entry_time]
            up = r.direction > 0
            pts = (f"{x(k)},{y(r.entry) + (14 if up else -14)} {x(k) - 7},{y(r.entry) + (26 if up else -26)} "
                   f"{x(k) + 7},{y(r.entry) + (26 if up else -26)}")
            el.append(f'<polygon points="{pts}" fill="{"#2e7d32" if up else "#c62828"}"/>')
        if r.exit_time in pos:
            k = pos[r.exit_time]
            el.append(f'<circle cx="{x(k):.1f}" cy="{y(r.exit):.1f}" r="5" fill="none" stroke="#000" stroke-width="2"/>'
                      f'<text x="{x(k) + 8:.1f}" y="{y(r.exit) - 8:.1f}" font-size="11">{html.escape(r.reason)} '
                      f'{"+" if r.pnl >= 0 else "-"}${abs(r.pnl):.2f}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%">{"".join(el)}</svg>'


def page(day: str, day_bars: pd.DataFrame, trades: pd.DataFrame, lines: list, bars_index: pd.DatetimeIndex) -> str:
    rows = "".join(
        f"<tr><td>{'LONG' if r.direction > 0 else 'SHORT'}</td><td>{r.entry_time.tz_convert(NY):%H:%M}</td>"
        f"<td>{r.entry:.2f}</td><td>{r.exit_time.tz_convert(NY):%H:%M}</td><td>{r.exit:.2f}</td>"
        f"<td>{html.escape(r.reason)}</td><td>{'+' if r.pnl >= 0 else '-'}${abs(r.pnl):.2f}</td></tr>"
        for r in trades.itertuples())
    total = trades.pnl.sum() if len(trades) else 0.0
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>MnqNoiseV38 replay {day}</title>"
            "<style>body{font-family:sans-serif;margin:16px}table{border-collapse:collapse}"
            "td,th{border:1px solid #ccc;padding:4px 8px}</style></head><body>"
            f"<h2>MnqNoiseV38, Funded growth's rules, {day} (5-minute bars, per 1 MNQ)</h2>"
            f"{svg(day_bars, trades, lines, bars_index)}"
            "<p>Dashed lines: the upper (blue) and lower (orange) noise lines from each half-hour check. Triangles: "
            "entries (green long, red short). Circles: exits.</p>"
            "<table><tr><th>side</th><th>in</th><th>entry</th><th>out</th><th>exit</th><th>why</th><th>P/L</th></tr>"
            f"{rows}</table><p>Day: {'+' if total >= 0 else '-'}${abs(total):.2f} per MNQ; "
            f"{len(trades)} trades.</p></body></html>")


def main() -> None:
    args = sys.argv[1:]
    out = Path(".")
    if "--out" in args:
        k = args.index("--out")
        out = Path(args[k + 1])
        del args[k:k + 2]
    files = [a for a in args if not (len(a) == 10 and a[4] == "-" and a[7] == "-")]
    days = [a for a in args if a not in files]
    if not files or not days:
        raise SystemExit(__doc__)
    bars = load(files)
    out.mkdir(parents=True, exist_ok=True)
    for d, (day_bars, trades, lines) in replay(bars, days).items():
        print(f"\n{d}: {len(trades)} trades, {'+' if trades.pnl.sum() >= 0 else '-'}${abs(trades.pnl.sum()):.2f} "
              "per MNQ")
        for r in trades.itertuples():
            print(f"  {'LONG ' if r.direction > 0 else 'SHORT'} {r.entry_time.tz_convert(NY):%H:%M} {r.entry:.2f} -> "
                  f"{r.exit_time.tz_convert(NY):%H:%M} {r.exit:.2f}  {r.reason:<14} "
                  f"{'+' if r.pnl >= 0 else '-'}${abs(r.pnl):.2f}")
        f = out / f"replay_{d}.html"
        f.write_text(page(d, day_bars, trades, lines, bars.index))
        print(f"  chart: {f}")


if __name__ == "__main__":
    main()
