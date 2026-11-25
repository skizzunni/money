"""Research (2026-11-25, docs section 114): the opening half hour's volume and the band trades, each period on its own.

rv = the 09:30-10:00 volume (the six 5-minute bars, complete at the band's first check at 10:00) against the mean of
the same over the 14 sessions before. The shipped band trades (1 contract, $ a trade) by rv tercile (cut on each
period's own trades, and on fixed cuts 0.8 / 1.2), and the gap trade for reference, per set.
Run from research/: python zoo/open_volume.py
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


def pf(s):
    return s[s > 0].sum() / -s[s < 0].sum() if (s < 0).any() else np.inf


def rel_vol(d):
    v = np.array([x["v"][(x["mm"] >= 570) & (x["mm"] < 600)].sum() for x in d])
    return {d[i]["d"]: v[i] / v[i - 14:i].mean() for i in range(14, len(d)) if v[i - 14:i].mean() > 0}


def bar0_vol(d):
    v = np.array([x["v"][x["mm"] == 570].sum() for x in d])  # the 09:30 bar alone: known at the gap trade's 09:35 entry
    return {d[i]["d"]: v[i] / v[i - 14:i].mean() for i in range(14, len(d)) if v[i - 14:i].mean() > 0}


def cells(u, by):
    return " | ".join(f"{k}: {len(v)} tr ${v.mean():.1f} PF {pf(v):.2f}" for k, v in u.groupby(by, observed=True))


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["rv"] = t.d.map(rel_vol(d))
        t = t.dropna(subset=["rv"])
        band = t[t.bar > 1].copy()
        band["q"] = pd.qcut(band.rv, 3, labels=["low", "mid", "high"])
        band["f"] = pd.cut(band.rv, [0, 0.8, 1.2, 99], labels=["<0.8", "0.8-1.2", ">1.2"])
        print(f"{lab}: band {len(band)} trades PF {pf(band.usd):.2f}; terciles cut at "
              f"{band.rv.quantile([1 / 3, 2 / 3]).round(2).tolist()}")
        for col in ("q", "f"):
            g = band.groupby(col, observed=True).usd
            print("   " + " | ".join(f"{k}: {len(v)} tr ${v.mean():.1f} PF {pf(v):.2f}" for k, v in g))
        gap = t[t.bar <= 1].copy()
        gq = pd.cut(gap.rv, [0, 0.8, 1.2, 99], labels=["<0.8", "0.8-1.2", ">1.2"])
        print("   gap trade by 09:30-10:00 volume (hindsight: the trade is in 09:35-09:55): "
              + cells(gap.usd, gq))
        gap["v0"] = gap.d.map(bar0_vol(d))
        for cuts in ([0, 0.8, 1.2, 99], [0, 1.0, 1.5, 99]):
            gq = pd.cut(gap.v0, cuts, labels=[f"<{cuts[1]}", f"{cuts[1]}-{cuts[2]}", f">{cuts[2]}"])
            print("   gap trade by the 09:30 bar's volume (known at entry): "
                  + cells(gap.usd, gq),
                  flush=True)


if __name__ == "__main__":
    main()
