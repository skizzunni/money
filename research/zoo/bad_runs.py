"""Research (2026-11-25, docs section 121): what a normal bad run looks like on a fresh 50K, each period on its own.

The shipped MNQ rules (gap + band, the size steps, the news rule, the extra contract, the $600 day stop) on fresh
starts each month, 12 months each, exactly as harness.account (checked start by start: same lost flag and profit),
also recording per start: the deepest fall from the highest end-of-day balance, the closest the balance came to the
trailing floor (the cushion's low), the longest run of losing trading days, the most trading days without a new
high, the worst day and the worst 5-day stretch. Prints the median and the worst 10% / worst start.
Run from research/: python zoo/bad_runs.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def runs(t, all_days, steps, day_stop, day_qty, max_q=3):
    """harness.account's loop (no eq / early / extra options), with the path kept."""
    days = [r["d"] for r in all_days]
    byday = {d: g.usd.to_numpy() for d, g in t.groupby("d")}
    adds = {d: g["add"].to_numpy() for d, g in t.groupby("d")}
    idx = pd.Series(range(len(days)), index=pd.to_datetime(days))
    out = []
    for s0 in sorted({x.to_period("M").start_time for x in idx.index}):
        end = s0 + pd.DateOffset(months=12)
        seg = idx[(idx.index >= s0) & (idx.index < end)].to_numpy()
        if len(seg) < 200 or (idx.index[-1] < end - pd.DateOffset(days=10)):
            continue
        bal, high, lost = 50000.0, 50000.0, False
        dd, cush_lo, streak, worst_streak, since_high, worst_since, pls = 0.0, 2000.0, 0, 0, 0, 0, []
        for j in seg:
            d = days[j]
            floor = min(high - 2000.0, 50000.0)
            day_pl, g = 0.0, byday.get(d)
            if g is not None:
                prof = bal - 50000.0
                q = 1
                for lim, qq in steps:
                    if prof >= lim:
                        q = qq
                q = day_qty(d, q)
                if q <= 0:
                    g, q = None, 0
                ad = adds.get(d, np.zeros(0))
                for k_, usd in enumerate(g if g is not None else []):
                    if day_stop and day_pl <= -day_stop:
                        break
                    day_pl += usd * (min(q + int(ad[k_]), max(q, max_q)) if len(ad) and q >= 1 else q)
                    if bal + day_pl <= floor:
                        lost = True
                        break
            bal += day_pl
            if g is not None:
                pls.append(day_pl)
                streak = streak + 1 if day_pl < 0 else 0
                worst_streak = max(worst_streak, streak)
            if lost or bal <= floor:
                lost = True
                break
            cush_lo = min(cush_lo, bal - floor)
            high = max(high, bal)
            dd = max(dd, high - bal)
            since_high = 0 if bal >= high else since_high + (g is not None)
            worst_since = max(worst_since, since_high)
        p = np.array(pls) if pls else np.zeros(1)
        wk = min(p[k:k + 5].sum() for k in range(max(1, len(p) - 4)))
        out.append(dict(lost=lost, profit=bal - 50000.0, dd=dd, cush_lo=cush_lo, streak=worst_streak,
                        no_high=worst_since, worst_day=p.min(), worst_5=wk))
    return pd.DataFrame(out)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        r = runs(t, d, B.STEPS, 600.0, B._news(d))
        ref = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
        assert len(ref) == len(r) and all(a[0] == b and abs(a[1] - c) < 0.01
                                          for a, b, c in zip(ref, r.lost, r.profit, strict=True)), "not as harness"
        q = r.drop(columns="lost").quantile([0.5, 0.9]).T
        print(f"{lab}: {len(r)} fresh starts (matches harness.account start by start), lost {r.lost.mean():.1%}")
        print(f"  deepest fall from the high: median ${q.loc['dd', 0.5]:,.0f}, worst 10% ${q.loc['dd', 0.9]:,.0f}, "
              f"worst ${r.dd.max():,.0f}")
        print(f"  closest to the floor (cushion low): median ${r.cush_lo.median():,.0f}, worst 10% "
              f"${r.cush_lo.quantile(0.1):,.0f}, worst ${r.cush_lo.min():,.0f}")
        print(f"  longest run of losing trading days: median {q.loc['streak', 0.5]:.0f}, worst 10% "
              f"{q.loc['streak', 0.9]:.0f}, worst {r.streak.max():.0f}")
        print(f"  most trading days without a new high: median {q.loc['no_high', 0.5]:.0f}, worst 10% "
              f"{q.loc['no_high', 0.9]:.0f}, worst {r.no_high.max():.0f}")
        print(f"  worst day: median ${r.worst_day.median():,.0f}, worst ${r.worst_day.min():,.0f}; worst 5 trading "
              f"days: median ${r.worst_5.median():,.0f}, worst ${r.worst_5.min():,.0f}", flush=True)


if __name__ == "__main__":
    main()
