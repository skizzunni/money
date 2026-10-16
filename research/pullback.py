"""Round thirty-three: sell the bounce, not the breakdown. A limit entry a little better than the signal price.

    python research/pullback.py nsx_5m_scaled.pkl

Reasoning, written before running. On 16 October 2026 the bot shorted four breakdowns that bounced about 17 points
inside the first 5 minutes and stopped out, then one that ran for +$3,278. A breakout often pulls back to retest
before it runs; entering on that pullback instead of at market gives a better price (and a stop further from the
entry), at the cost of missing the breakouts that never look back.
Rule: at a signal, instead of a market order at the next open, rest a limit order k noise units better than the
signal close (above it for a short, below it for a long): limit = close x (1 + side x (-k) x sigma) ... i.e. a sell
limit at close x (1 + k sigma), a buy limit at close x (1 - k sigma). It fills when price trades a tick through it,
at the limit (no slippage), and is cancelled at the next half-hour check if not filled (that check decides afresh).
Everything else as the bot trades now: line stop 0.24 noise units past the line, max loss live from the fill
(the limit price), 1.5-noise-unit take-profit from the bar after the fill, flat at 16:00. On the fill bar the stop
is checked after the fill (worst case). 1 contract, $1.24 fees, 1 tick slippage on market and stop fills, prices at
today's level.
Variants: k = 0.1 and 0.25; each at $116.67 a contract (the tested max loss) and at $35 (the $350 over 10 MNQ).
Pass bar against the bot at the same max loss, fixed before running: on 2011-2018 $ per day no lower, a t-stat no
more than 0.3 lower, more $ per day per dollar of worst losing stretch; the best passing variant goes on (judged at
$116.67); the same on 2019-2022; then 2023 - Sep 2026, run once.
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
import profit_levers as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402

LOOKBACK, BUF, TP = 14, 0.24, 1.5
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
CAPS = {"$117": 350.0 / 3 / PV, "$35": 35.0 / PV}
VARIANTS = [(cap, k) for cap in CAPS for k in (None, 0.1, 0.25)]
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))


def simulate(bars: pd.DataFrame, cap_pts: float, k: float) -> pd.DataFrame:
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
    pos, entry, ebar = 0, 0.0, 0
    order_side, order_px = 0, math.nan  # a resting limit entry
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[ebar], idx[i], pos, pos * (px - entry) * PV - FEE, why))
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if order_side and pos == 0 and in_rth:
            d = order_side
            if (d < 0 and h[i] >= order_px + TICK) or (d > 0 and l[i] <= order_px - TICK):
                pos, entry, ebar, order_side = d, order_px, i, 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            cap = entry - pos * cap_pts
            stop = max(stop, cap) if pos > 0 else min(stop, cap)
            if ebar == i:  # filled inside this bar: the stop counts if the bar reached it at all (worst case)
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = stop - pos * TICK
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
            order_side = 0
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            order_side = 0  # an unfilled limit is cancelled at the next check
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                side = 1 if c[i] > upper else -1 if c[i] < lower else 0
                if pos == 0 and side:
                    order_side = side
                    order_px = round(c[i] * (1 - side * k * sigma) / TICK) * TICK
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            order_side = 0
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why"])


def _job(args):
    path, (cap, k) = args
    bars = pd.read_pickle(path)
    if k is None:
        tf = P.simulate(bars, target=TP, target_on_fill_bar=False, cap_pts=CAPS[cap], cap_on_fill_bar=True)
    else:
        tf = simulate(bars, CAPS[cap], k)
    return (cap, k), tf


def main() -> None:
    path = sys.argv[1]
    bars = pd.read_pickle(path)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first))]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = {key: MT.clean(tf, first) for key, tf in ex.map(_job, [(path, v) for v in VARIANTS])}
    table, rows = {}, []
    for (cap, k), tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
            table[(cap, k, label)] = s
            rows.append((cap, "market (the bot)" if k is None else f"limit {k} better", label, s["trades/day"],
                         s["win %"], s["$/day"], s["t"], s["worst stretch"], s["eff"]))
    df = pd.DataFrame(rows, columns=["max loss", "entry", "period", "trades/day", "win %", "$/day", "t",
                                     "worst stretch", "$/day per $1k stretch"])
    print(df.round(2).to_string(index=False))

    def passes(cap, k, label):
        a, b = table[(cap, k, label)], table[(cap, None, label)]
        return a["$/day"] >= b["$/day"] and a["t"] >= b["t"] - 0.3 and a["eff"] > b["eff"]

    cands = [k for k in (0.1, 0.25) if passes("$117", k, "2011-2018")]
    print(f"\nDiscovery 2011-2018 at $117 a contract: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda k: table[("$117", k, "2011-2018")]["eff"])
    ok = passes("$117", best, "2019-2022")
    print(f"Best: limit {best} better. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    ss = sessions[sessions.year >= 2023]
    for k in (None, best):
        t = runs[("$117", k)][runs[("$117", k)].entry_time.dt.year >= 2023]
        s = MT.stats(t, ss)
        s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
        table[("$117", k, "2023-2026")] = s
        print(f"  2023-26 {'market' if k is None else f'limit {k}':10s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  "
              f"t {s['t']:.2f}  worst stretch {s['worst stretch']:.0f}")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes('$117', best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
