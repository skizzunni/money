"""Research (2026-11-25, docs section 115): the band trade out on a winner once the day's range is stretched.

`noise` exh_k: at a bar's close in profit, with the day's range so far at least exh_k x the 14-session average range,
a market exit filled at the next bar's open. Per period on fresh 50K starts (the shipped account rules), and the
TradingView window. Run from research/: python zoo/exhaustion_exit.py
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def score(sets, n, band):
    d, s = sets[n]
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    exits = int((t.why == "exit").sum())
    return (f"lost {np.mean([x[0] for x in r]):.1%} median ${np.median(p):,.0f} p25 ${np.percentile(p, 25):,.0f} "
            f"({exits} early exits)")


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for k in (0.0, 1.5, 1.75, 2.0, 2.5, 3.0):
        band = {"exh_k": k} if k else {}
        tv = B.line("", B.run(band=band)).split("|")[1].strip()
        print(f"exh_k {k}: 2015-19 {score(sets, 'dev', band)} | 2020-25 {score(sets, 'unseen_nq', band)} | {tv}",
              flush=True)


if __name__ == "__main__":
    main()
