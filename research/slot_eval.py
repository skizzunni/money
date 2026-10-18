"""Round one hundred and thirty-four: the bold finish and the evaluation's breakout risk, judged as money a week.

    python research/slot_eval.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 133 found every bigger evaluation size netting more a week than 4 MNQ in the three long periods (the pick, 8
MNQ, failing only in the newest 13 months). Two evaluation-only options were rejected per evaluation and are re-judged
the same way, 52 weeks from every start, the payout stop on, net of $100 an evaluation and $79 an activation
(research/slot_size). Fixed before running, evaluation side only (funded as now):
  W $300 / W $400      the breakout's risk in the evaluation $300 / $400 (1-10 MNQ; $200 now)
  bold d20 x2.5        round 129's bold finish: from calendar day 20, 2.5x size (bot 10 MNQ)
  bold d24 x2          from day 24, 2x
Pick and bar, fixed before running (as round 133): the highest net a week at $100 on 2011-18; adopted if it nets more
than the current setting on 2019-25 AND NQ 2015-24 and no less in the newest 13 months.
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
import bold_finish as BF  # noqa: E402
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import pass_lock as PL  # noqa: E402
import payout_lock as PO  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

SETUPS = {"now": (200.0, None), "W $300": (300.0, None), "W $400": (400.0, None),
          "bold d20 x2.5": (200.0, ("day", 20, 2.5)), "bold d24 x2": (200.0, ("day", 24, 2.0))}


def slots(ev_days, pa_days, starts, rule):
    """research/slot_size.slots with the evaluation run by bold_finish.attempt when a rule is given."""
    ev_memo, pa_memo, out = {}, {}, []
    for s in starts:
        t, end, total, evals, funded = s, s + S.HORIZON, 0.0, 0, 0
        while t < end:
            evals += 1
            if t not in ev_memo:
                ev_memo[t] = PL.attempt(ev_days[t:], True) if rule is None else BF.attempt(ev_days[t:], rule)
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
    ev_bot = T.bot_trades(bars, 3, 1.0, 2.5)
    evs = {}
    for risk in {r for r, _ in SETUPS.values()}:
        old, C.RISK = C.RISK, risk
        try:
            evs[risk] = T.leg_paths(bars, M.combine(bars, ev_bot, M.w_candidates(bars, False), False)[0])
        finally:
            C.RISK = old
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), M.w_candidates(bars, False), False)[0])
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + S.HORIZON <= len(ss)]
        pa_days = P.by_day(pa, ss)
        for name, (risk, rule) in SETUPS.items():
            out = slots(P.by_day(evs[risk], ss), pa_days, starts, rule)
            row = {"period": label, "setup": name, "starts": len(starts), "paid $/wk": out[:, 0].mean() / S.WEEKS,
                   "evals": out[:, 1].mean(), "funded accts": out[:, 2].mean()}
            for fee in S.FEES:
                row[f"net $/wk at ${fee:.0f}"] = (out[:, 0].mean() - fee * out[:, 1].mean() -
                                                  S.ACTIVATION * out[:, 2].mean()) / S.WEEKS
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
    key = df.set_index(["setup", "period"])["net $/wk at $100"]
    pick = df[df.period == "2011-2018"].sort_values("net $/wk at $100", ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {pick}")
    if pick == "now":
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key[(pick, p)] > key[("now", p)] for p in ("2019-2025", "NQ 2015-2024"))
    ok &= key[(pick, "Jul 2025-Aug 2026")] >= key[("now", "Jul 2025-Aug 2026")]
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
