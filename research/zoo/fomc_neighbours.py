"""Research (2026-11-26, docs section 183): the trading days next to an FOMC statement day (180 skips the day itself):
the day before (the market waiting) and the day after (the digestion). Each set's trades against the rest, by period
and by year; no trading on them on the account with the guard, against a placebo of as many random days.
Run from research/: python zoo/fomc_neighbours.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402
import ism_days as I  # noqa: E402

FOMC = set(F.FOMC)


def neighbours(d, step):
    days = [x["d"] for x in d]
    pos = {x: i for i, x in enumerate(days)}
    return {days[pos[f] + step] for f in FOMC if f in pos and 0 <= pos[f] + step < len(days)}


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        for nm, step in (("the day before", -1), ("the day after", 1)):
            ev = neighbours(d, step)
            F.FOMC = ev
            t, st = F.tables(d, s)
            f = t.d.isin(ev)
            print(f"{lab}, {nm} an FOMC day: {len(ev)} days")
            for nm2, m in (("those days", f), ("other days", ~f)):
                u = t[m].usd
                print(f"  {nm2}: {len(u)} trades, PF {F.pf(u):.2f}, ${u.mean():+.1f} a trade, ${u.sum():+,.0f}")
            if n in ("dev", "unseen_nq"):
                yr = pd.to_datetime(t.d).dt.year
                print("  by year, $ (trades): " + ", ".join(
                    f"{y} {t[f & (yr == y)].usd.sum():+,.0f} ({int((f & (yr == y)).sum())})" for y in sorted(set(yr))))
                I.acct("shipped", t, st, d)
                I.acct(f"no trading {nm}", *F.tables(d, s, skip=True), d)
                days = np.array([x["d"] for x in d], dtype=object)
                rng = np.random.default_rng(5)
                for k in range(3):
                    sk = set(rng.choice(days, len(ev), replace=False))
                    I.acct(f"placebo {k + 1}: as many random days", t[~t.d.isin(sk)].reset_index(drop=True),
                           st[~st.d.isin(sk)].reset_index(drop=True), d)
            print(flush=True)
        F.FOMC = FOMC


if __name__ == "__main__":
    main()
