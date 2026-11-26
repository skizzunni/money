"""Research (2026-11-26, docs section 176): the band trades by the pre-open move (08:29 close to 09:29 close, the
last price before the 08:30 releases to the last before the cash open; research/zoo/news.py's d["news"][2]), on
every day, not only news days. Agree: the trade's side is the pre-open move's way; against: the other way; flat: the
move under `flat` x the 14-session sigma of the first check (a quiet pre-open). Each period on its own, then by year.
Run from research/: python zoo/preopen_align.py
"""
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


def pf(u):
    return u[u > 0].sum() / max(1e-9, -u[u < 0].sum())


def tag(d, t, flat=0.1):
    mv = {x["d"]: x["news"][2] / x["c"][0] if x["news"][2] == x["news"][2] else np.nan for x in d}
    rng = {}
    for i, x in enumerate(d):  # the 14-session mean daily range as a fraction, for "flat"
        if i >= 14:
            rng[x["d"]] = np.mean([(np.max(y["h"]) - np.min(y["l"])) / y["c"][-1] for y in d[i - 14:i]])
    out = []
    for r in t.itertuples():
        m, g = mv.get(r.d, np.nan), rng.get(r.d, np.nan)
        if m != m or g != g:
            out.append("n/a")
        elif abs(m) < flat * g:
            out.append("flat")
        else:
            out.append("agree" if np.sign(m) == r.side else "against")
    return out


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["leg"] = np.where(t.bar <= 1, "gap", "band")
        for flat in (0.0, 0.1):
            t["al"] = tag(d, t, flat)
            print(f"{lab} (flat under {flat} x the range):")
            for leg in ("band", "gap"):
                for a in ("agree", "against", "flat"):
                    u = t[(t.leg == leg) & (t.al == a)].usd
                    if len(u):
                        print(f"  {leg} {a}: {len(u)} trades, PF {pf(u):.2f}, ${u.mean():+.1f} a trade, ${u.sum():+,.0f}")
        if n in ("dev", "unseen_nq"):
            t["al"] = tag(d, t, 0.0)
            t["y"] = pd.to_datetime(t.d).dt.year
            b = t[t.leg == "band"]
            print(f"  {lab} band by year, $ a trade agree / against (n):")
            for y, g in b.groupby("y"):
                a, x = g[g.al == "agree"].usd, g[g.al == "against"].usd
                print(f"    {y}: {a.mean():+.1f} ({len(a)}) / {x.mean():+.1f} ({len(x)})")
        print(flush=True)


if __name__ == "__main__":
    main()
