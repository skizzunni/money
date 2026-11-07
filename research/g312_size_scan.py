"""G312 (docs/NINJATRADER_V38.md): U55's Test sprint at 4, 5, 6 and 8 MNQ, with or without G305's $1,000 day guard. A
measurement for the user's rule "size up as long as the account is up and not dead": the share of two-week Tests that
pass, fail, end up and alive (profit above zero, not failed), and the median two weeks, on all Monday starts (NQ 2015-25,
the index 2011-26).

    SESS=10 python research/g312_size_scan.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
from g282_push import U53

CAP = {"day_cap_exit": True}
VARIANTS = {}
for q in (4, 5, 6, 8):
    VARIANTS[f"{q} MNQ"] = ({**U53, **CAP}, q)
    VARIANTS[f"{q} MNQ, guard $1,000"] = ({**U53, **CAP, "day_guard": 1000.0}, q)


def job(a):
    tag, name, start = a
    settings, sq = VARIANTS[tag]
    r = G.one((name, start, sq, 1500.0, settings))
    return None if r is None else {"tag": tag, **r}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    starts = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    starts += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2026-08-31", freq="W-MON")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts], chunksize=16) if r])
    d.to_csv("../verification/noise_v2/g312_size_scan.csv", index=False)
    d["up_alive"] = (d.net > 0) & ~d.failed
    print(d.groupby("tag", sort=False).agg(weeks=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"),
                                           up_and_alive=("up_alive", "mean"), median_net=("net", "median"))
          .round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
