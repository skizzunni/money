"""G337 (docs/NINJATRADER_V38.md): on U56, (as U57) the entry width by side (U57: 0.7 both): longs 0.65 / shorts 0.75,
0.7 / 0.8, 0.6 / 0.7, and the reverse 0.7 / 0.6. G253's measure; also the near-frozen Tests (G284b).

    SESS=10 python research/g337_side_width.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd
from g282_push import U53

CAP = {"day_cap_exit": True}
VARIANTS = {}
NFP = ",".join(pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfp_dates.csv")).date)
U56 = {**U53, **CAP, "streak_k": 4, "streak_skip": 2, "big_day_k": 1.5, "day_guard": 1200.0, "day_guard_grid": True,
       "news_dates": NFP, "news_mult": 1.5}
VARIANTS["U56"] = (U56, 1500.0, 4)
U57 = {**U56, "day_lock_at": 800.0, "day_lock_keep": 300.0}
VARIANTS = {"U57": (U57, 1500.0, 4)}
for lk, sk in ((0.65, 0.75), (0.7, 0.8), (0.6, 0.7), (0.7, 0.6)):
    VARIANTS[f"longs {lk}, shorts {sk}"] = ({**U57, "entry_k": lk, "entry_k_short": sk}, 1500.0, 4)


def job(a):
    tag, name, start = a
    settings, ds, sq = VARIANTS[tag]
    r = G.one((name, start, sq, ds, settings))
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
            d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts],
                chunksize=16) if r])
        d["stuck"] = ~d.passed & ~d.failed & (d.room < 500)
        d["failed_or_stuck"] = d.failed | d.stuck
        print(label + ":\n" + d.groupby("tag").agg(weeks=("passed", "size"), passed=("passed", "mean"),
                                                  failed=("failed", "mean"), stuck=("stuck", "mean"),
                                                  failed_or_stuck=("failed_or_stuck", "mean")).round(3).to_string(),
              flush=True)


if __name__ == "__main__":
    main()
