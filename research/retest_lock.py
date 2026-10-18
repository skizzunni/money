"""Round one hundred and twenty-six: the near-misses again, now that the evaluation closes at its target.

    python research/retest_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round 124 found every earlier evaluation result counted a pass only at a trade's close. The variants rejected on
those results that came closest are re-tested against the strategy now WITH close-at-target (research/pass_lock):
  together6   a same-direction breakout taken while the bot is in, at most 6 MNQ in all (rounds 102 / 111)
  lock 0.5    the evaluation's lock at 0.5 max loss, +2.5 (round 112)
  W $300      the breakout at $300 a trade in the evaluation (funded as now)
  VWAP        the bot's VWAP trailing stop, at the checks (round 116), evaluation and funded
  overnight   the 18:01-02:00 long, 1 MNQ, stop 100, evaluation and funded (round 114)
Bar, fixed before running: a variant is adopted if, against the strategy now with close-at-target, it passes more
evaluations and pays at least as much per evaluation in all three periods (2011-18, 2019-25, NQ 2015-24), and
passes at least as many in the 13 months from July 2025. Five variants, so a pass here is checked once more before
it is built in.
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
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import fast_payout as F  # noqa: E402
import overnight_combo as O  # noqa: E402
import pass_lock as PL  # noqa: E402
import trap_reversal as T  # noqa: E402
import vwap_stop as V  # noqa: E402

VARIANTS = ("now", "together6", "lock 0.5", "W $300", "VWAP", "overnight")


def legs(bars, path, name):
    """(evaluation day paths, funded day paths) for a variant."""
    cands = M.w_candidates(bars, False)
    ev_bot = T.bot_trades(bars, 3, 0.5 if name == "lock 0.5" else 1.0, 2.5)
    pa_bot = T.bot_trades(bars, 2, 0.5, 6.25)
    if name == "VWAP":
        ev_bot, pa_bot = V.bot_trades(bars, 3, 1.0, 2.5, "checks"), V.bot_trades(bars, 2, 0.5, 6.25, "checks")
    tog = name == "together6"
    if tog:
        M.MAXQ = 6
    try:
        ev_cands = cands
        if name == "W $300":
            old, C.RISK = C.RISK, 300.0
            try:
                ev_cands = M.w_candidates(bars, False)
            finally:
                C.RISK = old
        ev = T.leg_paths(bars, M.combine(bars, ev_bot, ev_cands, tog)[0])
        pa = T.leg_paths(bars, M.combine(bars, pa_bot, cands, tog)[0])
    finally:
        M.MAXQ = 10
    if name == "overnight":
        night = O.overnight(path, 1, 100.0, delay=1, end_min=120)
        ev, pa = night + ev, night + pa
    return ev, pa


def job(args):
    path, periods, name = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev, pa = legs(bars, path, name)
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
        f20 = [F.first_payout(pa_days[s:], 1, None, None, 20) for s in starts]
        r = [o for o, _ in outs]
        rows.append({"period": label, "setup": name, "pass %": 100 * r.count("passed") / len(r),
                     "bust %": 100 * r.count("failed") / len(r),
                     "sessions to pass": float(np.median([u for o, u in outs if o == "passed"])),
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([f[0] == "paid" for f in f20])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
             ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, v) for path, per in ((nsx, idx_p), (nq, nq_p)) for v in VARIANTS]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    for name in VARIANTS[1:]:
        ok = all(key.loc[(name, p)]["pass %"] > key.loc[("now", p)]["pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        ok &= bool(key.loc[(name, "Jul 2025-Aug 2026")]["pass %"] >= key.loc[("now", "Jul 2025-Aug 2026")]["pass %"])
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
