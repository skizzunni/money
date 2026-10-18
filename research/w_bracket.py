"""Round one hundred and thirty: a take-profit for the breakout, so every trade carries a full bracket.

    python research/w_bracket.py nsx1m_scaled.pkl nq1m_scaled.pkl

Several 2026 summaries of Apex's rules say every order must carry an attached stop AND take-profit (platform-enforced;
not confirmed on Apex's own site from here). The bot's trades have both; the breakout's had only a stop and its exit at
16:00. Take-profits, fixed before running, in R (the breakout's stop, a quarter of yesterday's range): 4R, 6R, 8R
(1, 1.5, 2 x yesterday's range from the fill); fills at the limit once price trades a tick through it, the stop first in
a bar reaching both (research/combo_more.w_candidates mgmt). The strategy now with close-at-target otherwise.
Pick, fixed before running: the nearest take-profit (most trades bracketed sensibly) whose pass rate is no more than
0.5 points below none and whose payouts per evaluation are at least 97% of none's in each of the three periods; if none
qualifies, the farthest (8R), as the compliance minimum.
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

R = 0.25
TPS = {"none": None, "4R": 4.0, "6R": 6.0, "8R": 8.0}


def job(args):
    path, periods, name = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    tp = TPS[name]
    cands = M.w_candidates(bars, False, None if tp is None else (99.0, 0.0, tp * R))
    ev = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)[0])
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
        outs = [PL.attempt(ev_days[s:], True) for s in starts]
        memo, paid = {}, []
        for s, (res, used) in zip(starts, outs, strict=True):
            if res != "passed":
                paid.append(0.0)
                continue
            fp = s + used
            if fp not in memo:
                memo[fp] = sum(x for _, x in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
            paid.append(memo[fp])
        r = [o for o, _ in outs]
        rows.append({"period": label, "take-profit": name, "pass %": 100 * r.count("passed") / len(r),
                     "$ paid per eval": float(np.mean(paid))})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
             ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, n) for path, per in ((nsx, idx_p), (nq, nq_p)) for n in TPS]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["take-profit", "period"])
    main3 = ("2011-2018", "2019-2025", "NQ 2015-2024")
    pick = "8R"
    for name in ("4R", "6R", "8R"):
        if all(key.loc[(name, p)]["pass %"] >= key.loc[("none", p)]["pass %"] - 0.5 and
               key.loc[(name, p)]["$ paid per eval"] >= 0.97 * key.loc[("none", p)]["$ paid per eval"] for p in main3):
            pick = name
            break
    print(f"\nPICK {pick}")


if __name__ == "__main__":
    main()
