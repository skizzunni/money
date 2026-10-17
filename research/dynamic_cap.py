"""Round ninety-one: a dynamic daily profit cap that keeps Apex's 50% consistency rule from blocking payouts.

    python research/dynamic_cap.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds eighty-seven to ninety: a fixed daily profit stop makes payouts possible sooner but cuts the big days that pay
for the losers; with profit uncapped, one big day blocks the payout under the 50% consistency rule (no day above half
the profit since the last payout) until smaller green days dilute it. A day's profit is at most half the cycle's
total exactly when it is at most the cycle's profit before that day. So, within Apex's rules, a DYNAMIC cap: each day
the bot may make up to max(F, profit since the last payout before today); once the day's equity (closed + open)
reaches that, it closes and stops for the day (filled at the level less a tick a contract). Big days stay allowed
once the cycle has the profit to absorb them.
Funded policies, fixed before running: floor F = $400, $600, $900, or no cap (the strategy now); 4 or 6 MNQ at a
25-point cap; 2 losers; lock 0.5 / +6.25 (as the strategy trades funded). The evaluation as the strategy trades it
(4 MNQ, 3 losers, lock 1.0 / +2.5; no consistency rule in the evaluation). Payout rules as research/apex_payouts.py.
Measures (2011-18, 2019-25, NQ 2015-24): payouts per evaluation (base caps), all six paid %, funded first payout
within 20 and 40 sessions, funded busts %.
Adoption bar, fixed before running: the policy with the highest payouts per evaluation on 2011-18 must beat the
strategy now (4 MNQ, no cap) by >= 10% in payouts per evaluation AND in P(first payout within 40 sessions of being
funded), on 2019-25 AND NQ futures.
"""
from __future__ import annotations

import itertools
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import lock_apex as L  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
SLIP = 0.25 * A.PV
FLOORS = (400.0, 600.0, 900.0, None)
QS = (4, 6)
CURRENT = (4, None)


def pa_dyn(days, q, caps, floor):
    """A funded account from days[0] with the dynamic cap: (payouts [(session, $)], end, sessions)."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, P.dll_for(bal)
        cap = None if floor is None else max(floor, sum(cycle))
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + q * hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + q * lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
            win = np.flatnonzero(bal + q * hi_run - day_start >= cap) if cap is not None else np.array([], int)
            first_loss = min(bust[0] if bust.size else math.inf, stop[0] if stop.size else math.inf)
            if win.size and win[0] < first_loss:
                peak = max(peak, run_peak[win[0]])
                bal = day_start + cap - q * SLIP
                peak = max(peak, bal)
                break
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
            bal += q * pnl
            peak = max(peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if sum(c >= P.QUAL for c in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof:
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
    ev_tr = L.trades_for(bars, 3, 1.0, 2.5)
    pa_tr = L.trades_for(bars, 2, 0.5, 6.25)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [d for d in all_sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev_tr, sess), P.by_day(pa_tr, sess)
        outcomes = [A.attempt(ev_days[s:], 4, "intraday", 30) for s, d in enumerate(sess) if d <= last]
        for q, floor in itertools.product(QS, FLOORS):
            memo, paid, six = {}, [], 0
            for s, (res, used) in enumerate(outcomes):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = pa_dyn(pa_days[fp:], q, P.CAPS["base"], floor)
                pp, end, _ = memo[fp]
                paid.append(sum(a for _, a in pp))
                six += end == "closed"
            # the funded account from every session (independent of the evaluation), for the payout timing
            firsts = [pa_dyn(pa_days[s:s + 40], q, P.CAPS["base"], floor) for s, d in enumerate(sess) if d <= last]
            rows.append({"period": label, "MNQ": q, "floor": floor or 0, "$ paid per eval": float(np.mean(paid)),
                         "all 6 %": 100 * six / len(outcomes),
                         "paid in 20 %": 100 * np.mean([bool(f[0]) and f[0][0][0] < 20 for f in firsts]),
                         "paid in 40 %": 100 * np.mean([bool(f[0]) for f in firsts]),
                         "bust in 40 %": 100 * np.mean([f[1] == "failed" for f in firsts])})
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
    key = df.set_index(["period", "MNQ", "floor"])
    d = df[df.period == "2011-2018"].sort_values("$ paid per eval", ascending=False).iloc[0]
    pick = (d.MNQ, d.floor)
    cur = (CURRENT[0], 0)
    print(f"\npick on 2011-18: {pick[0]} MNQ, floor {pick[1]} (${d['$ paid per eval']:.0f} per evaluation)")
    ok = pick != cur
    for p in ("2019-2025", "NQ 2015-2024"):
        b, c = key.loc[(p, *pick)], key.loc[(p, *cur)]
        good = (b["$ paid per eval"] >= 1.1 * c["$ paid per eval"] and b["paid in 40 %"] >= 1.1 * c["paid in 40 %"])
        ok &= good
        print(f"  {p}: ${b['$ paid per eval']:.0f} vs ${c['$ paid per eval']:.0f}, paid in 40 {b['paid in 40 %']:.1f}% "
              f"vs {c['paid in 40 %']:.1f}%: {'PASS' if good else 'FAIL'}")
    print(f"  {'ADOPT' if ok else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
