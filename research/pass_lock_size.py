"""Round one hundred and twenty-five: the evaluation's size and loser limit again, with close-at-target.

    python research/pass_lock_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 124: closing everything the moment the evaluation reaches +$3,000 passes far more evaluations. Every earlier
size test counted a pass only at a trade's close, so the evaluation's settings are re-tested with the rule. Grid,
fixed before running: contracts 3, 4, 5, 6 (25-point cap) x losers a day 2, 3, 4; lock, breakout and funded account
as now; the user's intraday-trail evaluation with close-at-target (research/pass_lock.attempt).
Pick and bar, fixed before running: the highest pass rate on 2011-18 (ties: more paid); adopted if, against 4 MNQ /
3 losers with close-at-target, it passes more and pays at least as much per evaluation on 2019-25 AND NQ 2015-24.
"""
from __future__ import annotations

import itertools
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

GRID = list(itertools.product((3, 4, 5, 6), (2, 3, 4)))
NOW = "4 MNQ, 3 losers"


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    ev_trades = {lz: T.bot_trades(bars, lz, 1.0, 2.5) for lz in (2, 3, 4)}
    evs = {}
    for q, lz in GRID:
        M.BOTQ = q
        try:
            evs[(q, lz)] = T.leg_paths(bars, M.combine(bars, ev_trades[lz], cands, False)[0])
        finally:
            M.BOTQ = 4
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        pa_days = P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
        memo = {}
        for (q, lz), ev in evs.items():
            ev_days = P.by_day(ev, ss)
            outs = [PL.attempt(ev_days[s:], True) for s in starts]
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
            rows.append({"period": label, "setup": f"{q} MNQ, {lz} losers",
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
        print(df[df.period == label].drop(columns="period").sort_values("pass %", ascending=False).round(1)
              .to_string(index=False))
    key = df.set_index(["setup", "period"])
    d = df[df.period == "2011-2018"].sort_values(["pass %", "$ paid per eval"], ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {d}")
    if d == NOW:
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key.loc[(d, p)]["pass %"] > key.loc[(NOW, p)]["pass %"] and
             key.loc[(d, p)]["$ paid per eval"] >= key.loc[(NOW, p)]["$ paid per eval"]
             for p in ("2019-2025", "NQ 2015-2024"))
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
