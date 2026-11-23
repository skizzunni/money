# ruff: noqa: E501
"""Stage 1 of the strategy search (2026-11-23): every family on its grid, 1 MNQ / 1 MES, on dev / unseen / live.

    ZOO_DATA=<data dir> python research/zoo/run1.py <out.csv>
"""
import itertools
import os
import sys
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def grid(**kw):
    keys = list(kw)
    return [dict(zip(keys, v)) for v in itertools.product(*kw.values())]


GRIDS = {
    "noise": grid(vwap=[True], trend=[0, 20], hard=[150.0, 250.0], vwap_stop=[False, True], k=[1.0, 1.25], be_r=[0.0, 0.5]),
    "orb": grid(n=[5, 15, 30, 60], stop=["far", "mid"], r=[0.0, 1.0, 2.0], cap=[40.0, 80.0]),
    "gap_fade": grid(k=[0.5, 1.0, 1.5], stop_mult=[0.5, 1.0], exit_m=[655, 775, 955], fill=[0.5, 1.0]),
    "gap_go": grid(k=[0.5, 1.0], exit_m=[655, 955], r=[0.0, 1.0, 2.0], cap=[50.0, 100.0]),
    "vwap_rev": grid(k=[1.5, 2.0, 2.5], ks=[3.0, 4.0], trend_only=[False, True], max_trades=[1, 3]),
    "rsi2": grid(lo_th=[5.0, 10.0], stop_pts=[25.0, 50.0], exit_rsi=[50.0, 70.0], max_trades=[2, 5]),
    "imom": grid(sig_end=[600, 930], enter=[930], stop_pts=[40.0, 1000.0], from_close=[True, False], min_move=[0.0, 0.002]),
    "pdhl": grid(mode=["break", "fade"], stop_pts=[25.0, 50.0], r=[0.0, 1.0, 2.0], first=[575, 600]),
    "ema_vwap": grid(f=[9], s=[21, 34], stop_pts=[25.0, 50.0], max_trades=[1, 3]),
    "drive": grid(n=[15, 30], top=[0.7, 0.85], stop=["low", "mid"], r=[0.0, 1.0, 2.0], cap=[60.0, 120.0]),
    "squeeze": grid(n=[20], kb=[2.0, 2.5], stop_pts=[30.0, 60.0]),
}


def job(a):
    fam, p = a
    sets = H.load_sets()
    label = fam + " " + " ".join(f"{k}={v}" for k, v in p.items())
    try:
        return H.evaluate(getattr(S, fam), sets, label, **p)
    except Exception as e:  # noqa: BLE001
        return [{"strategy": label, "set": "error", "err": repr(e)}]


if __name__ == "__main__":
    jobs = [(f, p) for f, g in GRIDS.items() for p in g]
    print(len(jobs), "variants", flush=True)
    rows = []
    with Pool(int(os.environ.get("PROCS", "4"))) as pool:
        for n, r in enumerate(pool.imap_unordered(job, jobs)):
            rows += r
            if n % 20 == 0:
                print(n, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[1], index=False)
