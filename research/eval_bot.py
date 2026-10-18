"""Round one hundred and twenty-three: the bot's evaluation settings with the breakout on the account.

    python research/eval_bot.py nsx1m_scaled.pkl nq1m_scaled.pkl

The evaluation's bot (4 MNQ, $200, 3 losers a day, lock 1.0 / +2.5) was set before the breakout; round 112 re-tested
only the lock. Grid, fixed before running: contracts 3, 4, 5 (25-point cap) x losers a day 2, 3, 4; the lock, the
breakout ($200) and the funded account as now. The user's intraday-trail evaluation (research/combo_more).
Pick and bar, fixed before running: the highest evaluation pass rate on 2011-18 (ties: more paid per evaluation);
adopted if, against now, it passes more evaluations and pays at least as much per evaluation, on 2019-25 AND NQ.
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

GRID = list(itertools.product((3, 4, 5), (2, 3, 4)))
NOW = (4, 3)


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    pa_legs = M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0]
    ev_trades = {lz: T.bot_trades(bars, lz, 1.0, 2.5) for lz in (2, 3, 4)}
    rows = []
    for q, lz in GRID:
        M.BOTQ = q
        try:
            ev_legs, ev_tr = M.combine(bars, ev_trades[lz], cands, False)
        finally:
            M.BOTQ = 4
        rows += M.evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, f"{q} MNQ, {lz} losers")
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    cols = ["setup", "$/week", "eval pass %", "eval bust %", "$ paid per eval"]
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label][cols].sort_values("eval pass %", ascending=False).round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    d = df[df.period == "2011-2018"].sort_values(["eval pass %", "$ paid per eval"], ascending=False).iloc[0].setup
    now = f"{NOW[0]} MNQ, {NOW[1]} losers"
    print(f"\npick on 2011-18: {d}")
    if d == now:
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key.loc[(d, p)]["eval pass %"] > key.loc[(now, p)]["eval pass %"] and
             key.loc[(d, p)]["$ paid per eval"] >= key.loc[(now, p)]["$ paid per eval"]
             for p in ("2019-2025", "NQ 2015-2024"))
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
