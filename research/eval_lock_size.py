"""Round eighty-four: the evaluation's lock and size together, for the pass rate.

    python research/eval_lock_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round eighty-two: arming the lock at 0.5 max loss cut evaluation busts by 6-12 points but more evaluations ran out of
time (30 days, no resets on Apex). A little more size makes the $3,000 target faster. Candidates, fixed before running
(evaluation only; 25-point cap, so $ max loss = contracts x $50; 3 losers a day): contracts 4, 5, 6 x lock (1.0, +2.5),
(0.5, +2.5), (0.5, +6.25): 9 variants, (4, 1.0, +2.5) being the current one. The funded account runs as the strategy
does now (4 MNQ, $200, 2 losers, lock 0.5 / +6.25).
Adoption bar, fixed before running: the variant with the highest evaluation pass rate on 2011-18 must beat the current
one by at least 2 points of pass rate on 2019-25 AND on NQ futures 2015-24, with payouts per evaluation no lower on
both. Measures as round eighty-three.
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
import lock_apex as L  # noqa: E402

SIZES = (4, 5, 6)
LOCKS = ((1.0, 2.5), (0.5, 2.5), (0.5, 6.25))
CURRENT = (4, 1.0, 2.5)
PA = (4, 0.5, 6.25)  # the funded account as the strategy trades it now


def job(args):
    path, periods = args
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    ev = {lk: L.trades_for(bars, 3, *lk) for lk in LOCKS}
    pa_tr = L.trades_for(bars, 2, PA[1], PA[2])
    rows = []
    for label, first, last_start in periods:
        sess = [x for x in all_sess if x >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        pa_days = P.by_day(pa_tr, sess)
        memo = {}
        for lk, tr in ev.items():
            ev_days = P.by_day(tr, sess)
            for q in SIZES:
                n = passes = busts = 0
                paid = []
                for s, day in enumerate(sess):
                    if day > last:
                        break
                    n += 1
                    res, used = A.attempt(ev_days[s:], q, "intraday", 30)
                    busts += res == "failed"
                    if res != "passed":
                        paid.append(0.0)
                        continue
                    passes += 1
                    fp = s + used
                    if fp not in memo:
                        memo[fp] = sum(a for _, a in P.pa_run(pa_days[fp:], PA[0], P.CAPS["base"])[0])
                    paid.append(memo[fp])
                rows.append({"period": label, "MNQ": q, "lock": f"{lk[0]} / +{lk[1]}",
                             "eval pass %": 100 * passes / n, "eval bust %": 100 * busts / n,
                             "timeout %": 100 * (n - passes - busts) / n, "$ paid per eval": float(np.mean(paid))})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["period", "MNQ", "lock"])
    cur = (CURRENT[0], f"{CURRENT[1]} / +{CURRENT[2]}")
    d = df[df.period == "2011-2018"].sort_values("eval pass %", ascending=False).iloc[0]
    best = (d.MNQ, d.lock)
    print(f"\nbest on 2011-18: {best[0]} MNQ, lock {best[1]} ({d['eval pass %']:.1f}% pass)")
    ok = best != cur
    for p in ("2019-2025", "NQ 2015-2024"):
        b, c = key.loc[(p, *best)], key.loc[(p, *cur)]
        good = b["eval pass %"] >= c["eval pass %"] + 2 and b["$ paid per eval"] >= c["$ paid per eval"]
        ok &= good
        print(f"  {p}: pass {b['eval pass %']:.1f}% vs {c['eval pass %']:.1f}%, paid ${b['$ paid per eval']:.0f} vs "
              f"${c['$ paid per eval']:.0f}: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
