"""G290 (docs/NINJATRADER_V38.md): on U55 (U53's Test sprint with G289b's $1,500 day cap that also closes the open
trade): the cap at $1,700 or $2,000, and G277's k296 settings with the $1,500 cap. G253's measure; also the Tests that
end open with less than $500 above the floor (G284b).

    SESS=10 python research/g290_cap_more.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
from g282_push import U53
from g284_defence import K296

CAP = {"day_cap_exit": True}
VARIANTS = {"U55": ({**U53, **CAP}, 1500.0), "cap $1,700": ({**U53, **CAP}, 1700.0),
            "cap $2,000": ({**U53, **CAP}, 2000.0), "k296, cap $1,500": ({**K296, **CAP}, 1500.0)}


def job(a):
    tag, name, start = a
    settings, ds = VARIANTS[tag]
    r = G.one((name, start, 4, ds, settings))
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
        d["stuck"] = ~d.passed & ~d.failed & (d.room < 500)
        d["failed_or_stuck"] = d.failed | d.stuck
        print(label + ":\n" + d.groupby("tag").agg(weeks=("passed", "size"), passed=("passed", "mean"),
                                                  failed=("failed", "mean"), stuck=("stuck", "mean"),
                                                  failed_or_stuck=("failed_or_stuck", "mean")).round(3).to_string(),
              flush=True)


if __name__ == "__main__":
    main()
