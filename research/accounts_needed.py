"""Round one hundred and thirty-two: what one account slot pays a week, and how many it takes for $1,500 a week.

    python research/accounts_needed.py nsx1m_scaled.pkl nq1m_scaled.pkl [sessions, default 130]

Every result so far is per evaluation bought. The user's goal is money per week. An "account slot" is how a trader
actually runs it: buy an evaluation; if it fails or times out, buy the next one the next session; once passed, trade
the funded account until it busts or pays its sixth payout, then buy the next evaluation. Measured over 26 weeks (130
sessions) from every start session, on the strategy now (bot + breakout, close-at-target in the evaluation, the funded
settings; research/pass_lock and research/apex_payouts), with and without the funded payout stop (round 128):
  $ a week per slot     the payouts in the 26 weeks / 26
  break-even eval fee   the evaluation price at which the slot's payouts just cover its evaluations and the $79
                        activation of each funded account
  evaluations a slot    bought in the 26 weeks (each is a month's fee)
  paid at all %         slots with at least one payout in the 26 weeks
Copied accounts take the same trades, so N copies started together pay exactly N times one slot: the expected weekly
amount scales with N but the spread does not shrink (the chance of a bad 26 weeks is the same for 1 or 10).
Also, before running: the bound one account sets. A day's P/L with mean m and spread s against a $2,000 drawdown
fails with probability about exp(-2 m 2000 / s^2) (a random walk with drift reaching a barrier). The measured daily
mean and spread of the funded strategy, and the mean it would need at that spread, are printed.
No adoption bar: this measures, it changes nothing in the strategy.
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
import pass_lock as PL  # noqa: E402
import payout_lock as PO  # noqa: E402
import trap_reversal as T  # noqa: E402

HORIZON = int(sys.argv[3]) if len(sys.argv) > 3 else 130  # sessions: 26 weeks (or as given)
WEEKS = HORIZON / 5
ACTIVATION = 79.0  # $ per funded account (third-party, 2026; intraday)
GOAL = 1500.0


def slot(ev_days, pa_days, s, lock):
    """One account slot from session s for HORIZON sessions: (payouts $, evaluations bought, funded accounts)."""
    t, end, total, evals, funded = s, s + HORIZON, 0.0, 0, 0
    while t < end:
        evals += 1
        res, used = PL.attempt(ev_days[t:end], True)
        if res != "passed":
            t += max(used, 1)
            continue
        funded += 1
        fp = t + used
        paid, status, n = PO.pa_lock(pa_days[fp:end], P.CAPS["base"], lock)
        total += sum(a for _, a in paid)
        if status in ("failed", "closed"):
            t = fp + n
        else:
            break
    return total, evals, funded


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)[0])
    pa_tr = M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0]
    pa = T.leg_paths(bars, pa_tr)
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        day_pnl = np.array([sum(p for p, _, _ in tr) for _, tr in pa_days])
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + HORIZON <= len(ss)]
        for lock in (False, True):
            out = np.array([slot(ev_days, pa_days, s, lock) for s in starts])
            wk = out[:, 0] / WEEKS
            rows.append({"period": label, "payout stop": "on" if lock else "off", "starts": len(starts),
                         "$ a week per slot": wk.mean(), "median $ a week": float(np.median(wk)),
                         "paid at all %": 100 * float(np.mean(out[:, 0] > 0)),
                         "evals a slot": out[:, 1].mean(), "funded a slot": out[:, 2].mean(),
                         "slots for $1,500": GOAL / wk.mean() if wk.mean() > 0 else np.inf,
                         "break-even eval fee $": (out[:, 0].mean() - ACTIVATION * out[:, 2].mean()) / out[:, 1].mean(),
                         "funded day mean $": day_pnl.mean(), "funded day sd $": day_pnl.std()})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(2).to_string(index=False))
    print("\nOne account's bound: the daily mean needed for a 20% / 50% chance of failing at the measured spread")
    for _, r in df[df["payout stop"] == "off"].iterrows():
        s = r["funded day sd $"]
        need20 = s * s * np.log(1 / 0.2) / (2 * 2000)
        need50 = s * s * np.log(1 / 0.5) / (2 * 2000)
        p_fail = np.exp(-2 * r["funded day mean $"] * 2000 / (s * s)) if r["funded day mean $"] > 0 else 1.0
        print(f"{r.period}: mean ${r['funded day mean $']:.0f}, sd ${s:.0f}, fail ~{100 * p_fail:.0f}%; "
              f"$300 a day at a 20% fail chance needs sd <= ${np.sqrt(300 * 2 * 2000 / np.log(5)):.0f}; "
              f"at this sd: ${need20:.0f}/day (20%), ${need50:.0f}/day (50%)")


if __name__ == "__main__":
    main()
