"""Round one hundred and thirty-three: the evaluation's and the funded account's size, judged as money a week.

    python research/slot_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 132 measured an account the way it is run (a new evaluation after each failed one) and found that a rule judged
per evaluation (the payout stop) was the better one per week. The sizes were all chosen per evaluation (rounds 60,
61, 125: "bigger sizes pass about as often, faster, and bust more"). Per week, faster matters: a slot that passes in
6 sessions instead of 12 is funded sooner, and a failed evaluation is replaced sooner (at a fee). Grid, fixed before
running, the strategy now (bot + breakout, close-at-target, the payout stop on), 52 weeks from every start session:
  evaluation  bot 4 / 5 / 6 / 8 MNQ x 2 / 3 losers a day (funded as now)
  funded      bot 3 / 5 / 6 MNQ (evaluation as now)
Measure: payouts a week per slot, less $100 for each evaluation and $79 for each funded account (per week); also at
$50 and $200 an evaluation. Pick and bar, fixed before running: the highest net a week at $100 on 2011-18; adopted if
it nets more than the current setting (4 MNQ / 3 losers, funded 4 MNQ) on 2019-25 AND NQ 2015-24 and no less in the
newest 13 months (Jul 2025 - Aug 2026).
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
import payout_lock as PO  # noqa: E402
import trap_reversal as T  # noqa: E402

HORIZON, WEEKS, ACTIVATION, FEES = 260, 52.0, 79.0, (50.0, 100.0, 200.0)
NOW = ("4 MNQ, 3 losers", 4)
SETUPS = [(f"{q} MNQ, {lz} losers", 4) for q in (4, 5, 6, 8) for lz in (2, 3)] + [("4 MNQ, 3 losers", q)
                                                                                    for q in (3, 5, 6)]


def paths(bars, cands, q, losers, lock_at, lock_plus):
    M.BOTQ = q
    try:
        return T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, losers, lock_at, lock_plus), cands, False)[0])
    finally:
        M.BOTQ = 4


def slots(ev_days, pa_days, starts):
    """research/accounts_needed.slot for every start, with each evaluation and funded account run once (memo)."""
    ev_memo, pa_memo, out = {}, {}, []
    for s in starts:
        t, end, total, evals, funded = s, s + HORIZON, 0.0, 0, 0
        while t < end:
            evals += 1
            if t not in ev_memo:
                ev_memo[t] = PL.attempt(ev_days[t:], True)
            res, used = ev_memo[t]
            if res != "passed":
                t += max(used, 1)
                continue
            fp = t + used
            if fp >= end:
                break
            funded += 1
            if fp not in pa_memo:
                pa_memo[fp] = PO.pa_lock(pa_days[fp:], P.CAPS["base"], True)
            paid, status, n = pa_memo[fp]
            total += sum(a for k, a in paid if fp + k < end)
            if status in ("failed", "closed") and fp + n <= end:
                t = fp + n
            else:
                break
        out.append((total, evals, funded))
    return np.array(out)


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    evs = {name: paths(bars, cands, int(name.split()[0]), int(name.split(", ")[1].split()[0]), 1.0, 2.5)
           for name in {e for e, _ in SETUPS}}
    pas = {q: paths(bars, cands, q, 2, 0.5, 6.25) for q in {p for _, p in SETUPS}}
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + HORIZON <= len(ss)]
        ev_days = {k: P.by_day(v, ss) for k, v in evs.items()}
        pa_days = {k: P.by_day(v, ss) for k, v in pas.items()}
        for e, p in SETUPS:
            out = slots(ev_days[e], pa_days[p], starts)
            row = {"period": label, "evaluation": e, "funded": f"{p} MNQ", "starts": len(starts),
                   "paid $/wk": out[:, 0].mean() / WEEKS, "evals": out[:, 1].mean(), "funded accts": out[:, 2].mean()}
            for fee in FEES:
                row[f"net $/wk at ${fee:.0f}"] = (out[:, 0].mean() - fee * out[:, 1].mean() -
                                                  ACTIVATION * out[:, 2].mean()) / WEEKS
            rows.append(row)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    df["setup"] = df.evaluation + " / funded " + df.funded
    key = df.set_index(["setup", "period"])["net $/wk at $100"]
    now = f"{NOW[0]} / funded {NOW[1]} MNQ"
    pick = df[df.period == "2011-2018"].sort_values("net $/wk at $100", ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {pick}")
    if pick == now:
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key[(pick, p)] > key[(now, p)] for p in ("2019-2025", "NQ 2015-2024"))
    ok &= key[(pick, "Jul 2025-Aug 2026")] >= key[(now, "Jul 2025-Aug 2026")]
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
