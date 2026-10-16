"""Round twenty-eight: up to 10 contracts and never more than $350 at risk, sized per trade.

    python research/risk_size.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. The account rules are "up to 10 MNQ" and "at most $350 lost per trade".
Fixed 10 contracts makes the $350 a $35-per-contract stop, which normal 5-minute moves hit (round
twenty-seven: about $6 a day per contract on 2023-2026). Risk-based sizing keeps both rules: at each signal,
measure the distance from the expected fill (the signal close plus a tick) to the bot's own stop (0.24 noise
units past the line), and trade n = floor($350 / (distance x $2)) contracts, between 1 and 10. The $350 max
loss stays in force for the whole position from the fill (so with n contracts it sits $350 / n / $2 points
away, at or beyond the line stop unless the line moves). The bot otherwise as it trades now: half-hour
checks, the 1.5-noise-unit take-profit from the bar after the fill, flat at 16:00. $1.24 fees + 1 tick per
contract per fill, prices at today's level.
Compared, in total $ per day (not per contract):
  fixed 10 with a $350 max loss (the current setting), fixed 3 with a $350 max loss, and risk-sized up to 10.
Pass bar, fixed before running, against fixed 10: more $ per day, a higher t-stat, and a worst losing stretch
no larger, on 2011-2018; then on 2019-2022; then on 2023 - Sep 2026, run once.
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

LOOKBACK, BUF, TP = 14, 0.24, 1.5
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
BUDGET, MAX_QTY = 350.0, 10
VARIANTS = {"fixed 10, $350 max loss": ("fixed", 10), "fixed 3, $350 max loss": ("fixed", 3),
            "risk-sized up to 10, $350 max loss": ("risk", 10)}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))


def simulate(bars: pd.DataFrame, mode: str, qty: int) -> pd.DataFrame:
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
    pos, n, entry, ebar, pending, pend_n, est = 0, 0, 0.0, 0, 0, 0, math.nan
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[ebar], idx[i], pos, n, n * (pos * (px - entry) * PV - FEE), why))
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, n, entry, ebar = pending, pend_n, o[i] + pending * TICK, i
            pending = 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            cap = (entry if ebar != i else est) - pos * BUDGET / n / PV
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
            elif ebar != i:
                tp = entry * (1 + pos * TP * sigma)
                if (pos > 0 and h[i] >= tp + TICK) or (pos < 0 and l[i] <= tp - TICK):
                    close(i, tp, "target")
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
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                side = 1 if c[i] > upper else -1 if c[i] < lower else 0
                if pos == 0 and side:
                    pending, est = side, c[i] + side * TICK
                    if mode == "fixed":
                        pend_n = qty
                    else:
                        line_stop = upper * (1 - BUF * sigma) if side > 0 else lower * (1 + BUF * sigma)
                        dist = abs(est - line_stop)
                        pend_n = int(min(max(math.floor(BUDGET / (dist * PV)), 1), qty))
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "qty", "pnl", "why"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), *VARIANTS[name])


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=3) as ex:
        runs = {n: MT.clean(tf, first_sessions) for n, tf in ex.map(_job, [(str(cache), n) for n in VARIANTS])}
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            table[(name, label)] = s
            rows.append((name, label, t.qty.mean(), s["win %"], t.pnl.min(), s["$/day"], s["t"], s["worst stretch"],
                         s["months up %"]))
    df = pd.DataFrame(rows, columns=["sizing", "period", "avg contracts", "win %", "worst trade", "$/day", "t",
                                     "worst stretch", "months up %"])
    print(df.round(2).to_string(index=False))

    def passes(label):
        a, b = table[("risk-sized up to 10, $350 max loss", label)], table[("fixed 10, $350 max loss", label)]
        return a["$/day"] > b["$/day"] and a["t"] > b["t"] and a["worst stretch"] <= b["worst stretch"]

    for label in ("2011-2018", "2019-2022"):
        ok = passes(label)
        print(f"{label}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return
    ss = sessions[sessions.year >= 2023]
    for name in VARIANTS:
        t = runs[name][runs[name].entry_time.dt.year >= 2023]
        s = MT.stats(t, ss)
        table[(name, "2023-2026")] = s
        print(f"  2023-26 {name:36s} avg contracts {t.qty.mean():.1f}  win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  "
              f"t {s['t']:.2f}  worst stretch {s['worst stretch']:.0f}  worst trade {t.pnl.min():.0f}")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes('2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
