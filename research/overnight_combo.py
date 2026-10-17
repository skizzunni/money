"""Round one hundred and five: the overnight long added to the strategy (bot + breakout), on one Apex 50K account.

    python research/overnight_combo.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round one hundred and four (research/overnight_drift.py): long from 18:00 to the 09:30 open made money on every data
set ($26 / $22 / $15 a night a contract after costs, up on 54-57% of nights) but its t on the two later sets, 1.75
and 1.62, missed that round's bar of 2. The effect is a published one (Boyarchenko, Larsen and Whelan 2023), not mined
here, and it trades while the account is otherwise flat; whether it helps on the account is what matters.
Apex's trading day runs from 18:00 to 16:59, so the night before a session belongs to that session's Apex day: the
overnight trade comes first in the day, then the bot and the breakout (research/combo_more.evaluate's legs, the
strategy as it is now), with the drawdown, the daily loss limit and the payout days counted over the whole Apex day.
Overnight trade: long q MNQ at the open of the first minute at or after 18:00 (plus a tick), a stop S points below
the fill (filled at the stop or the minute's open if worse, less a tick), else out at the 09:30 open less a tick;
$1.24 fees a contract. Nights crossing a month end: no trade (rescaled index data's monthly gap).
Variants, fixed before running: q 1 or 2 x S 75 or 150 points (at 1 MNQ $150 / $300 of risk), and none.
Pick and bar, fixed before running: on 2011-18 the variant with the most $ paid per evaluation; adopted if, against
none (the strategy now), it has more $ a week, an evaluation pass rate and payouts per evaluation at least as high and
a first payout within 20 sessions at least as often, on 2019-25 AND NQ futures 2015-24.
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

TICK, PV, FEE = 0.25, 2.0, 1.24
VARIANTS = [None] + list(itertools.product((1, 2), (75.0, 150.0)))
FUNDED_ONLY = False  # also each variant on the funded account only (the evaluation as now)


def overnight(path, q, stop_pts, delay=0):
    """Per night: (session date d', pnl, running max of minute equity, minute equity), $ at q contracts. delay 1:
    enter a bar later (at the close of the first bar from 18:00, as the NinjaTrader strategy can)."""
    bars = pd.read_pickle(path)
    idx = bars.index.tz_convert(A.NY)
    ns = idx.as_unit("ns").asi8
    o, h, lo = (bars[x].to_numpy(float) for x in ("open", "high", "low"))
    tmin = idx.hour * 60 + idx.minute
    sess = idx[tmin == 570].normalize().unique()
    out = []
    for k in range(1, len(sess)):
        d, d2 = sess[k - 1], sess[k]
        if d.month != d2.month:
            continue
        t1, t2 = (d2 - pd.Timedelta(hours=6)).value, (d2 + pd.Timedelta(minutes=570)).value
        j1, j2 = int(np.searchsorted(ns, t1)), int(np.searchsorted(ns, t2))
        if j1 >= len(ns) or j2 >= len(ns) or ns[j1] - t1 > 5 * 60 * 10**9 or ns[j2] - t2 > 5 * 60 * 10**9 or j2 <= j1:
            continue
        j1 += delay
        entry = o[j1] + TICK
        stop = entry - stop_pts
        x, px = j2, o[j2] - TICK
        for m in range(j1, j2):
            if lo[m] <= stop:
                x, px = m, min(o[m], stop) - TICK
                break
        pnl = q * ((px - entry) * PV - FEE)
        hi = np.append(q * ((h[j1:x] - entry) * PV - FEE), pnl)
        lp = np.append(q * ((lo[j1:x] - entry) * PV - FEE), pnl)
        out.append((d2.tz_localize(None), pnl, np.maximum.accumulate(hi), lp))
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
        ss_p = [d for d in ss if d <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex(ss_p))
        for dday, pnl, _, _ in ev_all:
            if dday in daily.index:
                daily[dday] += pnl
        eq = daily.cumsum()
        res = [r for r, _ in outs]
        rows.append({"period": label, "setup": name,
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "eval pass %": 100 * res.count("passed") / len(res),
                     "eval bust %": 100 * res.count("failed") / len(res),
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in f20])})
    return rows


def job(args):
    path, periods = args
    bars = A.rth(path)
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    cands = M.w_candidates(bars, False)
    sess = list(T.sessions_of(bars))
    ev_legs, _ = M.combine(bars, ev_bot, cands, False)
    pa_legs, _ = M.combine(bars, pa_bot, cands, False)
    ev_day, pa_day = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
    rows = []
    for v in VARIANTS:
        night = overnight(path, *v) if v else []
        name = "none (now)" if v is None else f"{v[0]} MNQ, stop {v[1]:g}"
        # the night first in each Apex day, then the regular session
        rows += measure(night + ev_day, night + pa_day, sess, periods, name)
        if v is not None and FUNDED_ONLY:
            rows += measure(ev_day, night + pa_day, sess, periods, name + ", funded only")
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
    disc = df[(df.period == "2011-2018") & (df.setup != "none (now)")]
    pick = disc.sort_values("$ paid per eval", ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {pick}")
    ok = True
    for p in ("2019-2025", "NQ 2015-2024"):
        v, b = key.loc[(pick, p)], key.loc[("none (now)", p)]
        good = bool(v["$/week"] > b["$/week"] and v["eval pass %"] >= b["eval pass %"] and
                    v["$ paid per eval"] >= b["$ paid per eval"] and v["paid in 20 %"] >= b["paid in 20 %"])
        ok &= good
        print(f"  {p}: {'PASS' if good else 'FAIL'}")
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
