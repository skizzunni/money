"""Round twenty-three: the bot's edge in the hours it doesn't trade.

    python research/overnight_noise.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. Nasdaq futures trade about 23 hours a day; the bot works 10:00-16:00
New York time. Rounds seven and eight tested overnight returns and drifts, never the bot's own logic (a move
past the usual range for the time since the session opened tends to keep going) inside an overnight
session. Fixed before running:
  Europe: session opens 03:00, checks every half hour 03:30-09:00, flat at 09:25.
  Asia:   session opens 20:00, checks every half hour 20:30-02:30, flat at 02:55.
  Noise for each check time = the average |close / session open - 1| at that time over the last 14
  complete sessions; lines = session open x (1 +/- noise). Flat: buy above the upper line, sell below the
  lower at the next open. In a trade: the bot's resting stop (0.24 noise units past the line) and the
  $116.67 max loss. 1 contract, $1.24 fees and 2 ticks of slippage per fill (thinner market), prices at
  today's level.
  Pass: the session's own daily P&L t >= 2.24 on 2011-2018 (5% two-sided over two), t >= 1.65 on 2019-2022,
  then t >= 1.65 on 2023 - Sep 2026, run once. Each session is judged on its own; it would trade alongside
  the bot, never at the same time.
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
TICK, SLIP, PV, FEE = 0.25, 2, 2.0, 1.24
SESSIONS = {"Europe": (180, 385), "Asia": (1200, 415)}  # start minute (New York), minutes until flat


def simulate(bars: pd.DataFrame, start: int, length: int) -> pd.DataFrame:
    checks = list(range(30, length - 25 + 1, 30))  # minutes since the session opened
    kof = {m: j for j, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    slip = SLIP * TICK
    ring = np.full((LOOKBACK, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    s_open = upper = lower = sigma = math.nan
    pos, entry, ebar, pending = 0, 0.0, 0, 0
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[ebar], idx[i], pos, pos * (px - entry) * PV - FEE, why))
        pos = 0

    for i in range(len(bars)):
        clock = (mins[i] - start) % 1440
        end = clock + 5
        inside = clock < length
        if pending:
            if pos == 0 and inside:
                pos, entry, ebar = pending, o[i] + pending * slip, i
            pending = 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            if ebar != i:
                cap = entry - pos * CAP_PTS
                stop = max(stop, cap) if pos > 0 else min(stop, cap)
            if ebar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * slip
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * slip
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * slip
            if hit:
                close(i, px, "stop")
        if pos and (not inside or clock == 0):
            close(i, c[i] - pos * slip, "gap")
        if clock == 0:
            s_open = o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if inside and not math.isnan(s_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / s_open - 1)
            if filled >= LOOKBACK:
                sigma = ring[:, j].mean()
                upper, lower = s_open * (1 + sigma), s_open * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending = 1
                elif pos == 0 and c[i] < lower:
                    pending = -1
        if inside and end == length:
            if pos:
                close(i, c[i] - pos * slip, "session end")
            pending = 0
            if not math.isnan(s_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            s_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), *SESSIONS[name])


def tstat(d: pd.Series) -> float:
    return d.mean() / d.std(ddof=1) * math.sqrt(len(d))


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    with ProcessPoolExecutor(max_workers=2) as ex:
        runs = dict(ex.map(_job, [(str(cache), n) for n in SESSIONS]))
    for name, tf in runs.items():
        # drop trades touching a month change (the price rescale makes a fake jump there)
        month_in = tf.entry_time.dt.tz_localize(None).dt.to_period("M")
        tf = tf[month_in == tf.exit_time.dt.tz_localize(None).dt.to_period("M")]
        tf = tf[~tf.entry_time.dt.tz_localize(None).dt.normalize().isin(first_sessions)]
        day = tf.exit_time.dt.tz_localize(None).dt.normalize()
        d_all = tf.groupby(day).pnl.sum()
        verdict = None
        for label, y0, y1, bar in (("2011-2018", 2011, 2018, 2.24), ("2019-2022", 2019, 2022, 1.65),
                                   ("2023-2026", 2023, 2026, 1.65)):
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            d = d_all.reindex(ss).fillna(0.0)
            t = tf[(day >= ss[0]) & (day <= ss[-1])]
            eq = d.cumsum()
            print(f"{name:7s} {label}  trades/day {len(t) / len(ss):.2f}  win {100 * (t.pnl > 0).mean():.1f}%  "
                  f"$/day {d.mean():+.2f}  t {tstat(d):+.2f}  worst stretch {(eq.cummax() - eq).max():.0f}")
            if tstat(d) < bar:
                verdict = f"FAIL at {label}"
                break
        print(f"{name}: {verdict or 'PASS all three'}\n")


if __name__ == "__main__":
    main()
