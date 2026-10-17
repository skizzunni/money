"""Round ninety-five: re-enter the same way after a quick stop-out, added to the bot (MNQ, one 50K Apex account).

    python research/reentry.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round ninety-four (research/trap_reversal.py) found that REVERSING after the bot is stopped out quickly reliably loses
(t -2.2 to -4.8 on all three data sets for the fixed-stop versions). The mirror: the breakout resumes after the
shake-out, so RE-ENTER IN THE ORIGINAL DIRECTION. This hypothesis comes from seeing round ninety-four's results on
every period, so there is no untouched holdout; the bar is strict and the result is to be read with that in mind.

Rules, fixed before running (6): the bot as it trades the evaluation (v1.6, 1-minute bars, 25-point max loss, take-
profit 1.5 from the fill, lock 1.0 / +2.5, 3 losers). A failed trade: closed by its line stop or max loss within N
minutes of its fill, N = 3, 10 or any time. The re-entry: the SAME direction, at the open of the next minute (+1
tick), same session, before 15:59; at most one a day (the day's first qualifying failure, taken or not). Stop a
fixed 25 points from the fill; target 1R or 2R (25 or 50 points), a limit filled a tick through; the stop counts
first when a minute reaches both; flat at the last minute before 16:00. 4 MNQ, $1.24 round trip a contract, a tick
of slippage on market and stop fills. The bot is unchanged; the re-entry is a separate position (minute equity
summed when they overlap).
Same simulation code as round ninety-four (research/trap_reversal.py's simulate and Apex machinery).
Bar, fixed before running: a rule counts only if its re-entries alone (daily P/L, every session) are positive with
t >= 3.0 on index 2011-18 AND t >= 2.5 on index 2019 - Sep 2026 AND t >= 2.0 on NQ futures 2015-2025. For a rule that
counts: bot + re-entry against the bot alone (winners, $ a week, worst losing stretch, green / red days, the 50K
intraday-trail evaluation pass / bust %, payouts per evaluation with the funded bot at lock 0.5 / +6.25 and 2 losers
and re-entries in the funded account too, the funded first payout within 20 and 40 sessions). Adopted only if payouts
per evaluation are higher and the pass rate no lower in all three periods.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import trap_reversal as T  # noqa: E402

RULES = list(itertools.product((3, 10, None), ("fixed",), (1.0, 2.0)))


def reentries(bars, trades, rule):
    """The re-entry trades for one rule (same structure as trap_reversal.reversals)."""
    n, _, k = rule
    o, h = bars.open.to_numpy(float), bars.high.to_numpy(float)
    lo, c = bars.low.to_numpy(float), bars.close.to_numpy(float)
    idx = bars.index.tz_convert(A.NY)
    last = T.session_last(idx)
    days = idx.normalize().tz_localize(None)
    tmin = idx.hour * 60 + idx.minute
    out, done = [], set()
    for t in trades:
        if t.reason not in ("Back inside", "Max loss"):
            continue
        mins = (t.exit_time - t.entry_time).total_seconds() / 60
        if n is not None and mins > n:
            continue
        e = t.exit_bar + 1
        if e >= len(bars) or days[e] != days[t.exit_bar] or tmin[e] >= 959:
            continue
        day = days[e]
        if day in done:
            continue
        d = t.direction
        stop = o[e] + d * T.TICK - d * T.CAP
        r = T.simulate(o, h, lo, c, e, last, d, stop, k)
        done.add(day)
        if r is None:
            continue
        entry, b, xp, pnl, hi_p, lo_p = r
        out.append({"day": day, "entry_bar": e, "exit_bar": b, "dir": d, "entry": entry, "exit": xp, "pnl": pnl,
                    "hi": hi_p, "lo": lo_p})
    return out


T.reversals = reentries  # trap_reversal's Apex machinery picks the re-entries up (set before the workers fork)


def disc_job(args):
    path, periods = args
    bars = A.rth(path)
    trades = T.bot_trades(bars, 3, 1.0, 2.5)
    sess = T.sessions_of(bars)
    out = []
    for rule in RULES:
        revs = reentries(bars, trades, rule)
        for label, y0, y1 in periods:
            out.append({"period": label, "rule": T.rule_name(rule), **T.stat(revs, sess, y0, y1)})
    return out


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 220)
    idx_p = (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026))
    nq_p = (("NQ 2015-2025", 2015, 2025),)
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(disc_job, [(nsx, idx_p), (nq, nq_p)]) for r in rows])
    print("Re-entries alone, 4 MNQ, every period")
    print(df.round(3).to_string(index=False))
    bars_t = {"2011-2018": 3.0, "2019-2026": 2.5, "NQ 2015-2025": 2.0}
    final = []
    for rule in RULES:
        name = T.rule_name(rule)
        ok = all(df[(df.period == p) & (df.rule == name)].iloc[0].t >= b for p, b in bars_t.items())
        print(f"{name}: {'COUNTS' if ok else 'does not count'}")
        if ok:
            final.append(rule)
    for rule in final:
        jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30")), rule),
                (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),), rule)]
        with ProcessPoolExecutor(max_workers=2) as pool:
            comb = pd.DataFrame([r for rows in pool.map(T.apex_job, jobs) for r in rows])
        comb["setup"] = comb["setup"].str.replace("reversal", "re-entry")
        print(f"\n{T.rule_name(rule)}: bot + re-entry against the bot alone")
        print(comb.round(1).to_string(index=False))
        piv = comb.set_index(["period", "setup"])
        adopt = all(piv.loc[(p, "bot + re-entry"), "$ paid per eval"] > piv.loc[(p, "bot"), "$ paid per eval"] and
                    piv.loc[(p, "bot + re-entry"), "eval pass %"] >= piv.loc[(p, "bot"), "eval pass %"]
                    for p in comb.period.unique())
        print(f"  {'ADOPT' if adopt else 'NOT ADOPTED'}")
    if not final:
        print("\nNo rule counts: nothing to add.")


if __name__ == "__main__":
    main()
