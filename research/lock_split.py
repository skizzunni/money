"""Round eighty-three: the current lock in the evaluation, an earlier lock on the funded account (description).

    python research/lock_split.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round eighty-two (research/lock_apex.py) found that arming the lock at 0.5 max loss (12.5 points at 4 MNQ, $200)
instead of 1.0 raised winning trades to 57-63% and paid as much or more per evaluation in every period, but fewer
evaluations finished within 30 days. So: keep lock 1.0 / +2.5 in the evaluation (its pass rate is the current one by
construction) and change only the funded account. Candidates (funded lock_at, lock_plus): (1.0, 2.5) now, (0.5, 2.5),
(0.5, 6.25), (0.75, 2.5). These were chosen after seeing round eighty-two's numbers on every period, so this is a
description, not a test. Same machinery and measures as round eighty-two.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import lock_apex as L  # noqa: E402

PA_LOCKS = ((1.0, 2.5), (0.5, 2.5), (0.5, 6.25), (0.75, 2.5))


def job(args):
    path, periods = args
    bars = A.rth(path)
    ev_tr = L.trades_for(bars, 3, 1.0, 2.5)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    pa_trs = {lk: L.trades_for(bars, 2, *lk) for lk in PA_LOCKS}
    for label, first, last_start in periods:
        sess = [x for x in all_sess if x >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days = P.by_day(ev_tr, sess)
        outcomes = []
        for s, day in enumerate(sess):
            if day > last:
                break
            res, used = A.attempt(ev_days[s:], L.Q, "intraday", 30)
            outcomes.append((res, s + used))
        for lk, pa_tr in pa_trs.items():
            pa_days = P.by_day(pa_tr, sess)
            memo, paid, six, first_pay = {}, [], 0, []
            for res, fp in outcomes:
                if res != "passed":
                    paid.append(0.0)
                    continue
                if fp not in memo:
                    pp, end, _ = P.pa_run(pa_days[fp:], L.Q, P.CAPS["base"])
                    wk = (sess[fp + pp[0][0]] - sess[fp - 1]).days / 7 if pp else np.nan
                    memo[fp] = (sum(a for _, a in pp), end == "closed", end == "failed", wk)
                paid.append(memo[fp][0])
                six += memo[fp][1]
                first_pay.append(memo[fp][3])
            passed = [memo[fp] for res, fp in outcomes if res == "passed"]
            rows.append({"period": label, "funded lock": f"{lk[0]} / +{lk[1]}",
                         "eval pass %": 100 * len(passed) / len(outcomes),
                         "$ paid per eval": float(np.mean(paid)), "all 6 %": 100 * six / len(outcomes),
                         "funded busts %": 100 * np.mean([x[2] for x in passed]),
                         "funded winners %": 100 * np.mean([x[1] > 0 for x in pa_tr
                                                            if pd.Timestamp(first) <= x[0] <= last]),
                         "weeks to 1st payout (median)": float(np.nanmedian(first_pay))})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))


if __name__ == "__main__":
    main()
