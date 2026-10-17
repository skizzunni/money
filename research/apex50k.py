"""Round sixty: the max loss, contracts and daily loser limit for an Apex 50K evaluation.

    python research/apex50k.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user moved back from 25K to 50K evaluations. Same simulation as research/apex25k.py (round fifty-nine), with the
Apex 50K evaluation (4.0, March 2026) as 2026 reviews quote it (Apex's site refuses this machine): $3,000 profit
target, $2,000 trailing drawdown, 30 calendar days, no minimum days, up to 60 MNQ; the end-of-day plan has a $1,000
daily loss limit that closes the position and stops trading for the day (not a fail); the intraday plan has none.

Candidates, fixed before running (contracts, max loss a trade): 3 MNQ at $350 (the evaluation setting before the 25K
change), $250 and $200 (the 25K setting); 4, 5 and 6 MNQ at $350; the tested 17.5-point cap at 5, 6, 8, 10, 12 and
15 MNQ ($175 - $525); a 25-point cap at 4, 6 and 8 MNQ ($200 - $400). Each with no new entries after 1, 2, 3 or 4
losers. Pass bar, fixed before running, for each plan: the variant with the highest 30-day pass rate on 2011-2018
must beat 3 MNQ, $350, 4 losers by at least 5 points of pass rate, with a bust rate no higher, on 2019 - Sep 2026 and
on the NQ futures 2015 - July 2025. If none does, the evaluation goes back to 3 MNQ, $350, 4 losers.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30  # set before the workers fork, so they see it
COMBOS = [(3, 175 / 3), (3, 125 / 3), (3, 100 / 3), (4, 43.75), (5, 35.0), (6, 175 / 6),
          (5, 17.5), (6, 17.5), (8, 17.5), (10, 17.5), (12, 17.5), (15, 17.5), (4, 25.0), (6, 25.0), (8, 25.0)]
RENAME = {"day <= -500 %": "day <= -1000 %", "day <= -1000 %": "day <= -2000 %"}  # A.worst_days uses DLL and DD


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=4) as pool:
        idx = A.table(nsx, (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026)), COMBOS, pool)
        fut = A.table(nq, (("NQ 2015-2025", 2015, 2025),), COMBOS, pool)
    allr = pd.concat([idx, fut]).rename(columns=RENAME)
    cols = [RENAME.get(c, c) for c in A.COLS]
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        d = allr[allr.period == label]
        print(f"\n{label}, sorted by the end-of-day plan's 30-day pass rate")
        print(d.sort_values("eod pass %", ascending=False)[cols].round(1).to_string(index=False))
    for plan in ("intraday", "eod"):
        disc = allr[allr.period == "2011-2018"]
        best = disc.sort_values(f"{plan} pass %", ascending=False).iloc[0]
        key = (best.MNQ, best["max loss $"], best.losers)
        print(f"\n{plan} plan: best on 2011-2018 is {key[0]} MNQ, ${key[1]}, {key[2]} losers "
              f"({best[f'{plan} pass %']:.1f}% pass)")
        ok = True
        for label in ("2019-2026", "NQ 2015-2025"):
            d = allr[allr.period == label]
            b = d[(d.MNQ == key[0]) & (d["max loss $"] == key[1]) & (d.losers == key[2])].iloc[0]
            c = d[A.is_current(d)].iloc[0]
            good = b[f"{plan} pass %"] >= c[f"{plan} pass %"] + 5 and b[f"{plan} bust %"] <= c[f"{plan} bust %"]
            ok &= good
            print(f"  {label}: {b[f'{plan} pass %']:.1f}% pass / {b[f'{plan} bust %']:.1f}% bust against 3 MNQ, $350, "
                  f"4 losers {c[f'{plan} pass %']:.1f}% / {c[f'{plan} bust %']:.1f}%: {'PASS' if good else 'FAIL'}")
        print(f"  {plan} plan: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
