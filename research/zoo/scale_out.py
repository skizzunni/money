# ruff: noqa
"""Research round (2026-11-24): one contract off early (at scale_r x the $200 hard stop) when 2-3 contracts trade,
the rest to the shipped 2.5x target / stops. Exact per trade given the shipped trade: the early contract shares the
stop path (break-even included) until its target, so it exits at its target if price trades a tick through it before the
shipped exit (bars from the fill to the bar before the exit; the exit bar only when the exit was the 2.5x target),
else with the rest."""
import sys, pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd
import bench as B, strats as S, harness as H
sets = pickle.load(open(B.PK, "rb"))
tick, pv = H.SPEC["MNQ"]; FEE = H.FEE
def trades(days):
    rows = []
    legs = (("gap_go", B.GAP), ("noise", B.BAND))
    for i in range(len(days)):
        for tr in S.everyday(days, i, tick=tick, legs=legs) or []:
            side, eb, e, x, why, xb = tr[:6]
            d = days[i]
            hi = d["h"] if side > 0 else d["l"]
            last = xb + 1 if why == "target" else xb
            ext = [side * (hi[b] - e) for b in range(eb, max(eb, last))]
            rows.append((d["d"], side, eb, (x - e) * side * pv - 2 * FEE, why, max(ext) if ext else 0.0))
    return pd.DataFrame(rows, columns=["d", "side", "bar", "usd", "why", "mfe"])
def early_col(t, r, gap_too):
    pts = round(r * 200.0 / pv / tick) * tick
    hit = t.mfe >= pts + tick
    if not gap_too: hit &= t.bar > 1
    return np.where(hit, pts * pv - 2 * FEE, t.usd)
def account(t, all_days, steps, day_stop, day_qty, max_q=3):
    days = [r["d"] for r in all_days]
    g_ = {d: (g.usd.to_numpy(), g.early.to_numpy(), g["add"].to_numpy()) for d, g in t.groupby("d")}
    idx = pd.Series(range(len(days)), index=pd.to_datetime(days))
    starts = sorted({x.to_period("M").start_time for x in idx.index})
    res = []
    for s0 in starts:
        end = s0 + pd.DateOffset(months=12)
        seg = idx[(idx.index >= s0) & (idx.index < end)].to_numpy()
        if len(seg) < 200 or (idx.index[-1] < end - pd.DateOffset(days=10)): continue
        bal, high, lost = 50000.0, 50000.0, False
        for j in seg:
            d = days[j]; floor = min(high - 2000.0, 50000.0); day_pl = 0.0
            g = g_.get(d)
            if g is not None:
                prof = bal - 50000.0; q = 1
                for lim, qq in steps:
                    if prof >= lim: q = qq
                q = day_qty(d, q)
                if q > 0:
                    for usd, ea, ad in zip(*g):
                        if day_stop and day_pl <= -day_stop: break
                        n = min(q + int(ad), max(q, max_q))
                        day_pl += usd * n + ((ea - usd) if n >= 2 else 0.0)
                        if bal + day_pl <= floor: lost = True; break
            bal += day_pl
            if lost or bal <= floor: lost = True; break
            high = max(high, bal)
        res.append((lost, bal - 50000.0))
    return res
def tv(d, t, start="2026-08-27"):
    t = t.copy(); t["d"] = pd.to_datetime(t.d)
    cum, n = 0.0, 0
    for i in range(21, len(d)):
        day = pd.Timestamp(d[i]["d"])
        if day < pd.Timestamp(start): continue
        sp = d[i]["news"][0]; q = 1
        for lim, qq in B.STEPS:
            if cum >= lim: q = qq
        if not np.isnan(sp):
            if B.NEWS[0] <= sp < B.NEWS[1]: continue
            if sp >= B.NEWS[2]: q = min(q + 1, 3)
        dp = 0.0
        for r in t[t.d == day].itertuples():
            if dp <= -600: break
            nq = min(q + int(r.add), 3)
            dp += r.usd * nq + ((r.early - r.usd) if nq >= 2 else 0.0); n += 1
        cum += dp
    return cum, n
base = {}
for n_ in ("dev", "unseen_nq", "live"):
    d, s = sets[n_]
    t = trades(d)
    t["add"] = ((B._stretch(d, t, B.BAND["k"]) >= 1.5)).astype(int)
    base[n_] = (d, t)
print("trades:", {k: len(v[1]) for k, v in base.items()}, flush=True)
for r_, gap_too in [(None, False), (0.5, False), (0.75, False), (1.0, False), (1.25, False), (1.5, False), (2.0, False), (1.0, True)]:
    pool = []
    for n_ in ("dev", "unseen_nq"):
        d, t = base[n_]
        t = t.copy(); t["early"] = t.usd if r_ is None else early_col(t, r_, gap_too)
        pool += account(t, d, B.STEPS, 600.0, B._news(d))
    d, t = base["live"]; t = t.copy(); t["early"] = t.usd if r_ is None else early_col(t, r_, gap_too)
    tvn, tvt = tv(d, t)
    prof = np.array([x[1] for x in pool])
    print(f"early {r_} gap {gap_too}: starts {len(pool)} lost {np.mean([x[0] for x in pool]):.3f} median ${np.median(prof):,.0f} "
          f"p25 ${np.percentile(prof, 25):,.0f} p10 ${np.percentile(prof, 10):,.0f} | TV window ${tvn:,.0f} ({tvt} trades)", flush=True)
