# ruff: noqa: E501
"""Stage 3 (2026-11-23): account protection on stage 2's best candidates. The failure stage 2 leaves is the 2020 regime
(every NQ start Jan-Nov 2020 lost at 1 MNQ). Dev (2015-19) loses no account, so it cannot pick a protection; the
protections are therefore picked on dev + unseen NQ pooled (stated, not hidden) and checked on ES and on the live MNQ
months, and a protection is kept only if it does not lower dev's median by more than 10%.
Grid: strategy-equity filter (sit out when its own last eq_n sessions at 1 contract are below eq_min), trades a day while
the cushion is small (early_max until early_cushion), contracts by profit (steps, at most 3: the user's cap).
Rule: the fewest pooled lost; ties: the higher pooled median.

    ZOO_DATA=<data dir> python research/zoo/run3.py <stage2.csv> <out.csv>
"""
import itertools
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import harness as H  # noqa: E402
import strats as S  # noqa: E402

EQ = [(0, 0.0), (10, 0.0), (20, 0.0), (40, 0.0), (20, -300.0)]
EARLY = [(0, 0.0), (1, 750.0), (1, 1500.0), (2, 1500.0)]
STEPS = [(), ((0, 1), (2000, 2), (4500, 3)), ((0, 1), (3000, 2), (6000, 3))]
DS = [0.0, 400.0]


def parse(label):
    n, g, ds = [x.strip() for x in label.split("|")]
    kv = dict(x.split("=") for x in n.split()[1:])
    noise = dict(vwap=True, trend=int(kv["tr"]), hard=float(kv["hard"]), vwap_stop=True, k=1.0, be_r=float(kv["be"]),
                 max_trades=int(kv["mt"]), last=int(kv["last"]))
    gv = g.split("=")[1]
    legs = ([("gap_go", dict(k=1.0, exit_m=595, r=0.0, cap=float(gv)))] if gv != "off" else []) + [("noise", noise)]
    return legs, float(ds.split("=")[1])


def job(label):
    """One candidate: its trades once per set, then every protection on them."""
    legs, _ = parse(label)
    sets = H.load_sets()
    tr = {name: (H.trades_of(S.combo, days, sym, legs=legs), days) for name, (days, sym) in sets.items()}
    out = []
    for eq, early, steps, ds in itertools.product(EQ, EARLY, STEPS, DS):
        acc = dict(day_stop=ds, eq_n=eq[0], eq_min=eq[1], early_max=early[0], early_cushion=early[1], steps=steps)
        tag = f"{label} || eq={eq} early={early} steps={'none' if not steps else steps[1][0]} ds={ds}"
        pooled = []
        for name, (t, days) in tr.items():
            out.append({"strategy": tag, **H.summary(name, t, days, **acc)})
            if name in ("dev", "unseen_nq"):
                pooled += H.account(t, days, **acc)
        lost = np.array([x[0] for x in pooled])
        prof = np.array([x[1] for x in pooled])
        out.append({"strategy": tag, "set": "pooled", "starts": len(pooled), "lost": round(float(lost.mean()), 3),
                    "median_12m": round(float(np.median(prof))), "reach_25k": round(float((prof >= 25000).mean()), 3),
                    "green_days": round(float(np.sum([x[2] for x in pooled]) / max(1, np.sum([x[3] for x in pooled]))), 3)})
    return out


if __name__ == "__main__":
    s2 = pd.read_csv(sys.argv[1])
    w = s2.pivot_table(index="strategy", columns="set", values=["lost", "median_12m"], aggfunc="first")
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    w["pool_lost"] = w.lost_dev * 49 / 104 + w.lost_unseen_nq * 55 / 104
    top = w.sort_values(["pool_lost", "median_12m_dev"], ascending=[True, False]).head(4).index.tolist()
    top += w[w.lost_dev == 0].sort_values("median_12m_dev", ascending=False).head(2).index.tolist()
    top = list(dict.fromkeys(top))
    print("candidates:", *top, sep="\n  ", flush=True)
    jobs = top
    rows = []
    with Pool(int(os.environ.get("PROCS", "4"))) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs)):
            rows += r
            if i % 50 == 0:
                print(i, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[2], index=False)
