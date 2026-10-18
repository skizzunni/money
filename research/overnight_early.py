"""Round one hundred and fourteen: the overnight long, 18:00 to 02:00 only, on the user's intraday-trail account.

    python research/overnight_early.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 104: of the overnight windows, 18:00-02:00 was the most consistent across the three data sets (t 1.99 / 2.23 /
1.92, $9.56 / $17.15 / $11.22 a night a contract); round 105 put only the full night on the account (more busts, payouts
per evaluation not reliably higher). The shorter window swings less and is flat hours before the open.
Trade, as round 105 at 18:01 (research/overnight_combo.overnight, delay 1) but out at the 02:00 open: 1 MNQ, stop 50 or
100 points; in the evaluation and funded, or funded only. The strategy now otherwise.
Bar, fixed before running: against now, more $ a week, a pass rate and payouts per evaluation at least as high, and a
first payout within 20 sessions at least as often, in all three periods.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import overnight_combo as O  # noqa: E402
import trap_reversal as T  # noqa: E402

STOPS = (50.0, 100.0)


def job(args):
    path, periods = args
    bars = A.rth(path)
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    cands = M.w_candidates(bars, False)
    sess = list(T.sessions_of(bars))
    ev_day = T.leg_paths(bars, M.combine(bars, ev_bot, cands, False)[0])
    pa_day = T.leg_paths(bars, M.combine(bars, pa_bot, cands, False)[0])
    rows = O.measure(ev_day, pa_day, sess, periods, "now")
    for stop in STOPS:
        night = O.overnight(path, 1, stop, delay=1, end_min=120)
        rows += O.measure(night + ev_day, night + pa_day, sess, periods, f"18:01-02:00, stop {stop:g}")
        rows += O.measure(ev_day, night + pa_day, sess, periods, f"18:01-02:00, stop {stop:g}, funded only")
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    for name in df.setup.unique():
        if name == "now":
            continue
        ok = all(key.loc[(name, p)]["$/week"] > key.loc[("now", p)]["$/week"] and
                 key.loc[(name, p)]["eval pass %"] >= key.loc[("now", p)]["eval pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"] and
                 key.loc[(name, p)]["paid in 20 %"] >= key.loc[("now", p)]["paid in 20 %"]
                 for p in df.period.unique())
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
