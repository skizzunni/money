# ruff: noqa: E501
"""The MambaFx 2-minute strategy's grid on the bench (2-minute sets, zoo_days2.pkl).

    ZOO_DATA=<data dir> python research/zoo/run_sr.py <out.csv>
"""
import itertools
import os
import pickle
import sys
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import harness as H  # noqa: E402
import sr_break as M  # noqa: E402

ACC = dict(steps=((0, 1), (2000, 2), (4500, 3)), day_stop=600.0)
GRID = [dict(zip(("k", "touches", "tol", "buf", "mode", "r", "last", "cap", "max_losses"), v, strict=True))
        for v in itertools.product((3, 5), (2, 3), (0.0003, 0.0006), (0.0001, 0.0004), ("fixed", "trail", "be"), (2.0, 4.0),
                                   (690, 900), (40.0,), (2, 3))
        if not (v[4] == "trail" and v[5] == 2.0)]


def job(p):
    sets = pickle.load(open(os.path.join(os.environ["ZOO_DATA"], "zoo_days2.pkl"), "rb"))
    label = "sr " + " ".join(f"{k}={v}" for k, v in p.items())
    return H.evaluate(M.sr_break, sets, label, acc=ACC, **p)


if __name__ == "__main__":
    rows = []
    with Pool(4) as pool:
        for i, r in enumerate(pool.imap_unordered(job, GRID)):
            rows += r
            if i % 40 == 0:
                print(i, len(GRID), flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[1], index=False)
