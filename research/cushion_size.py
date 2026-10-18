"""Round one hundred and fifteen: smaller size when the evaluation's cushion runs low.

    python research/cushion_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

How the user's intraday-trail evaluations bust (the strategy now, 2019-25 and NQ): not in one bad day but over a median
of 9 sessions; before the bust day about $1,750 of the $2,000 cushion is already gone, and the bust day only has to
lose another $230-250, one ordinary losing day at full size. Round 63's ladders sized on profit; here size follows
the cushion left (the balance minus the trailing threshold, at the day's start): below a level, the day trades
smaller (the bot and the breakout scaled together; research/trap_reversal.leg_paths days scaled), so a thin cushion
lasts longer for the edge to pull it back.
Rules, fixed before running (evaluation only; the funded account as now):
  C1  half size while the cushion is under $1,000
  C2  half size while the cushion is under $700
  C3  half under $1,000, a quarter under $500
Bar, fixed before running: adopted if, against now, the pass rate is higher and payouts per evaluation at least as
high in all three periods; if several, the most paid in sum.
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

RULES = {"now": (), "C1": ((1000.0, 0.5),), "C2": ((700.0, 0.5),), "C3": ((1000.0, 0.5), (500.0, 0.25))}


def attempt_scaled(days, rule, horizon=30):
    """apex25k.attempt's intraday trail, each day's trades scaled by the rule's factor for the cushion at its start."""
    bal = peak = 0.0
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon:
            return "timeout", n
        cushion = bal - (peak - A.DD)
        k = 1.0
        for level, factor in rule:
            if cushion < level:
                k = factor
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + k * hi_run)
            if (bal + k * lo_path <= run_peak - A.DD).any():
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
            outs = [attempt_scaled(ev_days[s:], rule) for s in starts]
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
    key = df.set_index(["rule", "period"])
    wins = []
    for name in list(RULES)[1:]:
        ok = all(key.loc[(name, p)]["pass %"] > key.loc[("now", p)]["pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in ("2011-2018", "2019-2025",
                                                                               "NQ 2015-2024")), name))
    print(f"ADOPT {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
