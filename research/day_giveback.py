"""Round one hundred and thirteen: a daily give-back stop for the intraday-trail evaluation.

    python research/day_giveback.py nsx1m_scaled.pkl nq1m_scaled.pkl

On the intraday trail the threshold follows the highest equity, open profit included, so profit the day gives back
is cushion lost for good. Round 85 tried trailing stops per trade. This acts on the whole day (bot + breakout): once
the day's equity (closed + open, from the day's start) has been up at least $P, if it falls $G below the day's best,
everything is closed at that level (less $10 of slippage) and the day is over. Profit stays uncapped.
Variants, fixed before running: P $300 or $600 x G $200 or $400, in the evaluation only (the funded account as now),
and the same four on both: 8, plus the strategy now. Merged minute equity per day as round 102
(research/trap_reversal.leg_paths).
Bar, fixed before running: adopted if, against now, the evaluation pass rate is higher and payouts per evaluation are
at least as high in all three periods; if several, the most paid in sum.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_more as M  # noqa: E402
import fast_payout as F  # noqa: E402
import trap_reversal as T  # noqa: E402

SLIP = 10.0
GRID = list(itertools.product((300.0, 600.0), (200.0, 400.0)))


def giveback(days, p, g):
    """Each day's merged path cut at the first minute whose low is $g below the best of the minutes before it, once
    that best has reached $p (the best before the minute: a minute's own high and low come in an unknown order)."""
    out = []
    for day, pnl, hi, lo in days:
        before = np.concatenate([[-np.inf], hi[:-1]])
        hit = np.flatnonzero((before >= p) & (lo <= before - g))
        if hit.size:
            m = hit[0]
            level = before[m] - g - SLIP
            out.append((day, float(level), hi[:m + 1].copy(), np.append(lo[:m], level)))
        else:
            out.append((day, pnl, hi, lo))
    return out


def measure(ev_all, pa_all, sess, periods, name):
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev_all, ss), P.by_day(pa_all, ss)
        starts = [s for s, d in enumerate(ss) if d <= last]
        outs = [A.attempt(ev_days[s:], 1, "intraday", 30) for s in starts]
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
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in ss if d <= last]))
        for dday, pnl, _, _ in ev_all:
            if dday in daily.index:
                daily[dday] += pnl
        r = [o for o, _ in outs]
        rows.append({"period": label, "setup": name, "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                     "eval pass %": 100 * r.count("passed") / len(r), "eval bust %": 100 * r.count("failed") / len(r),
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([f[0] == "paid" for f in f20])})
    return rows


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 3, 1.0, 2.5), cands, False)[0])
    pa = T.leg_paths(bars, M.combine(bars, T.bot_trades(bars, 2, 0.5, 6.25), cands, False)[0])
    rows = measure(ev, pa, sess, periods, "now")
    for p, g in GRID:
        ev_g = giveback(ev, p, g)
        rows += measure(ev_g, pa, sess, periods, f"P {p:.0f} G {g:.0f}, evaluation")
        rows += measure(ev_g, giveback(pa, p, g), sess, periods, f"P {p:.0f} G {g:.0f}, both")
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
    wins = []
    for name in df.setup.unique():
        if name == "now":
            continue
        ok = all(key.loc[(name, p)]["eval pass %"] > key.loc[("now", p)]["eval pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"]
                 for p in df.period.unique())
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in df.period.unique()), name))
    print(f"ADOPT {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
