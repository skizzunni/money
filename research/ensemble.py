"""Round twenty-two: spread the same bot over several copies instead of looking for a better signal.

    python research/ensemble.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. Every earlier round looked for a better signal. This one keeps the
signal and splits the contracts across copies of the bot that differ only in when they look (checks at
:00/:30 or at :15/:45) or over how many sessions they measure the noise area (10, 14 or 20). Each copy
trades the same edge, but their good and bad days don't line up exactly, so the average should keep the
profit per contract and shrink the losing stretches. This is diversification, not discovery: no copy is
chosen for its own backtest.
Variants, fixed before running (P&L per contract = the average of the copies, each run on 1 contract):
  offset checks: the bot + a copy checking at 10:15, 10:45, ..., 15:45
  mixed windows: copies with 10, 14 and 20-session noise averages
  both: the six combinations
Each copy: 5-minute bars, line stop 0.24 noise units past the line, $116.67 max loss per contract, flat at
16:00, $1.24 fees + 1 tick per fill, prices at today's level.
Pass bar against the bot: on 2011-2018 at least 95% of its $ per day, a t-stat at least as high, and a
smaller worst losing stretch. The passing variant with the smallest worst stretch goes on; the same tests
on 2019-2022; then 2023 - Sep 2026, run once.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402

from mnqbot.data import NY  # noqa: E402

BUF, CAP_PTS = 0.24, (350.0 / 3) / 2.0
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE = 570, 960
COPIES = {(first, lookback) for first in (600, 615) for lookback in (10, 14, 20)}
VARIANTS = {
    "bot": [(600, 14)],
    "offset checks": [(600, 14), (615, 14)],
    "mixed windows": [(600, 10), (600, 14), (600, 20)],
    "both": sorted(COPIES),
}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))


def simulate(bars: pd.DataFrame, first: int = 600, lookback: int = 14) -> pd.DataFrame:
    """One copy of the bot: half-hour checks from `first` to 15:30 (or 15:45), a `lookback`-session noise area."""
    checks = list(range(first, CLOSE - 15 + 1, 30)) if first % 30 else list(range(first, 930 + 1, 30))
    kof = {m: j for j, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((lookback, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, entry, ebar, pending = 0, 0.0, 0, 0
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[ebar], idx[i], pos, pos * (px - entry) * PV - FEE, why))
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, entry, ebar = pending, o[i] + pending * TICK, i
            pending = 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            if ebar != i:
                cap = entry - pos * CAP_PTS
                stop = max(stop, cap) if pos > 0 else min(stop, cap)
            if ebar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if hit:
                close(i, px, "stop")
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * TICK, "session")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= lookback and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending = 1
                elif pos == 0 and c[i] < lower:
                    pending = -1
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % lookback
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why"])


def _job(args):
    path, copy = args
    return copy, simulate(pd.read_pickle(path), *copy)


def daily(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.Series:
    return tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum().reindex(sessions).fillna(0.0)


def stats(d: pd.Series) -> dict:
    eq = d.cumsum()
    return {"$/day": d.mean(), "t": d.mean() / d.std(ddof=1) * math.sqrt(len(d)),
            "worst stretch": (eq.cummax() - eq).max(), "worst day": d.min(), "days up %": 100 * (d > 0).mean(),
            "months up %": 100 * (d.groupby(d.index.to_period("M")).sum() > 0).mean()}


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = {cp: daily(MT.clean(tf, first_sessions), sessions)
                for cp, tf in ex.map(_job, [(str(cache), cp) for cp in sorted(COPIES)])}
    days = {name: sum(runs[cp] for cp in copies) / len(copies) for name, copies in VARIANTS.items()}
    print("correlation of the copies' daily P&L, 2011-2022:")
    fit = pd.DataFrame({f"{f // 60}:{f % 60:02d} lb{lb}": runs[(f, lb)] for f, lb in sorted(COPIES)})
    print(fit[fit.index.year <= 2022].corr().round(2).to_string())
    table, rows = {}, []
    for name, d in days.items():
        for label, y0, y1 in PERIODS:
            s = stats(d[(d.index.year >= y0) & (d.index.year <= y1)])
            table[(name, label)] = s
            rows.append((name, label, s["$/day"], s["t"], s["worst stretch"], s["worst day"], s["days up %"],
                         s["months up %"]))
    print(pd.DataFrame(rows, columns=["variant", "period", "$/day", "t", "worst stretch", "worst day", "days up %",
                                      "months up %"]).round(2).to_string(index=False))

    def passes(name, label):
        a, b = table[(name, label)], table[("bot", label)]
        return a["$/day"] >= 0.95 * b["$/day"] and a["t"] >= b["t"] and a["worst stretch"] < b["worst stretch"]

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = min(cands, key=lambda n: table[(n, "2011-2018")]["worst stretch"])
    ok = passes(best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    for name in ("bot", best):
        s = stats(days[name][days[name].index.year >= 2023])
        table[(name, "2023-2026")] = s
        print(f"  2023-26 {name:14s} $/day {s['$/day']:.2f}  t {s['t']:.2f}  worst stretch {s['worst stretch']:.0f}  "
              f"worst day {s['worst day']:.0f}  months up {s['months up %']:.0f}%")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
