"""Round one hundred and twenty-eight: close for the day the moment closing makes the funded account payout-eligible.

    python research/payout_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl

The funded account's counterpart of round 124. Apex checks a payout at the day's end: five days of $200 or more since
the last payout, the balance at +$2,600 or more, no day above half the cycle's profit, at least $500 to take. All
funded results so far trade on to the close, so a day that was payout-eligible at 11:00 can give it back. Rule, fixed
before running: at each minute, if closing everything now (at the minute's worst equity, less $10) would leave the day
meeting every condition, close, stop for the day and take the payout (research/apex_payouts.pa_run otherwise).
Measured on the strategy now: the user's intraday-trail evaluation with close-at-target (research/pass_lock), then
the funded account.
Bar, fixed before running: adopted if it pays more per evaluation in all three periods (2011-18, 2019-25, NQ 2015-24)
and brings the first payout within 20 sessions at least as often.
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
import trap_reversal as T  # noqa: E402

SLIP = 10.0


def eligible(cycle, day_pnl, bal):
    c = cycle + [day_pnl]
    prof = sum(c)
    return (sum(x >= P.QUAL for x in c) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(c) <= 0.5 * prof)


def pa_lock(days, caps, lock):
    """apex_payouts.pa_run; lock: close for the day at the first minute closing would make the day payout-eligible."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, P.dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
            first_bad = min(bust[0] if bust.size else len(eq), stop[0] if stop.size else len(eq))
            if lock:
                hit = None
                for m in range(first_bad):
                    e = eq[m] - SLIP
                    if e - day_start >= P.QUAL and eligible(cycle, e - day_start, e) and \
                            min(caps[len(paid)], e - P.SAFETY) >= P.MIN_PAY:
                        hit = m
                        break
                if hit is not None:
                    peak = max(peak, float(run_peak[hit]))
                    bal = eq[hit] - SLIP
                    break  # done for the day: the day's end below takes the payout
            if bust.size and (not stop.size or bust[0] < stop[0] or
                              (bust[0] == stop[0] and thr[bust[0]] >= day_start - dll)):
                return paid, "failed", n + 1
            if stop.size:
                peak = max(peak, run_peak[stop[0]])
                bal = day_start - dll
                if bal <= min(peak - P.PA_DD, P.PA_LOCK):
                    return paid, "failed", n + 1
                break
            peak = max(peak, run_peak[-1])
            bal += pnl
            peak = max(peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if sum(x >= P.QUAL for x in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof:
            amt = min(caps[len(paid)], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days)


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
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
        outs = [PL.attempt(ev_days[s:], True) for s in starts]
        for lock in (False, True):
            memo, paid, n_pay, six = {}, [], [], 0
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = pa_lock(pa_days[fp:], P.CAPS["base"], lock)
                pp, end, _ = memo[fp]
                paid.append(sum(a for _, a in pp))
                n_pay.append(len(pp))
                six += end == "closed"
            firsts = [pa_lock(pa_days[s:s + 20], P.CAPS["base"], lock)[0] for s in starts]
            tens = [bool(f) and f[0][0] < 10 for f in firsts]
            rows.append({"period": label, "setup": "close when payout-eligible" if lock else "now",
                         "$ paid per eval": float(np.mean(paid)), "payouts per funded account": float(np.mean(n_pay)),
                         "all 6 % of evals": 100 * six / len(starts), "paid in 10 %": 100 * np.mean(tens),
                         "paid in 20 %": 100 * np.mean([bool(f) for f in firsts])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(2).to_string(index=False))
    key = df.set_index(["setup", "period"])
    ok = all(key.loc[("close when payout-eligible", p)]["$ paid per eval"] > key.loc[("now", p)]["$ paid per eval"]
             and key.loc[("close when payout-eligible", p)]["paid in 20 %"] >= key.loc[("now", p)]["paid in 20 %"]
             for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
    print("\nADOPT" if ok else "\nNOT ADOPTED")


if __name__ == "__main__":
    main()
