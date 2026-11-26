"""Research (2026-11-26, docs section 177): the band and gap trades by where they enter against the overnight range
(18:00 the evening before to 09:29; zoo/overnight.py's d["on"], known before the open). Beyond: a long above the
overnight high, a short below the overnight low; inside: the rest. Each period on its own, then by year.
Run from research/: python zoo/overnight_range.py
"""
import os
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402

ON = os.path.join(os.path.dirname(B.PK), "zoo_days_on.pkl")


def pf(u):
    return u[u > 0].sum() / max(1e-9, -u[u < 0].sum())


def with_on(sets):
    on = pickle.load(open(ON, "rb"))
    for n, (d, _) in sets.items():
        m = {x["d"]: x.get("on", (np.nan, np.nan)) for x in on[n][0]}
        for x in d:
            x["on"] = m.get(x["d"], (np.nan, np.nan))
    return sets


def tag(d, t):
    by = {x["d"]: x for x in d}
    out = []
    for r in t.itertuples():
        x = by[r.d]
        hi, lo = x["on"]
        e = x["o"][r.bar]
        if hi != hi:
            out.append("n/a")
        elif (r.side > 0 and e > hi) or (r.side < 0 and e < lo):
            out.append("beyond")
        else:
            out.append("inside")
    return out


def main():
    sets = with_on(pickle.load(open(B.PK, "rb")))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["leg"] = np.where(t.bar <= 1, "gap", "band")
        t["on"] = tag(d, t)
        print(lab)
        for leg in ("band", "gap"):
            for a in ("beyond", "inside"):
                u = t[(t.leg == leg) & (t.on == a)].usd
                if len(u):
                    print(f"  {leg} {a}: {len(u)} trades, PF {pf(u):.2f}, ${u.mean():+.1f} a trade, ${u.sum():+,.0f}")
        if n in ("dev", "unseen_nq"):
            t["y"] = pd.to_datetime(t.d).dt.year
            print("  band by year, $ a trade beyond / inside (n):")
            for y, g in t[t.leg == "band"].groupby("y"):
                a, x = g[g.on == "beyond"].usd, g[g.on == "inside"].usd
                print(f"    {y}: {a.mean():+.1f} ({len(a)}) / {x.mean():+.1f} ({len(x)})")
        print(flush=True)


if __name__ == "__main__":
    main()
