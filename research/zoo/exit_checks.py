"""Research (2026-11-25, docs section 116): checks that only manage the band trade (exits, never entries).

`noise` exit_checks: extra check times (bar ends, minutes) where an open band trade's stop moves to the band (the
VWAP, the hard stop) and a close at or past it exits at the next bar's open, but no entry. The shipped checks are
10:00-15:00 every 30 minutes; after 15:00 the stop holds until the 15:55 exit. Per period on fresh 50K starts (the
shipped account rules), and the TradingView window. Run from research/: python zoo/exit_checks.py
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
    rows = (("shipped", ()), ("15:30", (930,)), ("15:15 15:30 15:45", (915, 930, 945)),
            ("every 15 min from 12:00", tuple(range(735, 900, 30)) + (915, 930, 945)),
            ("every 15 min from 10:00", tuple(range(615, 900, 30)) + (915, 930, 945)),
            ("every 15 min 10:00-15:00", tuple(range(615, 900, 30))))
    for lab, ex in rows:
        band = {"exit_checks": ex} if ex else {}
        tv = B.line("", B.run(band=band)).split("|")[1].strip()
        print(f"{lab}: 2015-19 {score(sets, 'dev', band)} | 2020-25 {score(sets, 'unseen_nq', band)} | {tv}",
              flush=True)


if __name__ == "__main__":
    main()
