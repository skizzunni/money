"""Round one hundred and twenty-seven: when to ask for a payout on the funded account.

    python research/payout_buffer.py nsx1m_scaled.pkl nq1m_scaled.pkl

Every funded result so far (apex_payouts.pa_run) takes a payout the first day it is allowed (five $200 days since the
last, the balance at +$2,600 or more, no day above half the cycle's profit), as much as allowed (the cap, or down to
+$2,100). Each payout puts the balance back near the threshold, which is locked at +$100 by then, so the account
restarts with the minimum cushion. The funded account has no time limit, so a payout asked for later, leaving a buffer,
could pay more in total. Policies, fixed before running: ask only when, after the payout, the balance stays at least
$X above +$2,100, X = 0 (now), $500, $1,000, $2,000 (the payout still at most the cap; the rest as pa_run).
Measured on the strategy now: the user's intraday-trail evaluation with close-at-target (research/pass_lock), then
the funded account.
Bar, fixed before running: adopted if it pays more per evaluation in all three periods (2011-18, 2019-25, NQ
2015-24); the first payout within 20 sessions reported.
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

BUFFERS = (0.0, 500.0, 1000.0, 2000.0)


def pa_buffer(days, caps, buffer):
    """apex_payouts.pa_run, asking for a payout only when the balance after it stays >= +$2,100 + buffer."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, P.dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
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
            amt = min(caps[len(paid)], bal - P.SAFETY - buffer)
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
        for buf in BUFFERS:
            memo, paid, six, n_pay = {}, [], 0, []
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = pa_buffer(pa_days[fp:], P.CAPS["base"], buf)
                pp, end, _ = memo[fp]
                paid.append(sum(a for _, a in pp))
                n_pay.append(len(pp))
                six += end == "closed"
            firsts = [pa_buffer(pa_days[s:s + 20], P.CAPS["base"], buf)[0] for s in starts]
            rows.append({"period": label, "buffer": buf, "$ paid per eval": float(np.mean(paid)),
                         "payouts per funded account": float(np.mean(n_pay)) if n_pay else 0.0,
                         "all 6 % of evals": 100 * six / len(starts),
                         "paid in 20 %": 100 * np.mean([bool(f) for f in firsts])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(2).to_string(index=False))
    key = df.set_index(["buffer", "period"])
    for buf in BUFFERS[1:]:
        ok = all(key.loc[(buf, p)]["$ paid per eval"] > key.loc[(0.0, p)]["$ paid per eval"]
                 for p in df.period.unique())
        print(f"buffer ${buf:.0f}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
