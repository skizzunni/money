"""Round one hundred and twenty-nine: an evaluation that runs out of time has failed, so play bolder near the end.

    python research/bold_finish.py nsx1m_scaled.pkl nq1m_scaled.pkl

Every evaluation result so far treats "out of time" as just another way not to pass, and the strategy trades the same
size on day 29 as on day 1. But for the user a timeout and a bust are the same outcome (the evaluation is gone; a new
one is bought). Late in the 30 days, an evaluation that hasn't passed gives up nothing by taking more risk: with a small
edge and a deadline, bold play maximises the chance of reaching the target (the classic result for a gambler racing
a deadline). Rules, fixed before running (the strategy now with close-at-target, research/pass_lock; the day's whole
P/L and path scaled, as research/cushion_size):
  late x2 / late x2.5     from calendar day 20 of 30, if not yet passed, 2x / 2.5x size (bot 8 / 10 MNQ)
  later x2 / later x2.5   the same from day 24
  finish x2               2x on a day that starts within $1,000 of the target (any day)
Bar, fixed before running: adopted if it passes more evaluations in all three periods (2011-18, 2019-25, NQ
2015-24) and in the newest 13 months, with payouts per evaluation at least as high in the three; if several, the most
paid in sum. Size stays within Apex's 10 MNQ (the breakout's own contracts scale with it; a scaled breakout trade that
would exceed 10 is capped in the strategy, which the day-scaling here does not model: a slight overstatement).
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
RULES = {"now": None, "late x2": ("day", 20, 2.0), "late x2.5": ("day", 20, 2.5), "later x2": ("day", 24, 2.0),
         "later x2.5": ("day", 24, 2.5), "finish x2": ("near", 1000.0, 2.0)}


def attempt(days, rule, horizon=30):
    """research/pass_lock.attempt (close at the target, intraday trail) with the rule's size on qualifying days."""
    bal = peak = 0.0
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        age = (day - start).days
        if age >= horizon:
            return "timeout", n
        k = 1.0
        if rule is not None:
            kind, level, mult = rule
            if (kind == "day" and age >= level) or (kind == "near" and A.TARGET - bal <= level):
                k = mult
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + k * hi_run)
            bust = np.flatnonzero(bal + k * lo_path <= run_peak - A.DD)
            hit = np.flatnonzero(bal + k * hi_run >= A.TARGET + BUFFER)
            if hit.size and (not bust.size or hit[0] < bust[0]):
                return "passed", n + 1
            if bust.size:
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
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
        memo = {}
        for name, rule in RULES.items():
            outs = [attempt(ev_days[s:], rule) for s in starts]
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
            rows.append({"period": label, "rule": name, "pass %": 100 * r.count("passed") / len(r),
                         "bust %": 100 * r.count("failed") / len(r), "timeout %": 100 * r.count("timeout") / len(r),
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
    key = df.set_index(["rule", "period"])
    main3 = ("2011-2018", "2019-2025", "NQ 2015-2024")
    wins = []
    for name in list(RULES)[1:]:
        ok = all(key.loc[(name, p)]["pass %"] > key.loc[("now", p)]["pass %"] for p in main3 + ("Jul 2025-Aug 2026",))
        ok &= all(key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"] for p in main3)
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in main3), name))
    print(f"ADOPT {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
