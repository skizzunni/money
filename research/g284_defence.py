"""G284 (docs/NINJATRADER_V38.md): the Test sprint's defence: with less than $1,000 or $1,500 above the trailing floor,
the sprint takes 1 or 2 MNQ instead of 4 (the gap trade stays at 2), on U53 and on G277's k296 (13.8% passed / 10.6%
failed unseen). Measured as G253 (10 sessions, TPT's Test rules) on its development weeks (the index 2011-18) and its
unseen weeks (NQ 2015-25, the index 2019-26).

    SESS=10 python research/g284_defence.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
import g277_test_search as G7
from g282_push import U53

K296 = dict(G7.VARIANTS[296])
K296_DS = K296.pop("day stop")
K296.pop("sprint")
K296 = {**K296, **G7.FIXED}
BASES = {"U53": (U53, 1100.0), "k296": (K296, K296_DS)}
VARIANTS = {}
for b in BASES:
    VARIANTS[b] = (b, {})
    for room in (1000.0, 1500.0):
        for q in (1, 2):
            VARIANTS[f"{b}, {q} MNQ under ${room:,.0f}"] = (b, {"sprint_low_room": room, "sprint_low_qty": q})


def job(a):
    tag, name, start = a
    b, extra = VARIANTS[tag]
    settings, ds = BASES[b]
    r = G.one((name, start, 4, ds, {**settings, **extra}))
    return None if r is None else {"tag": tag, **r}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    for label, starts in (("development (index 2011-18)", dev), ("unseen (NQ 2015-25 + index 2019-26)", conf)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts], chunksize=16) if r])
        print(label + ":\n" + d.groupby("tag").agg(weeks=("passed", "size"), passed=("passed", "mean"),
                                                  failed=("failed", "mean")).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
