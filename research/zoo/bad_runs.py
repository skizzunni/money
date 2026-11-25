"""Research (2026-11-25, docs section 121): what a normal bad run looks like on a fresh 50K, each period on its own.

The shipped MNQ rules (gap + band, the size steps, the news rule, the extra contract, the $600 day stop) on fresh
starts each month, 12 months each, exactly as harness.account (checked start by start: same lost flag and profit),
also recording per start: the deepest fall from the highest end-of-day balance, the closest the balance came to the
trailing floor (the cushion's low), the longest run of losing trading days, the most trading days without a new
high, the worst day and the worst 5-day stretch. Prints the median and the worst 10% / worst start.
Run from research/: python zoo/bad_runs.py [--gold PATH/gold5.pkl] [--guard] [--start 48998]
(gold first in the day, sized like MNQ, no day stop of its own, as harness.account's extra leg).
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


def runs(t, all_days, steps, day_stop, day_qty, max_q=3, extra=None, strong=None, guard=0.0, strong_below=0.0,
         start=50000.0, share=0.25):
    """harness.account's loop (no eq / early options; extra: gold, first in the day, from +$0), with the path kept.
    guard (docs 38 / 50, as MnqCleanBand / MgcOvernightCarry): at a day's start under `guard` $ above the floor, 1
    contract (no extra or news contract), a day stop of a quarter of the cushion ($100-600) and no gold; under
    `strong_below` $ the day's trades from `strong` (the strategy run with min_stretch 1.5: strong breaks and the gap
    trade only). guard 0: exactly harness.account. start (docs 125): the start balance (the floor from a $50,000 high,
    so $48,000; the size steps from the $50,000 the account was opened with)."""
    days = [r["d"] for r in all_days]
    byday = {d: g.usd.to_numpy() for d, g in t.groupby("d")}
    stday = {d: g.usd.to_numpy() for d, g in strong.groupby("d")} if strong is not None else {}
    exday = {d: g.usd.to_numpy() for d, g in extra.groupby("d")} if extra is not None else {}
    adds = {d: g["add"].to_numpy() for d, g in t.groupby("d")}
    idx = pd.Series(range(len(days)), index=pd.to_datetime(days))
    out = []
    for s0 in sorted({x.to_period("M").start_time for x in idx.index}):
        end = s0 + pd.DateOffset(months=12)
        seg = idx[(idx.index >= s0) & (idx.index < end)].to_numpy()
        if len(seg) < 200 or (idx.index[-1] < end - pd.DateOffset(days=10)):
            continue
        bal, high, lost = start, max(50000.0, start), False
        own_high = start  # the fall is from the account's own best close since this start (= high on fresh starts)
        dd, cush_lo, streak, worst_streak, since_high, worst_since, pls = 0.0, start - 48000.0, 0, 0, 0, 0, []
        to15 = 0 if start - 48000.0 >= 1500.0 else np.nan  # docs 125: sessions until the cushion is back to $1,500
        to2 = to3 = np.nan  # docs 124: sessions until the first close at +$2,000 / +$3,500 (2 / 3 contracts next day)
        for n_, j in enumerate(seg, 1):
            d = days[j]
            floor = min(high - 2000.0, 50000.0)
            cush = bal - floor
            on = bool(guard) and cush < guard
            day_pl, g = 0.0, (stday.get(d) if on and cush < strong_below else byday.get(d))
            ds = max(100.0, min(day_stop, share * cush)) if on else day_stop  # share: docs 127
            # gold as harness.account's extra leg (extra_from 0: while not under the start); none while guarded
            if d in exday and bal - 50000.0 >= 0.0 and not on:
                g = np.concatenate([exday[d], g]) if g is not None else exday[d]
            if g is not None:
                prof = bal - 50000.0
                q = 1
                for lim, qq in steps:
                    if prof >= lim:
                        q = qq
                q = day_qty(d, q)
                if q <= 0:
                    g, q = None, 0
                q = min(q, 1) if on else q
                ad = adds.get(d, np.zeros(0)) if not on else np.zeros(0)
                ad = np.concatenate([np.zeros(len(g) - len(ad)), ad]) if g is not None and len(ad) < len(g) else ad
                for k_, usd in enumerate(g if g is not None else []):
                    if ds and day_pl <= -ds:
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
            if to15 != to15 and bal - min(high - 2000.0, 50000.0) >= 1500.0:
                to15 = n_
            if to2 != to2 and bal - 50000.0 >= 2000.0:
                to2 = n_
            if to3 != to3 and bal - 50000.0 >= 3500.0:
                to3 = n_
            high = max(high, bal)
            own_high = max(own_high, bal)
            dd = max(dd, own_high - bal)
            since_high = 0 if bal >= own_high else since_high + (g is not None)
            worst_since = max(worst_since, since_high)
        p = np.array(pls) if pls else np.zeros(1)
        wk = min(p[k:k + 5].sum() for k in range(max(1, len(p) - 4)))
        out.append(dict(lost=lost, profit=bal - start, to15=to15, dd=dd, cush_lo=cush_lo, streak=worst_streak,
                        no_high=worst_since, worst_day=p.min(), worst_5=wk, to2=to2, to3=to3))
    return pd.DataFrame(out)


def gold_trades(path):
    import mk_search as K
    G = pickle.load(open(path, "rb"))
    for g in G:
        for k in ("o", "h", "l", "c"):
            g[k] = np.round(np.asarray(g[k]), 1)
    rows = [(G[i]["d"], (x - e) * side * 10 - 1.24)
            for i in range(15, len(G)) for side, _k, e, x, _w, _b in K.carry(G, i, 0.1)]
    return pd.DataFrame(rows, columns=["d", "usd"])


def main():
    sets = pickle.load(open(B.PK, "rb"))
    gold = gold_trades(sys.argv[sys.argv.index("--gold") + 1]) if "--gold" in sys.argv else None
    guard = "--guard" in sys.argv  # docs 123: the shipped cushion guard ($1,500; strong breaks only under $1,000)
    start = float(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 50000.0  # docs 125
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        ref = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d), extra=gold)
        r = runs(t, d, B.STEPS, 600.0, B._news(d), extra=gold)
        assert len(ref) == len(r) and all(a[0] == b and abs(a[1] - c) < 0.01
                                          for a, b, c in zip(ref, r.lost, r.profit, strict=True)), "not as harness"
        if guard:
            st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
            r = runs(t, d, B.STEPS, 600.0, B._news(d), extra=gold, strong=st, guard=1500.0, strong_below=1000.0,
                     start=start)
            lab += " with the cushion guard"
        elif start != 50000.0:
            r = runs(t, d, B.STEPS, 600.0, B._news(d), extra=gold, start=start)
        if start != 50000.0:
            lab += f" from ${start:,.0f} (floor $48,000)"
        q = r.drop(columns="lost").quantile([0.5, 0.9]).T
        what = f"{lab}{' MNQ + gold' if gold is not None else ''}"
        kind = "fresh starts (matches" if start == 50000.0 else "starts (the plain fresh run matches"
        print(f"{what}: {len(r)} {kind} harness.account start by start with the guard off), "
              f"lost {r.lost.mean():.1%}")
        print(f"  deepest fall from the high: median ${q.loc['dd', 0.5]:,.0f}, worst 10% ${q.loc['dd', 0.9]:,.0f}, "
              f"worst ${r.dd.max():,.0f}")
        print(f"  closest to the floor (cushion low): median ${r.cush_lo.median():,.0f}, worst 10% "
              f"${r.cush_lo.quantile(0.1):,.0f}, worst ${r.cush_lo.min():,.0f}")
        print(f"  longest run of losing trading days: median {q.loc['streak', 0.5]:.0f}, worst 10% "
              f"{q.loc['streak', 0.9]:.0f}, worst {r.streak.max():.0f}")
        print(f"  most trading days without a new high: median {q.loc['no_high', 0.5]:.0f}, worst 10% "
              f"{q.loc['no_high', 0.9]:.0f}, worst {r.no_high.max():.0f}")
        print(f"  worst day: median ${r.worst_day.median():,.0f}, worst ${r.worst_day.min():,.0f}; worst 5 trading "
              f"days: median ${r.worst_5.median():,.0f}, worst ${r.worst_5.min():,.0f}")
        for col, lv in (("to15", "a $1,500 cushion (the guard off)"), ("to2", "+$2,000 (2 contracts)"),
                        ("to3", "+$3,500 (3 contracts)")):
            x = r[col].fillna(np.inf)  # not reached in the 12 months counts as slowest
            def f(v):
                return "not reached" if v == np.inf else f"{v:.0f}"
            md, q75 = x.quantile(0.5, interpolation="higher"), x.quantile(0.75, interpolation="higher")
            print(f"  sessions to {lv}: median {f(md)}, 75% of starts within {f(q75)}, slowest {f(x.max())}; "
                  f"not in 12 months {np.isinf(x).mean():.0%}", flush=True)


if __name__ == "__main__":
    main()
