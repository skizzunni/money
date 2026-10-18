"""Round one hundred and twenty-four: close everything the moment the evaluation reaches its target.

    python research/pass_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl

Every evaluation result so far (apex25k.attempt) counts a pass only when a trade closes with the balance at +$3,000 or
more. A trade (or the bot + breakout together) that carries the account past +$3,000 in open profit and then falls
back doesn't pass. A trader closes everything the moment the account's net liquidation (balance + open P/L) reaches
the target, which realises it; Apex's 2026 evaluations reportedly have no minimum number of days. Rule, fixed before
running: in the evaluation, once the day's merged minute equity (research/trap_reversal.leg_paths, the running high
of the minute's best) reaches +$3,000 + $25 (fees and slippage on the close), the evaluation is passed, unless the
threshold was hit in that same minute or earlier (checked first). The funded account as now.
Measured on the strategy now (bot + breakout), the user's intraday-trail evaluation (threshold never stopping) and,
second reading, with the threshold stopping at the start (round 109).
Bar, fixed before running: adopted if it passes more evaluations and pays at least as much per evaluation in all
three periods (2011-18, 2019-25, NQ 2015-24).
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

BUFFER = 25.0


def attempt(days, lock_target, stop_at=None, horizon=30):
    """The intraday-trail evaluation. lock_target: passed the minute equity reaches the target + BUFFER (bust checked
    first, up to and including that minute). stop_at: the threshold stops trailing at this level (None: never)."""
    bal = peak = 0.0
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon:
            return "timeout", n
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + hi_run)
            thr = run_peak - A.DD if stop_at is None else np.minimum(run_peak - A.DD, stop_at)
            bust = np.flatnonzero(bal + lo_path <= thr)
            if lock_target:
                hit = np.flatnonzero(bal + hi_run >= A.TARGET + BUFFER)
                if hit.size and (not bust.size or hit[0] < bust[0]):
                    return "passed", n + 1
            if bust.size:
                return "failed", n + 1
            peak = max(peak, float(run_peak[-1]))
            bal += pnl
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
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
        memo = {}
        for reading, stop_at in (("threshold never stops", None), ("threshold stops at the start", 0.0)):
            for lock in (False, True):
                outs = [attempt(ev_days[s:], lock, stop_at) for s in starts]
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
                rows.append({"period": label, "reading": reading, "setup": "close at target" if lock else "now",
                             "pass %": 100 * r.count("passed") / len(r), "bust %": 100 * r.count("failed") / len(r),
                             "timeout %": 100 * r.count("timeout") / len(r),
                             "sessions to pass": float(np.median([u for o, u in outs if o == "passed"])),
                             "$ paid per eval": float(np.mean(paid))})
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
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["reading", "setup", "period"])
    r = "threshold never stops"
    ok = all(key.loc[(r, "close at target", p)]["pass %"] > key.loc[(r, "now", p)]["pass %"] and
             key.loc[(r, "close at target", p)]["$ paid per eval"] >= key.loc[(r, "now", p)]["$ paid per eval"]
             for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
    print("\nADOPT" if ok else "\nNOT ADOPTED")


if __name__ == "__main__":
    main()
