"""Round twenty-four: Fed announcement days.

    python research/fomc.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

The scheduled FOMC announcement days 2011-2026 are in research/fomc_dates.csv, taken from the Federal
Reserve's meeting calendars (federalreserve.gov/monetarypolicy/fomccalendars.htm and fomchistorical<year>.htm;
unscheduled meetings, conference calls and notation votes left out). The statement comes out at 14:00 New
York time (in 2011-2012 some came at 12:30 or 14:15).

Reasoning, written before running. The announcement is the largest scheduled event for Nasdaq; price often
whipsaws at 14:00 and then trends. The bot treats the day like any other. Fixed before running:
  step aside: on Fed days, flat at the 13:55 bar close, no entries from the 13:30 and 14:00 checks; normal
    again from the 14:30 check.
  skip the day: no trades on Fed days.
  double after: on Fed days, entries from the 14:30 check on trade 2 contracts.
  pre-Fed long only: on Fed days, no short entries before the 14:00 check (the documented pre-announcement
    drift is upward).
The bot otherwise as it trades, 1 contract, $116.67 max loss per contract, prices at today's level.
Pass bar against the bot, as in rounds nineteen and twenty: on 2011-2018 $ per day no lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch higher; the best of those goes on; the same on
2019-2022; then 2023 - Sep 2026, run once.
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

LOOKBACK, BUF, CAP_PTS = 14, 0.24, (350.0 / 3) / 2.0
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
FOMC = {pd.Timestamp(d).date() for d in pd.read_csv(Path(__file__).with_name("fomc_dates.csv")).date}
VARIANTS = ["bot", "step aside", "skip the day", "double after", "pre-Fed long only"]
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))


def simulate(bars: pd.DataFrame, variant: str = "bot") -> pd.DataFrame:
    checks = list(range(FIRST, LAST + 1, 30))
    kof = {m: j for j, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((LOOKBACK, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, qty, entry, ebar, pending, pending_qty = 0, 1, 0.0, 0, 0, 1
    fed = False
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[ebar], idx[i], pos, qty, qty * (pos * (px - entry) * PV - FEE), why, fed))
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, qty, entry, ebar = pending, pending_qty, o[i] + pending * TICK, i
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
            fed = idx[i].date() in FOMC
        if in_rth:
            last_close = c[i]
        if fed and variant == "step aside" and end == 835 and pos:  # flat at the 13:55 bar close
            close(i, c[i] - pos * TICK, "before Fed")
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                side = 1 if c[i] > upper else -1 if c[i] < lower else 0
                if fed:
                    if variant == "skip the day" or (variant == "step aside" and end in (810, 840)):
                        side = 0
                    if variant == "pre-Fed long only" and side < 0 and end < 840:
                        side = 0
                if pos == 0 and side:
                    pending = side
                    pending_qty = 2 if (fed and variant == "double after" and end >= 870) else 1
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "qty", "pnl", "why", "fed"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), name)


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    fed_days = sessions[sessions.map(lambda d: d.date() in FOMC)]
    print(f"Fed days in the test sessions: {len(fed_days)} (2011-2018: {(fed_days.year <= 2018).sum()})")
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = {n: MT.clean(tf, first_sessions) for n, tf in ex.map(_job, [(str(cache), n) for n in VARIANTS])}
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
            table[(name, label)] = s
            fd = t[t.fed]
            fdd = fd.groupby(fd.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum()
            n_fed = ((fed_days.year >= y0) & (fed_days.year <= y1)).sum()
            rows.append((name, label, s["$/day"], s["t"], s["worst stretch"], s["eff"], fdd.sum() / n_fed,
                         len(fd)))
    df = pd.DataFrame(rows, columns=["variant", "period", "$/day", "t", "worst stretch", "$/day per $1k stretch",
                                     "$ per Fed day", "Fed-day trades"])
    print(df.round(2).to_string(index=False))

    def passes(name, label):
        a, b = table[(name, label)], table[("bot", label)]
        return a["$/day"] >= b["$/day"] and a["t"] >= b["t"] - 0.3 and a["eff"] > b["eff"]

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["eff"])
    ok = passes(best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    ss = sessions[sessions.year >= 2023]
    for name in ("bot", best):
        t = runs[name][runs[name].entry_time.dt.year >= 2023]
        s = MT.stats(t, ss)
        s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
        table[(name, "2023-2026")] = s
        fd = t[t.fed]
        print(f"  2023-26 {name:18s} $/day {s['$/day']:.2f}  t {s['t']:.2f}  worst stretch {s['worst stretch']:.0f}"
              f"  Fed-day P&L {fd.pnl.sum():+.0f} on {len(fd)} trades")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
