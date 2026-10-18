"""Round one hundred and twenty-two: the bot's funded settings again, now that the breakout shares the account.

    python research/funded_bot.py nsx1m_scaled.pkl nq1m_scaled.pkl

The funded bot (4 MNQ, $200, 2 losers a day, lock 0.5 / +6.25) was set in rounds 61 and 83, before the breakout.
Grid, fixed before running (25-point cap, so $ max loss = contracts x $50; the breakout at $200 as now; the evaluation
as now): contracts 3, 4, 5 x losers a day 2, 3 x lock (0.5, +6.25) or (1.0, +2.5): 12.
Pick and bar, fixed before running: the most $ paid per evaluation on 2011-18; adopted if, against now, it pays more
per evaluation and brings a first payout within 20 sessions at least as often, on 2019-25 AND NQ 2015-24.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

GRID = list(itertools.product((3, 4, 5), (2, 3), ((0.5, 6.25), (1.0, 2.5))))
NOW = (4, 2, (0.5, 6.25))


def name_of(g):
    q, lz, (la, lp) = g
    return f"{q} MNQ, {lz} losers, lock {la}/+{lp}"


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev_legs, ev_tr = M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)
    pa_trades = {(lz, lk): T.bot_trades(bars, lz, *lk) for lz in (2, 3) for lk in ((0.5, 6.25), (1.0, 2.5))}
    rows = []
    for g in GRID:
        q, lz, lk = g
        M.BOTQ = q
        try:
            pa_legs = M.combine(bars, pa_trades[(lz, lk)], cands, False)[0]
        finally:
            M.BOTQ = 4
        rows += M.evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name_of(g))
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    cols = ["setup", "$ paid per eval", "paid in 20 %"]
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label][cols].sort_values("$ paid per eval", ascending=False).round(1)
              .to_string(index=False))
    key = df.set_index(["setup", "period"])
    disc = df[df.period == "2011-2018"].sort_values("$ paid per eval", ascending=False).iloc[0].setup
    now = name_of(NOW)
    print(f"\npick on 2011-18: {disc}")
    if disc == now:
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key.loc[(disc, p)]["$ paid per eval"] > key.loc[(now, p)]["$ paid per eval"] and
             key.loc[(disc, p)]["paid in 20 %"] >= key.loc[(now, p)]["paid in 20 %"]
             for p in ("2019-2025", "NQ 2015-2024"))
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
