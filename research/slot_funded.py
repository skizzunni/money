"""Round one hundred and thirty-five: the funded account's breakout risk, loser limit and lock, judged as money a week.

    python research/slot_funded.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds 133-134 judged the evaluation's settings per week of a running account; the funded settings were chosen per
evaluation (rounds 83, 121, 122). Fixed before running, funded side only, the evaluation as now (4 MNQ, 3 losers, the
breakout at $400), 52 weeks, payout stop on, net of $100 an evaluation and $79 an activation (research/slot_size):
  W $100 / W $300   the funded breakout's risk ($200 now)
  3 losers          the funded loser limit 3 (2 now)
  eval lock         the funded lock at 1.0 / +2.5 points (the evaluation's) instead of 0.5 / +6.25
Pick and bar, fixed before running (as rounds 133-134): the highest net a week at $100 on 2011-18; adopted if it nets
more than the current setting on 2019-25 AND NQ 2015-24 and no less in the newest 13 months.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import slot_eval as SE  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

SETUPS = {"now": (200.0, 2, 0.5, 6.25), "W $100": (100.0, 2, 0.5, 6.25), "W $300": (300.0, 2, 0.5, 6.25),
          "3 losers": (200.0, 3, 0.5, 6.25), "eval lock": (200.0, 2, 1.0, 2.5)}


def legs(bars, bot, risk):
    old, C.RISK = C.RISK, risk
    try:
        return T.leg_paths(bars, M.combine(bars, bot, M.w_candidates(bars, False), False)[0])
    finally:
        C.RISK = old


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev = legs(bars, T.bot_trades(bars, 3, 1.0, 2.5), 400.0)
    pas = {name: legs(bars, T.bot_trades(bars, lz, la, lp), risk) for name, (risk, lz, la, lp) in SETUPS.items()}
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + S.HORIZON <= len(ss)]
        ev_days = P.by_day(ev, ss)
        for name in SETUPS:
            out = SE.slots(ev_days, P.by_day(pas[name], ss), starts, None)
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
