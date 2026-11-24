"""Never more than `gap_days` sessions in a row without a trade (the user, 2026-11-24: "max 2-3 days no trading").
A session is due when the last `gap_days` had no trade (a mild-news day counts as none): it trades the shipped rules
(the mild-news skip does not apply) and, if they do not trade, a backup: `fallback` band settings (one trade) and then
the last half hour's momentum (Gao et al.: in at 15:30 the day's way from the open, a stop `stop_pts`, out 15:55)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import strats as S

SPEC = {"dev": (0.25, 2.0), "unseen_nq": (0.25, 2.0), "unseen_es": (0.25, 5.0), "live": (0.25, 2.0)}


def last_half_hour(d, i, tick, stop_pts=50.0, from_close=False):
    return S.backup_trade(d, i, tick, stop_pts)


def trades(name, d, gap, band, gap_days=2, fallback=None, stop_pts=30.0, from_close=False, news=(2.0, 3.0)):
    tick, pv = SPEC[name]
    rows, quiet = [], 0
    for i in range(len(d)):
        if i < 21:
            continue
        sp = d[i]["news"][0]
        due = gap_days and quiet >= gap_days
        legs, forced = [], False
        if due or np.isnan(sp) or not (news[0] <= sp < news[1]):
            legs = S.gap_go(d, i, tick, **gap) + S.noise(d, i, tick, stop_slip=2, nt=True, **band)
        if due and not legs:
            forced = True
            if fallback is not None:
                legs = S.noise(d, i, tick, stop_slip=2, nt=True, **{**band, **fallback, "max_trades": 1})
            if not legs:
                legs = last_half_hour(d, i, tick, stop_pts, from_close)
        for tr in legs:
            side, eb, e, x = tr[0], tr[1], tr[2], tr[3]
            st = S.band_stretch(d, i, side, eb, band["k"]) if eb > 1 and not forced and eb < 72 else np.nan
            rows.append(dict(d=d[i]["d"], bar=eb, usd=(x - e) * side * pv - 1.24, add=int(st >= 1.5) if st == st else 0,
                             force=forced, due=bool(due)))
        quiet = 0 if legs else quiet + 1
    return pd.DataFrame(rows)


def max_quiet(d, t, start=None):
    days = [x["d"] for x in d[21:] if start is None or pd.Timestamp(x["d"]) >= pd.Timestamp(start)]
    have = set(t.d)
    run = best = 0
    for x in days:
        run = 0 if x in have else run + 1
        best = max(best, run)
    return best, sum(x in have for x in days) / len(days)


def account(t, d, steps=((0, 1), (2000, 2), (3500, 3)), day_stop=600.0, news=(2.0, 3.0, 6.0), force_q=1,
            start=None, months=12, every="M"):
    """As harness.account (fresh 50K starts every month, 12 months, the $2,000 trailing floor), with the news rule,
    one more contract on t.add, and the backup trades (t.force) at force_q contracts (0: the day's size)."""
    sp = {x["d"]: x["news"][0] for x in d}
    by = {k: g for k, g in t.groupby("d")}
    days = [x["d"] for x in d]
    idx = pd.Series(range(len(days)), index=pd.to_datetime(days))
    starts = [pd.Timestamp(start)] if start else sorted({x.to_period(every).start_time for x in idx.index})
    res = []
    for s0 in starts:
        end = s0 + pd.DateOffset(months=months)
        seg = idx[(idx.index >= s0) & (idx.index < end)].to_numpy()
        if not start and (len(seg) < 200 or idx.index[-1] < end - pd.DateOffset(days=10)):
            continue
        bal, high, lost, peak, dd, n = 50000.0, 50000.0, False, 0.0, 0.0, 0
        for j in seg:
            g = by.get(days[j])
            if g is None:
                continue
            floor = min(high - 2000.0, 50000.0)
            prof = bal - 50000.0
            q = 1
            for lim, qq in steps:
                if prof >= lim:
                    q = qq
            v = sp.get(days[j], np.nan)
            if v == v and v >= news[2]:
                q = min(q + 1, 3)
            day = 0.0
            for r in g.itertuples():
                if day_stop and day <= -day_stop:
                    break
                qq = (force_q or q) if r.force else min(q + int(r.add), 3)
                day += r.usd * qq
                n += 1
                if bal + day <= floor:
                    lost = True
                    break
            bal += day
            high = max(high, bal)
            peak, dd = max(peak, bal), max(dd, max(peak, bal) - bal)
            if lost:
                break
        res.append((lost, bal - 50000.0, dd, n))
    return res
