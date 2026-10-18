"""Round one hundred and seventeen: the breakout's shorts, smaller or dropped.

    python research/w_long.py nsx1m_scaled.pkl nq1m_scaled.pkl

The breakout as the strategy trades it (in the bot's gaps), $ a trade, longs / shorts: 2011-18 +24.1 (t 2.36) /
+8.5 (t 0.88); 2019-25 +16.6 / +15.1; July 2025-2026 +14.2 / -4.1; NQ 2015-24 +28.7 (t 2.72) / +5.3 (t 0.59). The
bot's shorts are weaker than its longs in 2019-25 and on NQ but not in 2011-18, the period kept for finding things,
so only the breakout is changed here. Variants, fixed before running: the breakout's shorts at half risk ($100, at
least 1 MNQ), or no breakout shorts. The strategy now otherwise, the user's intraday-trail evaluation
(research/combo_more.evaluate).
Bar, fixed before running: adopted if, against now, the pass rate and payouts per evaluation are at least as high,
and one of them higher, on 2019-25 AND NQ 2015-24 (2011-18 showed the pattern, so it isn't a test); the 13 months from
July 2025 are reported too.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

SETUPS = ("now", "shorts at half risk", "no breakout shorts")


def variant(cands, name):
    out = []
    for day_legs in cands:
        w = day_legs[0]
        if w["d"] > 0 or name == "now":
            out.append(day_legs)
        elif name == "shorts at half risk":
            q = max(1, math.floor(w["q"] / 2))  # half the contracts: half the $ risk (at least 1 MNQ)
            out.append([dict(w, q=q)])
        # "no breakout shorts": the day has no breakout trade
    return out


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev, pa = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    rows = []
    for name in SETUPS:
        rows += M.evaluate(bars, sess, ev, pa, variant(cands, name), False, periods, name)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 230)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    for name in SETUPS[1:]:
        ok = True
        for p in ("2019-2025", "NQ 2015-2024"):
            v, b = key.loc[(name, p)], key.loc[("now", p)]
            ok &= bool(v["eval pass %"] >= b["eval pass %"] and v["$ paid per eval"] >= b["$ paid per eval"] and
                       (v["eval pass %"] > b["eval pass %"] or v["$ paid per eval"] > b["$ paid per eval"]))
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
