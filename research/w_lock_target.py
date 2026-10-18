"""Round one hundred and thirty-one: the breakout's lock again, with close-at-target and its take-profit.

    python research/w_lock_target.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 103 (on the old pass rule): a lock on the breakout trade (stop to entry + 0.1R once it is up 0.5R or 1R) made
53-54% of all trades winners and cut red days to 42-44%, the user's "more likely to win than lose", but paid less.
Re-tested now: close-at-target, the breakout's take-profit at 8R (round 130). Bar, fixed before running: adopted if it
raises the share of winning trades AND passes at least as many evaluations (within 0.5 points) and pays at least 97%
as much per evaluation in all three periods.
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
VARIANTS = {"now (8R target)": (99.0, 0.0, 8 * R), "lock 0.5R": (0.5 * R, 0.1 * R, 8 * R),
            "lock 1R": (1.0 * R, 0.1 * R, 8 * R)}


def job(args):
    path, periods, name = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False, VARIANTS[name])
    ev_legs, ev_tr = M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)
    ev = T.leg_paths(bars, ev_legs)
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        starts = [s for s, d in enumerate(ss) if d <= last]
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
        tr = [t for t in ev_tr if pd.Timestamp(first) <= t[0] <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in ss if d <= last]))
        for d, pnl, _, _ in ev:
            if d in daily.index:
                daily[d] += pnl
        r = [o for o, _ in outs]
        rows.append({"period": label, "setup": name, "winners %": 100 * np.mean([t[1] > 0 for t in tr]),
                     "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                     "pass %": 100 * r.count("passed") / len(r), "$ paid per eval": float(np.mean(paid))})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
             ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, n) for path, per in ((nsx, idx_p), (nq, nq_p)) for n in VARIANTS]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    base = "now (8R target)"
    for name in list(VARIANTS)[1:]:
        ok = all(key.loc[(name, p)]["winners %"] > key.loc[(base, p)]["winners %"] and
                 key.loc[(name, p)]["pass %"] >= key.loc[(base, p)]["pass %"] - 0.5 and
                 key.loc[(name, p)]["$ paid per eval"] >= 0.97 * key.loc[(base, p)]["$ paid per eval"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
