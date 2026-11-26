"""Research (2026-11-26, docs section 182): the shipped MNQ trades on ISM manufacturing days (10:00 New York, the
first business day of February-December by rule: research/ism_dates.csv, research/news_days.py; the real calendar
moves a few releases a day or two). The 10:00 check fires as the number comes out. Trades on ISM days against the
rest (the 10:00 entry apart), by period and by year; no trading on ISM days and no 10:00 entry on ISM days on the
account with the guard (fomc_days.tables with the ISM set); a placebo of as many random days.
Run from research/: python zoo/ism_days.py
"""
import os
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bad_runs as BR  # noqa: E402
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402
import near_floor_tiers as NF  # noqa: E402

ISM = set(pd.to_datetime(pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "ism_dates.csv")).date).dt.date)


def acct(lab, t, st, d):
    cal = []
    for start in NF.STARTS:
        r = BR.runs(t, d, B.STEPS, 600.0, B._news(d), strong=st, guard=1500.0, strong_below=1000.0, start=start)
        cal.append(f"${start:,.0f} {r.lost.mean():.1%} / ${r.profit.median():,.0f}")
    sh = " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in NF.shuffled(t, st, d).items())
    print(f"  {lab}: {len(t)} trades, ${t.usd.sum():+,.0f} a contract\n     calendar: {' | '.join(cal)}"
          f"\n     shuffled years: {sh}", flush=True)


def main():
    F.FOMC = ISM  # fomc_days.tables reads its module's FOMC set
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t, st = F.tables(d, s)
        f = t.d.isin(ISM)
        ten = t.bar == (600 - 570) // 5
        print(f"{lab}: {sum(x['d'] in ISM for x in d)} ISM days of {len(d)}")
        for nm, m in (("ISM days", f), ("other days", ~f), ("ISM days, the 10:00 entry", f & ten),
                      ("other days, the 10:00 entry", ~f & ten), ("ISM days, later entries", f & ~ten & (t.bar > 1))):
            u = t[m].usd
            if len(u):
                print(f"  {nm}: {len(u)} trades, PF {F.pf(u):.2f}, ${u.mean():+.1f} a trade, ${u.sum():+,.0f}")
        if n in ("dev", "unseen_nq"):
            yr = pd.to_datetime(t.d).dt.year
            print("  ISM days by year, $ (trades): " + ", ".join(
                f"{y} {t[f & (yr == y)].usd.sum():+,.0f} ({int((f & (yr == y)).sum())})" for y in sorted(set(yr))))
            acct("shipped", t, st, d)
            acct("no trading on ISM days", *F.tables(d, s, skip=True), d)
            acct("ISM days: no 10:00 entry", *F.tables(d, s, band_fomc=dict(check_off=30)), d)
            days = np.array([x["d"] for x in d], dtype=object)
            rng = np.random.default_rng(5)
            for k in range(3):
                sk = set(rng.choice(days, sum(x["d"] in ISM for x in d), replace=False))
                acct(f"placebo {k + 1}: no trading on as many random days", t[~t.d.isin(sk)].reset_index(drop=True),
                     st[~st.d.isin(sk)].reset_index(drop=True), d)
        print(flush=True)


if __name__ == "__main__":
    main()
