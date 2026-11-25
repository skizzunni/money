"""Research (2026-11-25, docs section 126): a stricter last guard tier under $1,000 above the floor, per period.

Under $1,000 the shipped guard trades strong breaks (1.5 sigma) and the gap trade only (section 50). Variants for
those days: no gap trade, or the first trade of the day only. Calendar starts (bad_runs.runs, the guard on) from
$50,000 / $48,806 / $48,998 against a $48,000 floor; then shuffled years (2,000 runs of 252 days drawn from each
period, the same daily rules). MNQ alone. Run from research/: python zoo/near_floor_tiers.py [--share]
(--share, docs 127: the guard's day stop at 0.15-0.35 of the cushion instead; --stretch, docs 128: the tier's
strong breaks from 1.0-2.0 sigma; --levels, docs 129: the guard from $1,250-2,000, the tier from $750-1,250;
--extras, docs 130: the extra contract's stretch and the news rule; --steps, docs 131: the size steps;
--day-stop, docs 132: the regular day stop.)
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bad_runs as BR  # noqa: E402
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402

STARTS = (50000.0, 48806.0, 48998.0)


def shuffled(t, st, d, n_runs=2000, seed=1, share=0.25, guard=1500.0, below=1000.0, nw=None, steps=None,
             day_stop=600.0):
    """252 days drawn at random (with replacement), the shipped guard as bad_runs.runs; lost share and median."""
    by = {k: (g.usd.to_numpy(), g["add"].to_numpy()) for k, g in t.groupby("d")}
    sb = {k: g.usd.to_numpy() for k, g in st.groupby("d")}
    nf = B._news(d, nw) if nw else B._news(d)
    days = [x["d"] for x in d]
    out = {}
    for start in STARTS:
        rng = np.random.default_rng(seed)
        lost, prof = 0, []
        for _ in range(n_runs):
            bal, high = start, max(50000.0, start)
            for k in rng.integers(0, len(days), 252):
                day = days[k]
                floor = min(high - 2000.0, 50000.0)
                cush = bal - floor
                on = cush < guard
                g, ad = (sb.get(day, np.zeros(0)), None) if on and cush < below else by.get(day, (np.zeros(0), None))
                q = 1
                for lim, qq in (steps or B.STEPS):
                    if bal - 50000.0 >= lim:
                        q = qq
                q = nf(day, q)
                if q <= 0:
                    g = np.zeros(0)
                q = min(q, 1) if on else q
                ds = max(100.0, min(day_stop, share * cush)) if on else day_stop
                pl, dead = 0.0, False
                for j, u in enumerate(g):
                    if pl <= -ds:
                        break
                    a = int(ad[j]) if ad is not None and not on else 0
                    pl += u * min(q + a, max(q, 3))
                    if bal + pl <= floor:
                        dead = True
                        break
                bal += pl
                if dead or bal <= floor:
                    lost += 1
                    break
                high = max(high, bal)
            else:
                prof.append(bal - start)
        out[start] = (lost / n_runs, np.median(prof) if prof else np.nan)
    return out


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
        tiers = (("shipped (strong breaks + the gap trade)", st, 0.25),
                 ("strong breaks, no gap trade", st[st.bar > 1], 0.25),
                 ("strong breaks + gap, first trade a day only", st.groupby("d").head(1), 0.25))
        if "--share" in sys.argv:  # docs 127: the guard's day stop as this share of the cushion ($100-600)
            tiers = tuple((f"day stop {x} x the cushion", st, x) for x in (0.15, 0.2, 0.25, 0.3, 0.35))
        if "--stretch" in sys.argv:  # docs 128: the tier's strong-break stretch instead of 1.5 sigma
            tiers = tuple((f"strong breaks from {x} sigma (+ the gap trade)", H.trades_of(
                S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": x}))), 0.25)
                for x in (1.0, 1.25, 1.5, 1.75, 2.0))
        levels, extras, stepset, dstops = {}, {}, {}, {}
        if "--day-stop" in sys.argv:  # docs 132: the regular day stop with the guard in
            dstops = {f"day stop ${x:,}": float(x) for x in (400, 500, 600, 700, 800)}
            tiers = tuple((name, st, 0.25) for name in dstops)
        if "--steps" in sys.argv:  # docs 131: the size steps with the guard in
            sets_ = (("shipped 2 / 3 from +$2,000 / +$3,500", ((0, 1), (2000, 2), (3500, 3))),
                     ("2 / 3 from +$1,500 / +$3,000", ((0, 1), (1500, 2), (3000, 3))),
                     ("2 / 3 from +$2,500 / +$4,000", ((0, 1), (2500, 2), (4000, 3))),
                     ("2 / 3 from +$2,000 / +$3,000", ((0, 1), (2000, 2), (3000, 3))),
                     ("2 / 3 from +$2,000 / +$4,500", ((0, 1), (2000, 2), (4500, 3))))
            tiers = tuple((name, st, 0.25) for name, _ in sets_)
            stepset = dict(sets_)
        if "--extras" in sys.argv:  # docs 130: the extra contract's stretch and the news rule, the guard in
            stretch = B._stretch(d, t, 1.0)
            rows = [("shipped (extra contract from 1.5 sigma, news 2-3x skip / 6x +1)", 1.5, None),
                    ("no extra contract", 99.0, None)] + [(f"extra contract from {x} sigma", x, None)
                                                           for x in (1.25, 1.75, 2.0)]
            lo, hi, big = B.NEWS
            rows += [("no mild-news skip", 1.5, (0.0, 0.0, big)), ("no 6x news contract", 1.5, (lo, hi, 1e9)),
                     ("skip 1.75-3x", 1.5, (1.75, hi, big)), ("skip 2-4x", 1.5, (lo, 4.0, big))]
            tiers = tuple((name, st, 0.25) for name, _x, _n in rows)
            extras = {name: (x, nw) for name, x, nw in rows}
            base_add = t["add"].copy()
        if "--levels" in sys.argv:  # docs 129: the guard's trigger and the strong-only tier's level
            combos = ((1500, 1000), (1250, 1000), (1750, 1000), (2000, 1000), (1500, 750), (1500, 1250))
            tiers = tuple((f"guard under ${g:,}, strong only under ${b:,}", st, 0.25) for g, b in combos)
            levels = {f"guard under ${g:,}, strong only under ${b:,}": (float(g), float(b)) for g, b in combos}
        for name, tier, share in tiers:
            gl, bl = levels.get(name, (1500.0, 1000.0))
            ax, nw = extras.get(name, (None, None))
            if ax is not None:
                t["add"] = (stretch >= ax).astype(int)
            nf = B._news(d, nw) if nw else B._news(d)
            stp = stepset.get(name, B.STEPS)
            dsx = dstops.get(name, 600.0)
            cal = []
            for start in STARTS:
                r = BR.runs(t, d, stp, dsx, nf, strong=tier, guard=gl, strong_below=bl,
                            start=start, share=share)
                cal.append(f"${start:,.0f} {r.lost.mean():.1%} / ${r.profit.median():,.0f}")
            sh = shuffled(t, tier, d, share=share, guard=gl, below=bl, nw=nw, steps=stp, day_stop=dsx)
            shs = " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in sh.items())
            if extras:
                t["add"] = base_add
            print(f"{lab} {name}:\n   calendar (lost / median 12-month profit): {' | '.join(cal)}\n"
                  f"   shuffled years: {shs}", flush=True)


if __name__ == "__main__":
    main()
