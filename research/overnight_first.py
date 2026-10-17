"""Round one hundred and six: the overnight long on the funded account only until its first payout.

    python research/overnight_first.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round one hundred and five (research/overnight_combo.py): the overnight long (1 MNQ, 18:01 to the 09:30 open, stop
100 points) brings the funded account's first payout 2.6-3.3 times as often within 20 sessions, but later busts give
it back: payouts per evaluation are not higher. The user's goal is the first payout within two weeks. So: the
overnight long on the funded account until the first payout is paid, then off (the strategy as it is now from then
on); the evaluation as now. Description (chosen after round one hundred and five; all periods seen).
Measures from every possible start: the evaluation as now (research/combo_more), then the funded account: first
payout within 10 sessions (two weeks) and 20, $ paid per evaluation (base caps), all six paid %.
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
import overnight_combo as O  # noqa: E402
import trap_reversal as T  # noqa: E402


def pa_switch(days_before, days_after, caps):
    """apex_payouts.pa_run, with days_before's trades until the first payout and days_after's from the next day."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n in range(len(days_before)):
        trades = (days_after if paid else days_before)[n][1]
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
            amt = min(caps[len(paid)], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days_before)


def job(args):
    path, periods = args
    bars = A.rth(path)
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    cands = M.w_candidates(bars, False)
    sess = list(T.sessions_of(bars))
    ev_day = T.leg_paths(bars, M.combine(bars, ev_bot, cands, False)[0])
    pa_day = T.leg_paths(bars, M.combine(bars, pa_bot, cands, False)[0])
    night = O.overnight(path, 1, 100.0, delay=1)
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days = P.by_day(ev_day, ss)
        plain, nightly = P.by_day(pa_day, ss), P.by_day(night + pa_day, ss)
        starts = [s for s, d in enumerate(ss) if d <= last]
        outs = [A.attempt(ev_days[s:], 1, "intraday", 30) for s in starts]
        for name, before, after in (("now", plain, plain), ("overnight always", nightly, nightly),
                                    ("overnight until 1st payout", nightly, plain)):
            memo, paid, six = {}, [], 0
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = pa_switch(before[fp:], after[fp:], P.CAPS["base"])
                pp, end, _ = memo[fp]
                paid.append(sum(a for _, a in pp))
                six += end == "closed"
            # the funded account from every session, for the timing of the first payout
            firsts = [pa_switch(before[s:s + 20], after[s:s + 20], P.CAPS["base"])[0] for s in starts]
            rows.append({"period": label, "funded": name,
                         "eval pass %": 100 * np.mean([r == "passed" for r, _ in outs]),
                         "$ paid per eval": float(np.mean(paid)), "all 6 %": 100 * six / len(starts),
                         "paid in 10 %": 100 * np.mean([bool(f) and f[0][0] < 10 for f in firsts]),
                         "paid in 20 %": 100 * np.mean([bool(f) for f in firsts])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
             ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))
    jobs = [(nsx, idx_p), (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    print(df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
