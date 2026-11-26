"""Research (2026-11-26, docs section 190): docs 189's candidate. On a day whose first band trade is a short, at most
N band entries (2 / 3); also at most 2 losing band trades. Trades are one at a time, so cutting the later ones leaves
the earlier ones as they were (the day stop is applied by the account). Against: the same cap on long days, and on
random days at the short days' rate (5 draws). FOMC days skipped as shipped. By period and year (1 contract) and on the
account with the guard (shuffled years). Run from research/: python zoo/short_day_cap.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402
import near_floor_tiers as NF  # noqa: E402


def cap(t, days, n=0, losers=0):
    """Keep at most n band entries (or until `losers` losing band trades) on the given days."""
    keep = np.ones(len(t), bool)
    for day, g in t.groupby("d"):
        if day not in days:
            continue
        band = g[g.bar > 1]
        cnt = lost = 0
        for i, r in band.iterrows():
            if (n and cnt >= n) or (losers and lost >= losers):
                keep[t.index.get_loc(i)] = False
                continue
            cnt += 1
            lost += r.usd < 0
    return keep


def first_side(t):
    b = t[t.bar > 1]
    return b.groupby("d").side.first()


def run(lab, t, st, d, days, **kw):
    k, ks = cap(t, days, **kw), cap(st, days, **kw)
    tt, ss = t[k].reset_index(drop=True), st[ks].reset_index(drop=True)
    r = NF.shuffled(tt, ss, d)
    yr = (tt.groupby(pd.to_datetime(tt.d).dt.year).usd.sum() - t.groupby(pd.to_datetime(t.d).dt.year).usd.sum())
    print(f"  {lab}: {int((~k).sum())} trades cut, ${tt.usd.sum() - t.usd.sum():+,.0f} a contract; by year "
          + " ".join(f"{y}:{v:+,.0f}" for y, v in yr.items()) + "\n     shuffled: "
          + " ".join(f"${a:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for a, v in r.items()), flush=True)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t, st = F.tables(d, s, skip=True)
        fs = first_side(t)
        short, long_ = set(fs[fs < 0].index), set(fs[fs > 0].index)
        print(f"{lab}: {len(short)} short first-band days, {len(long_)} long", flush=True)
        r = NF.shuffled(t, st, d)
        print("  shipped: " + " ".join(f"${a:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for a, v in r.items()), flush=True)
        for nm, kw in (("at most 2 band entries", dict(n=2)), ("at most 3 band entries", dict(n=3)),
                       ("at most 2 losing band trades", dict(losers=2))):
            run(f"short days, {nm}", t, st, d, short, **kw)
            run(f"long days, {nm}", t, st, d, long_, **kw)
        days = np.array(sorted(set(fs.index)), dtype=object)
        rng = np.random.default_rng(4)
        for k in range(3):
            pick = set(rng.choice(days, len(short), replace=False))
            run(f"placebo {k + 1}: random days at the short rate, at most 2 band entries", t, st, d, pick, n=2)


if __name__ == "__main__":
    main()
