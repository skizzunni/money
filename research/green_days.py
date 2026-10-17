"""Round eighty-eight: more $200 days, for a faster first payout on a 50K Apex intraday-trail account.

    python research/green_days.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round eighty-seven: Apex's first payout needs five days of +$200 or more (and +$2,600, no day above half the profit);
the bot ends only 11-16% of days $200 up (22% green, 34-35% red), so whatever the size, five such days rarely come
within ten sessions. Here the bot is bent toward many modest green days instead of a few big ones, keeping its entries
(v1.6 signals, 1-minute bars, lock 1.0 / +2.5, 25-point max loss a trade, take-profit from the fill), and the first
payout race is measured again.

Variants, fixed before running (36): contracts 6, 8, 10 x take-profit 0.25, 0.5 or 1.5 (now) noise units from the
fill x a daily profit stop at +$250 (once the day's closed + open P/L reaches +$250, close at that level less a tick
a contract and stop for the day) or none x losers a day 2 or 3. The profit stop is applied to each trade's minute
equity before anything else (a trade whose minute high takes the day to +$250 is cut there at +$250 less a tick a
contract, and the day's later trades are dropped), so the evaluation and the payout race see the same trades.
Measures, per period (2011-18 discovery; 2019-25; NQ futures 2015-24): share of days ending at +$200 or more, green %,
red %, mean $ a day, worst losing stretch; P(first payout within 10 and within 20 sessions) and P(bust within 10) from
a funded start on every session (research/fast_payout.py first_payout, no further stops); the 50K evaluation's pass and
bust % within 30 days (research/apex25k.py attempt, intraday trail, $3,000 / $2,000).
Pick and bar, fixed before running: among variants with a positive mean $ a day on 2011-18, the one with the highest
P(first payout within 10 sessions) on 2011-18. Adopted only if on 2019-25 AND on NQ futures its P(payout within 10) is
higher than round eighty-seven's pick (6.5% and 5.5%), exceeds its own P(bust within 10), and its mean $ a day is
positive.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import fast_payout as F  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP = 25.0
SLIP1 = 0.25 * A.PV  # a tick, one contract
QS, TPS, XS, LOSERS = (6, 8, 10), (0.25, 0.5, 1.5), (250.0, None), (2, 3)
R87 = {"2019-2025": 6.5, "NQ 2015-2024": 5.5}
PERIODS_IDX = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
PERIODS_NQ = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)


def trades_for(bars, losers, take_profit):
    """1 contract: (session, pnl, running max of minute equity, minute equity) per trade (as lock_apex.trades_for)."""
    cfg = NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=1.0, lock_plus=2.5, take_profit=take_profit)
    res = run(bars, cfg, minutes=1)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for t in res.trades:
        a, b = t.entry_bar, t.exit_bar
        if t.direction > 0:
            hi_path, lo_path = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hi_path, lo_path = t.entry - lo[a:b], t.entry - h[a:b]
        hi_path = np.append(hi_path * A.PV - A.FEE, t.pnl)
        lo_path = np.append(lo_path * A.PV - A.FEE, t.pnl)
        out.append((t.entry_time.tz_convert(A.NY).normalize().tz_localize(None), t.pnl,
                    np.maximum.accumulate(hi_path), lo_path))
    return out


def profit_stopped(trades, q, x):
    """The day-level profit stop applied at 1 contract: once the day's closed + open P/L reaches x / q a contract, the
    trade is closed there less a tick and the day's later trades are dropped. x None: unchanged."""
    if x is None:
        return list(trades)
    level = x / q
    out, day, closed, done = [], None, 0.0, False
    for d, pnl, hi_run, lo_path in trades:
        if d != day:
            day, closed, done = d, 0.0, False
        if done:
            continue
        hit = np.flatnonzero(closed + hi_run >= level)
        if hit.size:
            k = hit[0]
            fill = level - SLIP1 - closed  # this trade's P/L at the stop
            # the trade's equity peaks at the stop level (it is closed there), then the exit at the fill
            new_hi = np.maximum.accumulate(np.append(np.minimum(hi_run[:k + 1], level - closed), fill))
            new_lo = np.append(lo_path[:k + 1], fill)
            out.append((d, fill, new_hi, new_lo))
            done = True
        else:
            out.append((d, pnl, hi_run, lo_path))
            closed += pnl
    return out


def job(args):
    path, periods, losers, tp = args
    bars = A.rth(path)
    base = trades_for(bars, losers, tp)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for q, x in itertools.product(QS, XS):
        tr = profit_stopped(base, q, x)
        for label, first, last_start in periods:
            sess = [d for d in all_sess if d >= pd.Timestamp(first)]
            last = pd.Timestamp(last_start)
            days = P.by_day(tr, sess)
            starts = [s for s, d in enumerate(sess) if d <= last]
            r10 = [F.first_payout(days[s:], q, None, None, 10) for s in starts]
            r20 = [F.first_payout(days[s:], q, None, None, 20) for s in starts]
            ev = [A.attempt(days[s:], q, "intraday", 30)[0] for s in starts]
            in_p = [d for d in sess if d <= last]
            daily = pd.Series(0.0, index=pd.DatetimeIndex(in_p))
            for d, pnl, _, _ in tr:
                if d in daily.index:
                    daily[d] += q * pnl
            eq = daily.cumsum()
            rows.append({"period": label, "MNQ": q, "TP": tp, "profit stop": x or 0, "losers": losers,
                         "days>=200 %": 100 * (daily >= 200).mean(), "green %": 100 * (daily > 0).mean(),
                         "red %": 100 * (daily < 0).mean(), "$/day": daily.mean(),
                         "worst stretch": float((eq.cummax() - eq).max()),
                         "paid in 10 %": 100 * np.mean([r[0] == "paid" for r in r10]),
                         "bust in 10 %": 100 * np.mean([r[0] == "bust" for r in r10]),
                         "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in r20]),
                         "eval pass %": 100 * ev.count("passed") / len(ev),
                         "eval bust %": 100 * ev.count("failed") / len(ev)})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(path, per, lz, tp) for path, per in ((nsx, PERIODS_IDX), (nq, PERIODS_NQ))
            for lz in LOSERS for tp in TPS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    key = ["MNQ", "TP", "profit stop", "losers"]
    pd.set_option("display.width", 250)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        d = df[df.period == label].sort_values("paid in 10 %", ascending=False)
        print(f"\n{label}: top 12 by P(first payout within 10 sessions)")
        print(d.head(12).drop(columns="period").round(1).to_string(index=False))
    disc = df[(df.period == "2011-2018") & (df["$/day"] > 0)].sort_values("paid in 10 %", ascending=False).iloc[0]
    pick = {k: disc[k] for k in key}
    print(f"\npick on 2011-18: {pick} ({disc['paid in 10 %']:.1f}% paid within 10, ${disc['$/day']:.0f}/day)")
    ok = True
    for label in ("2019-2025", "NQ 2015-2024"):
        d = df[df.period == label]
        b = d[np.logical_and.reduce([d[k] == v for k, v in pick.items()])].iloc[0]
        good = (b["paid in 10 %"] > R87[label] and b["paid in 10 %"] > b["bust in 10 %"] and b["$/day"] > 0)
        ok &= good
        print(f"  {label}: paid in 10 {b['paid in 10 %']:.1f}% (round 87: {R87[label]}%), bust in 10 "
              f"{b['bust in 10 %']:.1f}%, ${b['$/day']:.0f}/day, $200 days {b['days>=200 %']:.1f}%: "
              f"{'PASS' if good else 'FAIL'}")
    print(f"  {'ADOPT' if ok else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
