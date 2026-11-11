"""G284b (docs/NINJATRADER_V38.md): how U53's and U54's two-week Tests end: passed, failed, open with less than $500
above the trailing floor (near-frozen), or open with more. G253's measure on the unseen weeks (NQ 2015-25, the index
2019-26).

    SESS=10 python research/g284b_frozen.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd
from g284_defence import BASES

RUNS = {"U53": ("U53", {}), "U54": ("k296", {"sprint_low_room": 1000.0, "sprint_low_qty": 2})}


def job(a):
    tag, name, start = a
    b, extra = RUNS[tag]
    settings, ds = BASES[b]
    r = G.one((name, start, 4, ds, {**settings, **extra}))
    return None if r is None else {"tag": tag, **r}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in RUNS for n, s in conf], chunksize=16) if r])
    d.to_csv("../verification/noise_v2/g284b_frozen.csv", index=False)
    op = ~d.passed & ~d.failed
    d["ended"] = "open, $500+ above the floor"
    d.loc[op & (d.room < 500), "ended"] = "open, under $500 above the floor"
    d.loc[d.passed, "ended"], d.loc[d.failed, "ended"] = "passed", "failed"
    print(pd.crosstab(d.tag, d.ended, normalize="index").round(3).to_string())
    print(d[op].groupby("tag").room.describe().round(0).to_string(), flush=True)


if __name__ == "__main__":
    main()
