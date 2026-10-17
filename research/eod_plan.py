"""Round one hundred and seven: the strategy now (bot + breakout) on Apex's 50K EOD-trail evaluation.

    python research/eod_plan.py nsx1m_scaled.pkl nq1m_scaled.pkl

A check, not a search. The EOD-trail evaluation ($3,000 target, $2,000 drawdown set from end-of-day balances, $1,000
daily loss limit, 30 days; apex25k.attempt "eod") against the intraday trail the user trades now, with the bot at
4 MNQ, at round sixty's EOD setting (6 MNQ, $300) and at 8 MNQ ($400), and with round 105's overnight long (1 MNQ,
18:01 to the 09:30 open, stop 100) at 6. The funded account as everywhere (research/apex_payouts.pa_run).
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
import combo_more as M  # noqa: E402
import fast_payout as F  # noqa: E402
import overnight_combo as O  # noqa: E402
import trap_reversal as T  # noqa: E402

SETUPS = (("intraday", 4, False), ("eod", 4, False), ("eod", 6, False), ("eod", 8, False), ("eod", 6, True))


def job(args):
    path, periods = args
    bars = A.rth(path)
    cands = M.w_candidates(bars, False)
    sess = list(T.sessions_of(bars))
    pa_day = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    ev_bot = T.bot_trades(bars, 3, 1.0, 2.5)
    evs = {}
    for q in (4, 6, 8):
        M.BOTQ = q
        evs[q] = T.leg_paths(bars, M.combine(bars, ev_bot, cands, False)[0])
    M.BOTQ = 4
    night = O.overnight(path, 1, 100.0, delay=1)
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        starts = [s for s, d in enumerate(ss) if d <= last]
        for plan, q, nt in SETUPS:
            ev_days = P.by_day((night if nt else []) + evs[q], ss)
            pa_days = P.by_day((night if nt else []) + pa_day, ss)
            outs = [A.attempt(ev_days[s:], 1, plan, 30) for s in starts]
            memo, paid = {}, []
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = sum(x for _, x in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
                paid.append(memo[fp])
            f20 = [F.first_payout(pa_days[s:], 1, None, None, 20) for s in starts]
            r = [o for o, _ in outs]
            rows.append({"period": label, "plan": plan, "bot MNQ": q, "overnight": nt,
                         "pass %": 100 * r.count("passed") / len(r), "bust %": 100 * r.count("failed") / len(r),
                         "timeout %": 100 * r.count("timeout") / len(r),
                         "sessions to pass": float(np.median([u for o, u in outs if o == "passed"])),
                         "$ paid per eval": float(np.mean(paid)),
                         "paid in 20 %": 100 * np.mean([f[0] == "paid" for f in f20])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    print(df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
