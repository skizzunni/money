"""Round one hundred and four: the overnight drift in MNQ (description and test).

    python research/overnight_drift.py nsx1m_scaled.pkl nq1m_scaled.pkl

The bot and the breakout trade 09:30-16:00 only; MNQ trades almost all night, and Apex only asks for flat by
16:59 New York. Boyarchenko, Larsen and Whelan ("The Overnight Drift", Review of Financial Studies 2023) find US
index futures' overnight returns concentrated in the first hours of European trading (about 02:00-03:00 New York)
and larger after US sessions that fell. A new cue for the hours the account sits idle, in the user's own market.

Trades, at 1 MNQ, each night between two regular sessions d and d' (Friday's runs into Monday): long at the open of
the first minute at or after T1, out at the open of the first minute at or after T2 (each within 5 minutes, else no
trade). Costs $1.24 a round trip and a tick each way ($2.24 a trade). Nights that cross a month end are left out (the
rescaled index data's monthly gap).
Windows (New York): 18:00-09:30, 18:00-02:00, 01:00-04:00, 02:00-03:00, 04:00-09:30. Conditions: every night;
after session d fell (its 16:00 close below its 09:30 open); after it rose. 15 rules.
Bar, fixed before running: a rule counts if on 2011-18 its mean $ a trade is positive and survives Benjamini-Hochberg
at 10% across the 15 (one-sided t-test), AND it is positive with t >= 2 on 2019-25 AND on NQ futures 2015-25.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402

PV, COST = 2.0, 1.24 + 2 * 0.25 * 2.0
WINDOWS = {"18:00-09:30": (-360, 570), "18:00-02:00": (-360, 120), "01:00-04:00": (60, 240),
           "02:00-03:00": (120, 180), "04:00-09:30": (240, 570)}  # minutes from midnight of d'
CONDS = ("all", "after down", "after up")


def nights(path):
    """Per night: d' (the next session's date), session d's 09:30-16:00 return in points, and the price at every
    window time (NaN if no minute within 5 minutes)."""
    bars = pd.read_pickle(path)
    idx = bars.index.tz_convert(A.NY)
    o = bars.open.to_numpy(float)
    c = bars.close.to_numpy(float)
    ns = idx.as_unit("ns").asi8  # ns since epoch, for searchsorted (the index data is stored in us)
    tmin = idx.hour * 60 + idx.minute
    days = idx.normalize()
    rth_open = np.flatnonzero(tmin == 570)
    sess = days[rth_open]
    rows = []
    for k in range(len(rth_open) - 1):
        d, d2 = sess[k], sess[k + 1]
        if d.month != d2.month:
            continue
        a = rth_open[k]
        last = np.flatnonzero((days[a:a + 500] == d) & (tmin[a:a + 500] < 960))
        if not len(last):
            continue
        ret = c[a + last[-1]] - o[a]
        row = {"day": d2.tz_localize(None), "ret": ret}
        for t in sorted({m for w in WINDOWS.values() for m in w}):
            target = d2 + pd.Timedelta(minutes=t)
            j = int(np.searchsorted(ns, target.value))
            ok = j < len(ns) and ns[j] - target.value <= 5 * 60 * 10**9
            row[t] = o[j] if ok else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def table(df, first, last):
    df = df[(df.day >= pd.Timestamp(first)) & (df.day <= pd.Timestamp(last))]
    out = []
    for w, (t1, t2) in WINDOWS.items():
        for cond in CONDS:
            x = df if cond == "all" else df[df.ret < 0] if cond == "after down" else df[df.ret > 0]
            pnl = ((x[t2] - x[t1]) * PV - COST).dropna().to_numpy()
            t, p = stats.ttest_1samp(pnl, 0.0, alternative="greater")
            out.append({"window": w, "cond": cond, "trades": len(pnl), "$/trade": pnl.mean(),
                        "win %": 100 * (pnl > 0).mean(), "t": t, "p": p,
                        "$/year": pnl.sum() / max(1e-9, (x.day.max() - x.day.min()).days / 365.25)})
    return pd.DataFrame(out)


def main() -> None:
    with ProcessPoolExecutor(max_workers=2) as pool:
        nsx, nq = pool.map(nights, sys.argv[1:3])
    pd.set_option("display.width", 200)
    res = {"2011-2018": table(nsx, "2011-01-01", "2018-12-31"), "2019-2025": table(nsx, "2019-01-01", "2026-09-30"),
           "NQ 2015-2025": table(nq, "2015-01-01", "2025-07-31")}
    for k, v in res.items():
        print(f"\n{k}")
        print(v.round(3).to_string(index=False))
    disc = res["2011-2018"].copy()
    m = len(disc)
    order = disc.p.rank(method="first")
    disc["bh"] = disc.p <= 0.10 * order / m
    # step-up: every rule up to the largest rank that passes
    passing = order[disc.bh]
    disc["bh"] = order <= (passing.max() if len(passing) else 0)
    print()
    found = False
    for i, r in disc.iterrows():
        if not (r.bh and r["$/trade"] > 0):
            continue
        h = [res[p].iloc[i] for p in ("2019-2025", "NQ 2015-2025")]
        ok = all(x["$/trade"] > 0 and x.t >= 2 for x in h)
        found |= ok
        print(f"{r.window} {r.cond}: discovery p {r.p:.4f}; holdouts t {h[0].t:.2f} / {h[1].t:.2f}: "
              f"{'COUNTS' if ok else 'does not count'}")
    print("found" if found else "nothing counts")


if __name__ == "__main__":
    main()
