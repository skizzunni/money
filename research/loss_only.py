"""Round ninety: profit uncapped, only losses capped (the user's rule), for the first payout.

    python research/loss_only.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user: profit is uncapped, only losses. So no daily profit stop; a daily loss stop of $250, $350, $500, $800 or
none, at 4, 6, 8 or 10 MNQ (25-point cap), 2 or 3 losers, lock (0.5, +6.25) or (1.0, +2.5): 80 policies. The funded
account's first payout as round eighty-seven (research/fast_payout.py's first_payout), within 10, 20 and 40 sessions,
and busts within 40. Description: rounds eighty-seven and eighty-nine already set the bar for two weeks.
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

QS, YS, LOSERS = (4, 6, 8, 10), (250.0, 350.0, 500.0, 800.0, None), (2, 3)
LOCKS = ((0.5, 6.25), (1.0, 2.5))


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
        for q, y in itertools.product(QS, YS):
            r40 = [F.first_payout(days[s:], q, None, y, 40) for s in starts]
            paid_n = [r[1] if r[0] == "paid" else 99 for r in r40]
            rows.append({"period": label, "MNQ": q, "loss stop": y or 0, "losers": losers,
                         "lock": f"{lock[0]}/+{lock[1]}",
                         "paid in 10 %": 100 * np.mean([n <= 10 for n in paid_n]),
                         "paid in 20 %": 100 * np.mean([n <= 20 for n in paid_n]),
                         "paid in 40 %": 100 * np.mean([n <= 40 for n in paid_n]),
                         "bust in 40 %": 100 * np.mean([r[0] == "bust" for r in r40]),
                         "1st payout $": float(np.mean([r[2] for r in r40 if r[0] == "paid"] or [0.0]))})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, lz, lk) for path, per in ((nsx, idx_p), (nq, nq_p)) for lz in LOSERS for lk in LOCKS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}: top 12 by P(paid within 20 sessions)")
        d = df[df.period == label].sort_values("paid in 20 %", ascending=False).head(12)
        print(d.drop(columns="period").round(1).to_string(index=False))


if __name__ == "__main__":
    main()
