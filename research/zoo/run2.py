# ruff: noqa: E501
"""Stage 2 (2026-11-23): the two families that held in stage 1 (the noise band, gap and go), tuned and combined on one
account, with a day stop. 1 MNQ. dev picks; unseen and live check.

    ZOO_DATA=<data dir> python research/zoo/run2.py <out.csv>
"""
import itertools
import os
import sys
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import harness as H  # noqa: E402
import strats as S  # noqa: E402

NOISE = [dict(vwap=True, trend=tr, hard=hd, vwap_stop=True, k=1.0, be_r=be, max_trades=mt, last=la)
         for tr, hd, be, mt, la in itertools.product((10, 20, 40), (200.0, 250.0, 300.0), (0.0, 0.5, 1.0), (2, 3, 9), (840, 900))]
GAP = [None, dict(k=1.0, exit_m=595, r=0.0, cap=50.0), dict(k=1.0, exit_m=595, r=0.0, cap=100.0)]
DAYSTOP = [0.0, 400.0]


def job(n):
    """One noise setting: its trades and each gap leg's once per set, combined (one position at a time, the earlier
    entry first), then each day stop."""
    sets = H.load_sets()
    out = []
    base = {name: [S.noise(days, i, SPEC_TICK, **n) for i in range(len(days))] for name, (days, _) in sets.items()}
    for g in GAP:
        gl = {name: [S.gap_go(days, i, SPEC_TICK, **g) if g else [] for i in range(len(days))] for name, (days, _) in sets.items()}
        for name, (days, sym) in sets.items():
            per_day = [S.merge(gl[name][i] + base[name][i]) for i in range(len(days))]
            t = H.trades_of(lambda days_, i, tick, pd_=per_day, **_: pd_[i], days, sym)
            for ds in DAYSTOP:
                label = f"noise tr={n['trend']} hard={n['hard']} be={n['be_r']} mt={n['max_trades']} last={n['last']} | gap={'off' if not g else g['cap']} | daystop={ds}"
                out.append({"strategy": label, **H.summary(name, t, days, day_stop=ds)})
    return out


SPEC_TICK = 0.25


if __name__ == "__main__":
    jobs = NOISE
    print(len(jobs), flush=True)
    rows = []
    with Pool(int(os.environ.get("PROCS", "4"))) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs)):
            rows += r
            if i % 20 == 0:
                print(i, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[1], index=False)
