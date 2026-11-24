"""The adoption bench as one call (2026-11-24): the shipped legs (gap with the 09:30 bar rule, the band) with
overrides, the news rule, the steps, the $600 day stop, one more contract on band entries add_at sigmas past the band;
returns the 104-start account numbers (dev + unseen NQ), per-set 1-contract stats and the TradingView window."""
from __future__ import annotations

import pickle

import harness as H
import numpy as np
import pandas as pd
import strats as S

PK = "/tmp/claude-0/-home-user-money/a932a565-3474-5ea9-80d7-5853e3bebb0c/scratchpad/data/zoo_days_news.pkl"
GAP = dict(k=0.6, exit_m=590, r=0.0, cap=30.0, min_body=0.03, max_bar=1.75)  # max_bar: docs 61; k 0.6: docs 87
BAND = dict(vwap=False, vwap_stop=True, hard=200.0, be_r=0.4, tp_r=2.5, last=840, trend=20, k=1.0, max_trades=9,
            range_pos=0.65, max_move=1.1, be_plus=2.0, move_free="first_check", lad_r=1.5, lad_lock=0.5)  # lad: docs 61
STEPS = ((0, 1), (2000, 2), (3500, 3))


def _stretch(d, t, k):
    idx = {x["d"]: i for i, x in enumerate(d)}
    return np.array([np.nan if r.bar <= 1 else S.band_stretch(d, idx[r.d], r.side, r.bar, k) for r in t.itertuples()])


NEWS = (2.0, 3.0, 6.0)  # no trading from / to, one more contract from (08:30 volume spike)


def _news(d, nw=NEWS):
    sp = {x["d"]: x["news"][0] for x in d}

    def f(day, q):
        v = sp.get(day, np.nan)
        if np.isnan(v):
            return q
        if nw[0] <= v < nw[1]:
            return 0
        return min(q + 1, 3) if v >= nw[2] else q
    return f


def tv(d, t, start="2026-08-27", steps=STEPS, day_stop=600.0, nw=NEWS):
    t = t.copy()
    t["d"] = pd.to_datetime(t.d)
    cum, n, w, gw, gl, peak, dd = 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0
    for i in range(21, len(d)):
        day = pd.Timestamp(d[i]["d"])
        if day < pd.Timestamp(start):
            continue
        sp = d[i]["news"][0]
        q = 1
        for lim, qq in steps:
            if cum >= lim:
                q = qq
        if not np.isnan(sp):
            if nw[0] <= sp < nw[1]:
                continue
            if sp >= nw[2]:
                q = min(q + 1, 3)
        dp = 0.0
        for r in t[t.d == day].itertuples():
            if day_stop and dp <= -day_stop:
                break
            p = r.usd * min(q + int(r.add), 3)
            dp += p
            n += 1
            w, gw, gl = (w + 1, gw + p, gl) if p > 0 else (w, gw, gl - p)
        cum += dp
        peak, dd = max(peak, cum), max(dd, peak - cum)
    return dict(net=cum, trades=n, win=w / max(n, 1), pf=gw / max(gl, 1e-9), dd=dd)


def run(band: dict | None = None, gap: dict | None = None, add_at: float = 1.5, legs_fn=None, steps=STEPS,
        day_stop: float = 600.0, add2_at: float = 0.0, news: bool = True, nw=NEWS) -> dict:
    sets = pickle.load(open(PK, "rb"))
    b, g = {**BAND, **(band or {})}, {**GAP, **(gap or {})}
    pool, out = [], {}
    for n, (d, s) in sets.items():
        legs = legs_fn(g, b) if legs_fn else (("gap_go", g), ("noise", b))
        t = H.trades_of(S.everyday, d, s, legs=legs)
        st = _stretch(d, t, b["k"])
        t["add"] = ((st >= add_at) & (add_at > 0)).astype(int) + ((st >= add2_at) & (add2_at > 0)).astype(int)
        u = t.usd
        yrs = len(d) / 252
        out[n] = dict(win=(u > 0).mean(), pf=u[u > 0].sum() / max(1e-9, -u[u < 0].sum()), per_yr=len(t) / yrs,
                      net_yr=u.sum() / yrs)
        if n in ("dev", "unseen_nq"):
            pool += H.account(t, d, steps=steps, day_stop=day_stop, day_qty=_news(d, nw) if news else None)
        if n == "live":
            out["tv"] = tv(d, t, steps=steps, day_stop=day_stop, nw=nw)
    prof = np.array([x[1] for x in pool])
    out["acct"] = dict(lost=np.mean([x[0] for x in pool]), median=np.median(prof), p25=np.percentile(prof, 25))
    return out


def line(label: str, r: dict) -> str:
    a, tv_ = r["acct"], r["tv"]
    sets = " | ".join(f"{n}: PF {r[n]['pf']:.2f} {r[n]['per_yr']:.0f}/yr ${r[n]['net_yr']:,.0f}"
                      for n in ("dev", "unseen_nq", "unseen_es", "live"))
    return (f"{label}: lost {a['lost']:.1%} median ${a['median']:,.0f} p25 ${a['p25']:,.0f} | TV ${tv_['net']:+,.0f} "
            f"{tv_['trades']}tr PF {tv_['pf']:.2f} dd ${tv_['dd']:,.0f} | {sets}")
