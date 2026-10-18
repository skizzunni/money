"""Round one hundred and thirty-nine (the audit's open items): a tighten-only stop, and skipping a breakout trade whose
one contract costs more than its risk budget.

    python research/exits2.py nsx1m_scaled.pkl nq1m_scaled.pkl

Two rule changes the audit logged (docs/AUDIT.md, concern 10 and stage 5), defined before running, each the whole
strategy re-run (research/exits.build):
  tighten-only     the stop never moves back toward the price: each bar it is the tightest of the line stop, the
                   $200 cap, the lock and the stop it had (mnqbot/noise.py tighten_only, the webhook mode's rule)
  skip over-budget a breakout day whose single contract would risk 1-1.5x the budget has no breakout trade (now: one
                   contract is forced up to 1.5x)
Measured and judged as round 138: more on the account in all four periods and an intraday drawdown no larger in
three of the four.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_more as M  # noqa: E402
import components as K  # noqa: E402
import exits as E  # noqa: E402
import slot_eval as SE  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

RULES = {"now": ({}, True), "tighten-only": ({"tighten_only": True}, True), "skip over-budget": ({}, False)}


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    rows = []
    for name, (extra, force) in RULES.items():
        M.FORCE_ONE = force
        try:
            ev_legs, ev_trades = E.build(bars, E.bot(bars, 3, 1.0, 2.5, extra), 400.0)
            pa_legs, _ = E.build(bars, E.bot(bars, 2, 0.5, 6.25, extra), 200.0)
        finally:
            M.FORCE_ONE = True
        ev_all, pa_all = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
        for label, first, last_start, last in periods:
            row = {"period": label, "rule": name, **K.stats(ev_legs, ev_trades, first, last)}
            ss = [d for d in sess if d >= pd.Timestamp(first)]
            starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + S.HORIZON <= len(ss)]
            out = SE.slots(P.by_day(ev_all, ss), P.by_day(pa_all, ss), starts, None)
            row["account net $/wk at $100"] = (out[:, 0].mean() - 100 * out[:, 1].mean() -
                                               S.ACTIVATION * out[:, 2].mean()) / S.WEEKS
            rows.append(row)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31", "2018-12-31"),
                   ("2019-2025", "2019-01-01", "2025-06-30", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14", "2026-09-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["rule", "period"])
    periods = list(df.period.unique())
    col = "account net $/wk at $100"
    for name in list(RULES)[1:]:
        more = all(key.loc[(name, p)][col] > key.loc[("now", p)][col] for p in periods)
        dd = sum(key.loc[(name, p)]["intraday DD"] <= key.loc[("now", p)]["intraday DD"] for p in periods)
        print(f"{name}: account more in all four: {more}; intraday DD no larger in {dd} of 4 -> "
              f"{'CARRY FORWARD' if more and dd >= 3 else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
