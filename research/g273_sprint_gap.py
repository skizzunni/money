"""G273 (docs/NINJATRADER_V38.md): U51's Test sprint with the gap trade at 2, 6 or 8 MNQ.
Measured as G253 (10 sessions, TPT's Test rules) on its development weeks (the index 2011-18) and its unseen weeks (NQ
2015-25, the index 2019-26).

    SESS=10 python research/g273_sprint_gap.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd

K317 = {"lookback": 18, "entry_k": 0.7, "range_pos_min": 0.7, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2,
        "skip_checks": "", "max_losers": 3, "time_stop": 30, "trend_n": 0, "big_day_k": 0.0, "stop_buffer": 0.24,
        "lock_plus": 2.5, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go_k": 0.5}
VARIANTS = {"U51 (gap at 4)": 0, "gap at 2": 2, "gap at 6": 6, "gap at 8": 8}


def job(a):
    tag, name, start = a
    r = G.one((name, start, 4, 1100.0, {**K317, "sprint_target": 5000.0, "sprint_gap_qty": VARIANTS[tag]}))
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
        print(label + ":\n" + d.groupby("tag").agg(weeks=("passed", "size"), passed=("passed", "mean"),
                                                  failed=("failed", "mean")).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
