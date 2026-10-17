"""Round eighty-two: the lock dial, tuned for the Apex 50K account instead of $ a day.

    python research/lock_apex.py nsx1m_scaled.pkl nq1m_scaled.pkl

The lock (once a trade is lock_at x the max loss in profit, the stop moves to entry + lock_plus points) was tuned in
earlier rounds for $ a day. On an intraday trailing drawdown, open profit given back raises the threshold for good, so
an earlier lock, or one that keeps more of the move, might pass and pay more even at the same money. Never tested for
that objective.

Variants, fixed before running: lock_at in {0.5, 0.75, 1.0 (now), 1.25} x lock_plus in {2.5 (now), 6.25, 12.5} points:
12 variants, at 4 MNQ, $200 max loss (25 points), 3 losers a day in the evaluation and 2 in the funded account,
take-profit 1.5 noise units from the fill, 1-minute bars (round eighty-one: the strategy runs on a 1-minute chart).
Measures per period (index 2011-18 discovery, 2019-25, NQ futures 2015-24), machinery as research/wick_size.py: winners,
$ a week, the 50K intraday-trail evaluation pass / bust % (apex25k.attempt, $3,000 target, $2,000 trailing drawdown),
payouts per evaluation and all six payouts % (apex_payouts.pa_run, base caps).
Adoption bar, fixed before running: the variant with the highest payouts per evaluation on 2011-18 must beat the current
(1.0, 2.5) by at least 10% in payouts per evaluation on 2019-25 and on NQ futures, with an evaluation pass rate no lower
on both. Also shown, as description: any variant that beats the current in all three periods on both payouts and pass
rate.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP, Q = 25.0, 4
LOCK_AT = (0.5, 0.75, 1.0, 1.25)
LOCK_PLUS = (2.5, 6.25, 12.5)
CURRENT = (1.0, 2.5)


def trades_for(bars, losers, lock_at, lock_plus):
    """As apex25k.trades_for, with the lock as parameters: (session, pnl, running max of minute equity, minute equity)
    per trade, 1 contract."""
    cfg = NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus)
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


def job(args):
    path, lock_at, lock_plus, periods = args
    bars = A.rth(path)
    ev_tr = trades_for(bars, 3, lock_at, lock_plus)
    pa_tr = trades_for(bars, 2, lock_at, lock_plus)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [x for x in all_sess if x >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev_tr, sess), P.by_day(pa_tr, sess)
        starts = passes = busts = six = 0
        paid, memo = [], {}
        for s, day in enumerate(sess):
            if day > last:
                break
            starts += 1
            res, used = A.attempt(ev_days[s:], Q, "intraday", 30)
            busts += res == "failed"
            if res != "passed":
                paid.append(0.0)
                continue
            passes += 1
            fp = s + used
            if fp not in memo:
                pp, end, _ = P.pa_run(pa_days[fp:], Q, P.CAPS["base"])
                memo[fp] = (sum(a for _, a in pp), end == "closed")
            paid.append(memo[fp][0])
            six += memo[fp][1]
        in_p = [x for x in ev_tr if pd.Timestamp(first) <= x[0] <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in in_p:
            if day in daily.index:  # a session without a 09:30 bar (data gap) isn't a start or a session here
                daily[day] += Q * pnl
        rows.append({"period": label, "lock_at": lock_at, "lock_plus": lock_plus,
                     "winners %": 100 * np.mean([x[1] > 0 for x in in_p]),
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "eval pass %": 100 * passes / starts, "eval bust %": 100 * busts / starts,
                     "$ paid per eval": float(np.mean(paid)), "all 6 %": 100 * six / starts})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, la, lp, per) for path, per in ((nsx, idx_p), (nq, nq_p)) for la in LOCK_AT for lp in LOCK_PLUS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["period", "lock_at", "lock_plus"])
    disc = df[df.period == "2011-2018"].sort_values("$ paid per eval", ascending=False).iloc[0]
    best = (disc.lock_at, disc.lock_plus)
    print(f"\nbest on 2011-18: lock_at {best[0]}, lock_plus {best[1]} (${disc['$ paid per eval']:.0f} per evaluation)")
    ok = best != CURRENT
    for p in ("2019-2025", "NQ 2015-2024"):
        b, c = key.loc[(p, *best)], key.loc[(p, *CURRENT)]
        good = b["$ paid per eval"] >= 1.1 * c["$ paid per eval"] and b["eval pass %"] >= c["eval pass %"]
        ok &= good
        print(f"  {p}: ${b['$ paid per eval']:.0f} / {b['eval pass %']:.1f}% against the current "
              f"${c['$ paid per eval']:.0f} / {c['eval pass %']:.1f}%: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")
    periods = ("2011-2018", "2019-2025", "NQ 2015-2024")
    better = [(la, lp) for la in LOCK_AT for lp in LOCK_PLUS if (la, lp) != CURRENT and all(
        key.loc[(p, la, lp)]["$ paid per eval"] > key.loc[(p, *CURRENT)]["$ paid per eval"] and
        key.loc[(p, la, lp)]["eval pass %"] >= key.loc[(p, *CURRENT)]["eval pass %"] for p in periods)]
    print(f"\nbeat the current in all three periods on payouts and pass rate (description): {better or 'none'}")


if __name__ == "__main__":
    main()
