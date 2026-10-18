"""Round one hundred and nineteen: the hours next to the session, after the close and before the open.

    python research/edge_hours.py nsx1m_scaled.pkl nq1m_scaled.pkl

The bot and the breakout trade 09:30-16:00; Apex's day runs to 16:59 and starts at 18:00, so 16:00-16:59 and the
morning before 09:30 are open to the account. Trades at 1 MNQ, in at the open of the first minute of the window, out
at the open of the minute after it (16:59: the 16:59 bar's close), $2.24 costs a trade; a minute missing at either
end: no trade. Sessions straddling a month end left out (the rescaled data's gap).
Windows: 16:00-16:30, 16:00-16:59 (after session d), 09:00-09:30, 08:30-09:30 (before session d').
Signals: "with" = in the direction of the move before the window (16:00 windows: session d's 09:30-16:00; morning
windows: the prior close at 16:00 to the window's start); "against" = the other way; "long" = long. 12 rules.
Bar, fixed before running: Benjamini-Hochberg at 10% on 2011-18 (one-sided), then t >= 2 on 2019-26 AND NQ 2015-25,
and positive in the 13 months from July 2025.
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
WINDOWS = {"16:00-16:30": ("after", 960, 990), "16:00-16:59": ("after", 960, 1019),
           "09:00-09:30": ("before", 540, 570), "08:30-09:30": ("before", 510, 570)}


def table_rows(path):
    bars = pd.read_pickle(path)
    idx = bars.index.tz_convert(A.NY)
    ns = idx.as_unit("ns").asi8
    o, c = bars.open.to_numpy(float), bars.close.to_numpy(float)
    tmin = idx.hour * 60 + idx.minute
    sess = idx[tmin == 570].normalize().unique()

    def at(t):
        j = int(np.searchsorted(ns, t.value))
        return j if j < len(ns) and ns[j] == t.value else None

    rows = []
    for k in range(1, len(sess) - 1):
        d, d2 = sess[k], sess[k + 1]
        if d.month != d2.month:
            continue
        a, z = at(d + pd.Timedelta(minutes=570)), at(d + pd.Timedelta(minutes=959))
        if a is None or z is None:
            continue
        rth = c[z] - o[a]
        row = {"day": d.tz_localize(None)}
        for name, (side, m0, m1) in WINDOWS.items():
            base = d if side == "after" else d2
            j0 = at(base + pd.Timedelta(minutes=m0))
            j1 = at(base + pd.Timedelta(minutes=m1))
            if j0 is None or j1 is None:
                row[name] = np.nan
                continue
            exit_px = c[j1] if m1 == 1019 else o[j1]
            move = rth if side == "after" else o[j0] - c[z]
            row[name] = exit_px - o[j0]
            row[name + " prior"] = move
        rows.append(row)
    return pd.DataFrame(rows)


def rules(df):
    out = []
    for name in WINDOWS:
        r, prior = df[name].to_numpy(), np.sign(df[name + " prior"].to_numpy())
        ok = ~np.isnan(r) & (prior != 0)
        for sig in ("with", "against", "long"):
            d = prior if sig == "with" else -prior if sig == "against" else np.ones_like(prior)
            out.append((f"{name} {sig}", (d * r * PV - COST)[ok]))
    return out


def table(df, first, last):
    df = df[(df.day >= pd.Timestamp(first)) & (df.day <= pd.Timestamp(last))]
    res = []
    for name, pnl in rules(df):
        t, p = stats.ttest_1samp(pnl, 0.0, alternative="greater")
        res.append({"rule": name, "trades": len(pnl), "$/trade": pnl.mean(), "win %": 100 * (pnl > 0).mean(),
                    "t": t, "p": p})
    return pd.DataFrame(res)


def main() -> None:
    with ProcessPoolExecutor(max_workers=2) as pool:
        nsx, nq = pool.map(table_rows, sys.argv[1:3])
    res = {"2011-2018": table(nsx, "2011-01-01", "2018-12-31"), "2019-2026": table(nsx, "2019-01-01", "2026-09-30"),
           "Jul 2025-Sep 2026": table(nsx, "2025-07-01", "2026-09-30"), "NQ 2015-2025": table(nq, "2015-01-01",
                                                                                            "2025-07-31")}
    pd.set_option("display.width", 200)
    for k, v in res.items():
        print(f"\n{k}")
        print(v.round(3).to_string(index=False))
    disc = res["2011-2018"]
    rank = disc.p.rank(method="first")
    passing = rank[disc.p <= 0.10 * rank / len(disc)]
    cut = passing.max() if len(passing) else 0
    found = False
    print()
    for i, r in disc.iterrows():
        if rank[i] > cut or r["$/trade"] <= 0:
            continue
        h = res["2019-2026"].iloc[i], res["NQ 2015-2025"].iloc[i], res["Jul 2025-Sep 2026"].iloc[i]
        ok = h[0].t >= 2 and h[1].t >= 2 and h[2]["$/trade"] > 0
        found |= ok
        print(f"{r.rule}: t {h[0].t:.2f} / {h[1].t:.2f}, newest ${h[2]['$/trade']:.2f}: "
              f"{'COUNTS' if ok else 'does not count'}")
    print("found" if found else "nothing counts")


if __name__ == "__main__":
    main()
