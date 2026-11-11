"""G261b (docs/NINJATRADER_V38.md): G261's five lowest-failure combinations of stage 1 (passed at least 10%, failed at
most 10% on the index 2011-18) on G257's stage-2 weeks (NQ 2015-25, the index 2019-26), never seen in their selection.

    SESS=10 python research/g261b_low_fail.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g261_test_search as G5
import pandas as pd

PICK = [250, 88, 178, 103, 290]
G5.ROWS = "verification/noise_v2/g261b_rows.jsonl"


def main() -> None:
    G = G5.G
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        s2 = G5.score(G5.run_saved(ex, [(k, n, s) for k in PICK for n, s in conf], 2))
    s2 = s2.join(pd.Series({k: json.dumps(G5.VARIANTS[k]) for k in s2.index}, name="settings"))
    s2.to_csv("verification/noise_v2/g261b_stage2.csv")
    print(s2.sort_values("failed").round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
