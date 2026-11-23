# ruff: noqa: E501
"""A bias + Fibonacci pullback strategy (the user, 2026-11-23: "identify a bias, figure out where the market is trending,
find a point to enter; Fibonacci", in the style of the RyzensTrades channel), on NQ 2015-2025 (MNQ) and ES 2020-2024 (MES).

Rules, one trade a day, 1 micro contract, regular hours:
  * bias: "sma20" trades only longs when yesterday's close is above the average of the last 20 daily closes and only
    shorts below it; "none" takes the first side whose setup triggers;
  * the leg (long): the day's high so far H and the lowest low before it L, at least `leg` (a fraction of the price)
    apart; for a short the day's low so far and the highest high before it;
  * entry: a limit at the `ent` retracement of the leg (0.5 / 0.618 / 0.705 from the high back toward the low), working
    from 10:00 to 14:30, filled when a minute trades a tick through it; a new high moves the leg (and the level) up;
  * stop: the `sl` retracement (0.786, or 1.0 = the swing low) minus a tick; target: the `tp` level of the leg measured
    from L (1.0 = a retest of H, 1.272 = the extension); out at 15:59 otherwise; the stop first in a minute reaching both;
  * $0.62 a side, a tick of slippage on the stop and the 15:59 exit.
The account test as research/orb_every_day.py: fresh 50K starts every quarter, 12 months, the $2,000 trailing floor.

    python research/fib_pullback.py <nq1m_scaled.pkl> <es_continuous_1m.parquet> <out.csv>
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd
from orb_every_day import FEE, NY, SPEC, account_test, sessions


def day_trade(s, bias: int, leg: float, ent: float, sl: float, tp: float, tick: float):
    d, mm, o, h, lo, c = s
    n = len(o)
    hi_v, hi_t, lo_v, lo_t = h[0], 0, lo[0], 0
    for k in range(1, n):
        if mm[k] >= 870:
            return None
        # the long leg: the high so far and the lowest low before it; the short leg likewise
        if mm[k] >= 600:
            for side in ((1,) if bias > 0 else (-1,) if bias < 0 else (1, -1)):
                if side > 0:
                    top = hi_v
                    bot = lo[:hi_t + 1].min()
                else:
                    bot = lo_v
                    top = h[:lo_t + 1].max()
                size = top - bot
                if size < leg * c[k - 1] or (side > 0 and hi_t == 0) or (side < 0 and lo_t == 0):
                    continue
                level = top - ent * size if side > 0 else bot + ent * size
                stop = top - sl * size - tick if side > 0 else bot + sl * size + tick
                # the setup is dead once price has traded through its stop since the swing (fixed 2026-11-23: before,
                # an entry far past the stop counted the "stop" above the fill as a win)
                if (side > 0 and lo[hi_t:k].min() <= stop) or (side < 0 and h[lo_t:k].max() >= stop):
                    continue
                target = bot + tp * size if side > 0 else top - tp * size
                hit = lo[k] <= level - tick if side > 0 else h[k] >= level + tick
                if not hit:
                    continue
                fill = min(o[k], level) if side > 0 else max(o[k], level)
                for j in range(k, n):
                    if (side > 0 and lo[j] <= stop) or (side < 0 and h[j] >= stop):
                        px = (min(o[j], stop) if side > 0 else max(o[j], stop)) if j > k else stop
                        return d, side, (px - side * tick - fill) * side
                    if j > k and ((side > 0 and h[j] >= target + tick) or (side < 0 and lo[j] <= target - tick)):
                        return d, side, (target - fill) * side  # never on the fill minute (its order is unknown)
                    if mm[j] >= 959:
                        return d, side, (c[j] - side * tick - fill) * side
                return d, side, (c[-1] - side * tick - fill) * side
        if h[k] > hi_v:
            hi_v, hi_t = h[k], k
        if lo[k] < lo_v:
            lo_v, lo_t = lo[k], k
    return None


GRID = [("sma20", "none"), (0.003, 0.005), (0.5, 0.618, 0.705), (0.786, 1.0), (1.0, 1.272)]


def study(name, ss, sym, legs):
    tick, pv = SPEC[sym]
    closes = pd.Series([s[5][-1] for s in ss])
    sma = closes.rolling(20).mean().shift(1)
    prev = closes.shift(1)
    bias_sma = np.where(prev > sma, 1, np.where(prev < sma, -1, 0))
    rows = []
    for b, lg, ent, sl, tp in itertools.product(*GRID):
        if sl <= ent:
            continue
        tr = []
        for i, s in enumerate(ss):
            if b == "sma20" and (i < 21 or bias_sma[i] == 0):
                continue
            x = day_trade(s, int(bias_sma[i]) if b == "sma20" else 0, lg, ent, sl, tp, tick)
            if x is not None:
                tr.append(x)
        if not tr:
            continue
        t = pd.DataFrame(tr, columns=["d", "side", "pts"])
        t["usd"] = t.pts * pv - 2 * FEE
        daily = t.groupby("d").usd.sum().reindex([x[0] for x in ss], fill_value=0.0)  # every session
        eq = daily.cumsum()
        yr = t.groupby(pd.to_datetime(t.d).dt.year).usd.sum()
        rows.append({"set": name, "bias": b, "leg": lg, "entry": ent, "stop": sl, "target": tp,
                     "days_traded": round(len(tr) / len(ss), 3), "win": round((t.usd > 0).mean(), 3),
                     "net": round(t.usd.sum()), "per_trade": round(t.usd.mean(), 2),
                     "pf": round(t.usd[t.usd > 0].sum() / max(1e-9, -t.usd[t.usd < 0].sum()), 2),
                     "dd": round((eq.cummax().clip(lower=0) - eq).max()), "worst_day": round(daily.min()),
                     "yrs_up": f"{(yr > 0).sum()}/{len(yr)}", **account_test(daily)})
        print(rows[-1], flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    nq = pd.read_pickle(sys.argv[1])
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)][["open", "high", "low", "close"]]
    es = pd.read_parquet(sys.argv[2])[["open", "high", "low", "close"]]
    es.index = es.index.tz_convert(NY)
    out = pd.concat([study("NQ 2015-25 (MNQ)", sessions(nq), "MNQ", (0.003, 0.005)),
                     study("ES 2020-24 (MES)", sessions(es), "MES", (0.003, 0.005))])
    out.to_csv(sys.argv[3], index=False)


if __name__ == "__main__":
    main()
