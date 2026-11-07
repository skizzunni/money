"""G283 (docs/NINJATRADER_V38.md): U53's Test sprint sized from a fixed dollar risk on each trade's own stop
(risk_per_trade $300 / $450 / $600, at most 6 or 8 MNQ) instead of a flat 4 MNQ (the gap trade stays at 2; the floor's
and the day's room still cut it). Measured as G253 (10 sessions, TPT's Test rules) on its development weeks (the index 2011-18) and
its unseen weeks (NQ 2015-25, the index 2019-26).

    SESS=10 python research/g283_risk_size.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
from g271_day_stop import K317

U53 = {**K317, "sprint_target": 5000.0, "sprint_gap_qty": 2, "gap_go_be": 0.0}
VARIANTS = {"U53": {}}
for r in (300.0, 450.0, 600.0):
    for q in (6, 8):
        VARIANTS[f"risk ${r:,.0f} up to {q}"] = {"risk_per_trade": r, "risk_max_qty": q}


def job(a):
    tag, name, start = a
    r = G.one((name, start, 4, 1100.0, {**U53, **VARIANTS[tag]}))
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
