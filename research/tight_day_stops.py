"""Round eighty-nine: tight daily loss stops for the two-week first payout.

    python research/tight_day_stops.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round eighty-seven tested daily loss stops of $500, $800 or none. Red days are a third of all days (round
eighty-seven), so a TIGHT daily loss stop could keep the account alive through more of them while the profit stop
banks the green days. Policies, fixed before running: 6, 8 or 10 MNQ (25-point cap) x daily loss stop $250 or $350 x
daily profit stop $500, $650 or $800 x 2 or 3 losers x lock (0.5, +6.25) or (1.0, +2.5): 72. Same simulation as round
eighty-seven (research/fast_payout.py's first_payout).
Pick and bar, fixed before running: the 2011-18 policy with the highest P(paid within 10 sessions); adopted only if on
2019-25 and NQ futures it beats round eighty-seven's pick (6.5% and 5.5%) and pays within 10 sessions more often than it
busts within 10.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import fast_payout as F  # noqa: E402
import lock_apex as L  # noqa: E402

QS, YS, XS, LOSERS = (6, 8, 10), (250.0, 350.0), (500.0, 650.0, 800.0), (2, 3)
LOCKS = ((0.5, 6.25), (1.0, 2.5))
R87 = {"2019-2025": 6.5, "NQ 2015-2024": 5.5}


def job(args):
    path, periods, losers, lock = args
    bars = A.rth(path)
    tr = L.trades_for(bars, losers, *lock)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [d for d in all_sess if d >= pd.Timestamp(first)]
        days = P.by_day(tr, sess)
        starts = [s for s, d in enumerate(sess) if d <= pd.Timestamp(last_start)]
        for q, x, y in itertools.product(QS, XS, YS):
            r10 = [F.first_payout(days[s:], q, x, y, 10) for s in starts]
            r20 = [F.first_payout(days[s:], q, x, y, 20) for s in starts]
            rows.append({"period": label, "MNQ": q, "profit stop": x, "loss stop": y, "losers": losers,
                         "lock": f"{lock[0]}/+{lock[1]}",
                         "paid in 10 %": 100 * np.mean([r[0] == "paid" for r in r10]),
                         "bust in 10 %": 100 * np.mean([r[0] == "bust" for r in r10]),
                         "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in r20]),
                         "bust in 20 %": 100 * np.mean([r[0] == "bust" for r in r20])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, lz, lk) for path, per in ((nsx, idx_p), (nq, nq_p)) for lz in LOSERS for lk in LOCKS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    key = ["MNQ", "profit stop", "loss stop", "losers", "lock"]
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}: top 10 by P(paid within 10 sessions)")
        d = df[df.period == label].sort_values("paid in 10 %", ascending=False).head(10)
        print(d.drop(columns="period").round(1).to_string(index=False))
    pick = df[df.period == "2011-2018"].sort_values("paid in 10 %", ascending=False).iloc[0]
    sel = {k: pick[k] for k in key}
    print(f"\npick on 2011-18: {sel} ({pick['paid in 10 %']:.1f}% paid within 10)")
    ok = True
    for label, bar in R87.items():
        d = df[df.period == label]
        b = d[np.logical_and.reduce([d[k] == v for k, v in sel.items()])].iloc[0]
        good = b["paid in 10 %"] > bar and b["paid in 10 %"] > b["bust in 10 %"]
        ok &= good
        print(f"  {label}: paid in 10 {b['paid in 10 %']:.1f}% (bust {b['bust in 10 %']:.1f}%), round 87 {bar}%: "
              f"{'PASS' if good else 'FAIL'}")
    print(f"  {'ADOPT' if ok else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
