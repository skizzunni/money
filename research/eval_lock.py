"""Round one hundred and nine: the intraday-trail evaluation if its threshold stops trailing, and sizing up after.

    python research/eval_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl

Every evaluation result so far (apex25k.attempt, "intraday") lets the $2,000 threshold trail the peak, open profit
included, all the way to the $3,000 target. Third-party summaries of Apex's 2026 rules say the intraday threshold
stops trailing: on funded accounts at the start + $100, and in evaluations possibly at the starting balance (once the
peak reaches +$2,000). Not confirmed on Apex's own site from here, so both are measured, plus no lock (as so far).
Once the threshold has stopped, every dollar of profit widens the cushion, so the last stretch to $3,000 can carry
more size without more risk of failing than the start had.
Setups (the user's evaluation: the strategy now, bot 4 MNQ + breakout; funded as now, apex_payouts.pa_run):
  lock: none / at the start ($0) / at +$100
  after the lock (from the next day, while the cushion above the locked threshold is at least $2,000): contracts
  x1 (as now), x1.5, x2 (the whole day's P/L and path scaled; at most 10 MNQ is not checked here)
Bar, fixed before running, for each lock assumption: x1.5 or x2 adopted if it passes more evaluations than x1 and
pays at least as much per evaluation, in all three periods.
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
import trap_reversal as T  # noqa: E402

LOCKS = {"none": None, "start": 0.0, "start + 100": 100.0}
MULTS = (1.0, 1.5, 2.0)


def attempt_lock(days, lock, mult, horizon=30):
    """apex25k.attempt's intraday trail, the threshold capped at `lock` (None: never), and from the day after it is
    reached the day's trades scaled by `mult`. 'passed' | 'failed' | 'timeout', sessions used."""
    bal = peak = 0.0
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon:
            return "timeout", n
        locked = lock is not None and peak - A.DD >= lock
        k = mult if locked else 1.0
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + k * hi_run)
            thr = run_peak - A.DD if lock is None else np.minimum(run_peak - A.DD, lock)
            if (bal + k * lo_path <= thr).any():
                return "failed", n + 1
            peak = max(peak, float(run_peak[-1]))
            bal += k * pnl
            peak = max(peak, bal)
            if bal >= A.TARGET:
                return "passed", n + 1
    return "timeout", len(days)


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)[0])
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= last]
        memo = {}
        for lname, lock in LOCKS.items():
            for mult in MULTS:
                if lock is None and mult != 1.0:
                    continue
                outs = [attempt_lock(ev_days[s:], lock, mult) for s in starts]
                paid = []
                for s, (res, used) in zip(starts, outs, strict=True):
                    if res != "passed":
                        paid.append(0.0)
                        continue
                    fp = s + used
                    if fp not in memo:
                        memo[fp] = sum(x for _, x in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
                    paid.append(memo[fp])
                r = [o for o, _ in outs]
                rows.append({"period": label, "lock": lname, "size after lock": mult,
                             "pass %": 100 * r.count("passed") / len(r), "bust %": 100 * r.count("failed") / len(r),
                             "timeout %": 100 * r.count("timeout") / len(r),
                             "sessions to pass": float(np.median([u for o, u in outs if o == "passed"])),
                             "$ paid per eval": float(np.mean(paid))})
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
    key = df.set_index(["lock", "size after lock", "period"])
    for lname in ("start", "start + 100"):
        for mult in (1.5, 2.0):
            ok = all(key.loc[(lname, mult, p)]["pass %"] > key.loc[(lname, 1.0, p)]["pass %"] and
                     key.loc[(lname, mult, p)]["$ paid per eval"] >= key.loc[(lname, 1.0, p)]["$ paid per eval"]
                     for p in df.period.unique())
            print(f"lock {lname}, x{mult}: {'ADOPT' if ok else 'not adopted'}")


if __name__ == "__main__":
    main()
