"""Round twenty: let the noise area adapt to today's market.

    python research/adaptive.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. The noise area is the range price usually wanders in by each time of
day, from a plain 14-session average. Volatility clusters, so today's normal range is better predicted by
recent and current conditions than by a flat average; and two independent levels breaking together should
be a stronger signal than one. Four angles, five variants:
  A. Overnight-adjusted band. At 09:30, r = today's overnight range (high - low from 18:00 to 09:30, over the
     09:30 open) / its average over the last 14 sessions. Every sigma today is multiplied by r ** b, with r
     clipped to [0.5, 2]. Variants b = 0.5, 1.0.
  B. Faster-adapting band. Sigma for each check time is an exponentially weighted average of past moves with
     a half-life of 7 sessions, instead of the plain 14-session mean (started from that mean).
  C. A 09:45 check. One more check, with its own noise from the 09:45 moves; the rest unchanged.
  D. Yesterday's levels. Take a breakout only if the check also closed past yesterday's RTH high (long) or
     low (short).
The bot otherwise as it trades (5-minute bars, line stop 0.24 noise units past the line, $116.67 max loss,
flat at 16:00), 1 contract, $1.24 fees + 1 tick per fill, prices at today's level.
Pass bar, fixed before running, against the bot: on 2011-2018 $ per day no lower, t-stat no more than 0.3
lower, $ per day per dollar of worst losing stretch higher. The passing variant with the highest of that
last measure goes on; the same tests on 2019-2022; then 2023 - Sep 2026, run once.
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
OPEN, CLOSE, LAST = 570, 960, 930
VARIANTS = {"bot": {}, "overnight 0.5": {"overnight": 0.5}, "overnight 1.0": {"overnight": 1.0},
            "fast average": {"ewma": True}, "09:45 check": {"early": True}, "yesterday's levels": {"levels": True}}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def simulate(bars: pd.DataFrame, overnight: float | None = None, ewma: bool = False, early: bool = False,
             levels: bool = False) -> pd.DataFrame:
    checks = ([585] if early else []) + list(range(600, LAST + 1, 30))
    kof = {m: j for j, m in enumerate(checks)}
    n_k = len(checks)
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((LOOKBACK, n_k), np.nan)
    ew = np.full(n_k, np.nan)
    alpha = 1 - 0.5 ** (1 / 7)
    today = np.full(n_k, np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, entry, ebar, pending = 0, 0.0, 0, 0
    on_hi = on_lo = math.nan
    on_hist: list[float] = []
    scale = 1.0
    y_hi = y_lo = math.nan
    d_hi = d_lo = math.nan
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
        if t_min == 18 * 60:  # the overnight session starts
            on_hi, on_lo = h[i], l[i]
        elif not in_rth and t_min != OPEN and not math.isnan(on_hi) and (t_min >= 18 * 60 or t_min < OPEN):
            on_hi, on_lo = max(on_hi, h[i]), min(on_lo, l[i])
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
            scale = 1.0
            if not math.isnan(on_hi):
                r_on = (on_hi - on_lo) / o[i]
                if overnight is not None and len(on_hist) >= LOOKBACK and np.mean(on_hist[-LOOKBACK:]) > 0:
                    r = min(max(r_on / np.mean(on_hist[-LOOKBACK:]), 0.5), 2.0)
                    scale = r ** overnight
                on_hist.append(r_on)
            on_hi = on_lo = math.nan
            d_hi, d_lo = h[i], l[i]
        if in_rth:
            last_close = c[i]
            d_hi, d_lo = max(d_hi, h[i]), min(d_lo, l[i])
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                base = ew[j] if ewma else ring[:, j].mean()
                sigma = base * scale
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                side = 1 if c[i] > upper else -1 if c[i] < lower else 0
                if levels and side and not math.isnan(y_hi):
                    if (side > 0 and c[i] <= y_hi) or (side < 0 and c[i] >= y_lo):
                        side = 0
                if pos == 0 and side:
                    pending = side
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
                if filled == LOOKBACK:
                    ew = ring.mean(axis=0)
                elif filled > LOOKBACK:
                    ew = (1 - alpha) * ew + alpha * today
            y_hi, y_lo = d_hi, d_lo
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), **VARIANTS[name])


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
        runs = {n: MT.clean(tf, first_sessions) for n, tf in ex.map(_job, [(str(cache), n) for n in VARIANTS])}
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in PERIODS[:2]:  # the final period is read once, below
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
            table[(name, label)] = s
            w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
            rows.append((name, label, s["trades/day"], s["win %"], w.mean(), lo.mean(), s["$/day"], s["t"],
                         s["worst stretch"], s["eff"]))
    df = pd.DataFrame(rows, columns=["variant", "period", "trades/day", "win %", "avg win", "avg loss", "$/day",
                                     "t", "worst stretch", "$/day per $1k stretch"])
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
        print(f"  2023-26 {name:20s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
