"""Round one hundred and twenty-one: the breakout's risk on the funded account alone.

    python research/funded_w.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 101 put the breakout in the evaluation and the funded account together at $200 a trade. Payouts come only from
the funded account, whose rules differ (the threshold stops at +$100 once the peak is +$2,100; payouts after five
$200 days, a $52,600 balance and no day above half the cycle's profit). Funded-side variants, fixed before running:
no breakout, $100, $200 (now), $300 of risk a trade (1-10 MNQ); the evaluation as now. The user's intraday-trail
evaluation, then the funded account (research/combo_more.evaluate_legs).
Bar, fixed before running: adopted if, against now, payouts per evaluation are higher and the first payout within 20
sessions comes at least as often, in all three periods (2011-18, 2019-25, NQ 2015-24); the newest 13 months reported.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

RISKS = {"no breakout funded": None, "$100 funded": 100.0, "$200 funded (now)": 200.0, "$300 funded": 300.0}


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    ev_legs, ev_tr = M.combine(bars, ev_bot, M.w_candidates(bars, False), False)
    rows = []
    for name, risk in RISKS.items():
        if risk is None:
            pa_legs = M.combine(bars, pa_bot, [], False)[0]
        else:
            old = C.RISK
            C.RISK = risk
            try:
                pa_legs = M.combine(bars, pa_bot, M.w_candidates(bars, False), False)[0]
            finally:
                C.RISK = old
        rows += M.evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    cols = ["period", "setup", "eval pass %", "$ paid per eval", "paid in 20 %"]
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label][cols[1:]].round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    base = "$200 funded (now)"
    for name in RISKS:
        if name == base:
            continue
        ok = all(key.loc[(name, p)]["$ paid per eval"] > key.loc[(base, p)]["$ paid per eval"] and
                 key.loc[(name, p)]["paid in 20 %"] >= key.loc[(base, p)]["paid in 20 %"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
