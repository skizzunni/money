"""Round one hundred: the bot plus the risk-sized Williams breakout, as it can run on one Apex account.

    python research/combo_live.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round ninety-nine (research/williams_sized.py) found the Williams breakout with k 0.5 (levels at the open +/- half of
yesterday's regular-hours range, first side only), a stop a quarter of yesterday's range from the fill, $200 of risk a
trade (1-10 MNQ) and out at the close, positive alone in every data set (t 4.14 / 2.96 / 4.64; NQ futures up in all
11 years, the index in 14 of 16). Added to the bot it summed two independent positions. On one Apex account that is
not allowed (hedging is banned) and the positions net; NinjaTrader's managed orders also can't hold a buy stop and a
sell stop at once. So the version that can run: ONE POSITION AT A TIME, whichever setup's entry comes first owns the
account until it is flat (the other setup's entries meanwhile are not taken; the bot's own state runs on as if they
were), and the Williams entry is a market order at the next minute's open after a 1-minute bar touches a level (a
bar that touches both: skipped). Bot as the NinjaTrader strategy trades it (1-minute bars, 4 MNQ, 25-point cap; the
evaluation 3 losers, lock 1.0 / +2.5; funded 2 losers, lock 0.5 / +6.25). Fees $1.24 and a tick a side.
Measures (2011-18, 2019-25, NQ 2015-24; minute equity per day): $ a week, winners, red days, evaluation pass / bust %
(apex25k.attempt), payouts per evaluation (apex_payouts.pa_run, base caps), funded first payout within 20 sessions.
Adoption bar, fixed before running: against the bot alone on the same machinery, a higher evaluation pass rate and
more $ a week in all three periods, and payouts per evaluation at least 90% of the bot's in each.
"""
from __future__ import annotations

import math
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
TICK, PV, FEE = 0.25, 2.0, 1.24
K, S, RISK, LAST_ENTRY = 0.5, 0.25, 200.0, 900  # 15:00


def bot_legs(bars, losers, lock_at, lock_plus):
    """The bot at 4 MNQ: (start bar, end bar, direction, entry, exit, pnl $) per trade, positions in `bars`."""
    cfg = NoiseConfig(qty=4, max_loss_per_trade=25.0 * PV * 4, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus)
    res = run(bars, cfg, minutes=1)
    return [(t.entry_bar, t.exit_bar, t.direction, t.entry, t.exit, t.pnl, 4) for t in res.trades]


def williams_legs(bars):
    """One Williams trade a session at most: (start bar, end bar, direction, entry, exit, pnl $, contracts)."""
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o, h, lo, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(tmin == 570)
    out, prev_rng = [], None
    for n, a in enumerate(starts):
        b = starts[n + 1] if n + 1 < len(starts) else len(bars)
        b = a + int(np.searchsorted(day[a:b], day[a], side="right"))  # this session's bars only
        rng = prev_rng
        prev_rng = h[a:b].max() - lo[a:b].min()
        if rng is None or rng <= 0 or n == 0 or day[starts[n - 1]].month != day[a].month:
            continue  # no previous session, or the first session of a month (the rescaling gap)
        up, dn = o[a] + K * rng, o[a] - K * rng
        for j in range(a, b - 1):
            if tmin[j] > LAST_ENTRY:
                break
            hu, hd = h[j] >= up, lo[j] <= dn
            if hu and hd:
                break
            if not (hu or hd):
                continue
            d = 1 if hu else -1
            e = j + 1  # market order at the next minute's open
            entry = o[e] + d * TICK
            dist = S * rng
            q = math.floor(RISK / (dist * PV))
            if q < 1:
                if dist * PV > 1.5 * RISK:
                    break
                q = 1
            q = min(q, 10)
            stop = entry - d * dist
            last = b - 1 if tmin[b - 1] < 960 else b - 2  # the 15:59 bar
            x, px = last, c[last] - d * TICK
            for m in range(e, last + 1):
                if (d > 0 and lo[m] <= stop) or (d < 0 and h[m] >= stop):
                    px = (min(o[m], stop) if d > 0 else max(o[m], stop)) - d * TICK
                    x = m
                    break
            out.append((e, x, d, entry, px, q * (d * (px - entry) * PV - FEE), q))
            break
    return out


def schedule(legs):
    """One position at a time: the earliest start owns the account until its end."""
    taken, busy_until = [], -1
    for leg in sorted(legs, key=lambda x: (x[0], x[1])):
        if leg[0] > busy_until:
            taken.append(leg)
            busy_until = leg[1]
    return taken


def paths(bars, legs):
    """Per leg: (session, pnl, running max of minute equity, minute equity), the leg's contracts included."""
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    idx = bars.index.tz_convert(A.NY)
    out = []
    for a, b, d, entry, _, pnl, q in legs:
        if d > 0:
            hi, lp = h[a:b] - entry, lo[a:b] - entry
        else:
            hi, lp = entry - lo[a:b], entry - h[a:b]
        hi = np.append(q * (hi * PV - FEE), pnl)
        lp = np.append(q * (lp * PV - FEE), pnl)
        out.append((idx[a].normalize().tz_localize(None), pnl, np.maximum.accumulate(hi), lp))
    return out


def job(args):
    path, periods, with_w = args
    bars = A.rth(path)
    ev = bot_legs(bars, 3, 1.0, 2.5)
    pa = bot_legs(bars, 2, 0.5, 6.25)
    if with_w:
        w = williams_legs(bars)
        ev, pa = schedule(ev + w), schedule(pa + w)
    ev_p, pa_p = paths(bars, ev), paths(bars, pa)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [d for d in all_sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev_p, sess), P.by_day(pa_p, sess)
        n = passes = busts = 0
        paid, memo = [], {}
        for s, d in enumerate(sess):
            if d > last:
                break
            n += 1
            res, used = A.attempt(ev_days[s:], 1, "intraday", 30)
            busts += res == "failed"
            if res != "passed":
                paid.append(0.0)
                continue
            passes += 1
            fp = s + used
            if fp not in memo:
                memo[fp] = sum(a for _, a in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
            paid.append(memo[fp])
        firsts = [F.first_payout(pa_days[s:], 1, None, None, 20) for s, d in enumerate(sess) if d <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        pn = []
        for day, pnl, _, _ in ev_p:
            if day in daily.index:
                daily[day] += pnl
                pn.append(pnl)
        rows.append({"period": label, "setup": "bot + Williams" if with_w else "bot",
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "winners %": 100 * np.mean(np.array(pn) > 0), "red days %": 100 * (daily < 0).mean(),
                     "eval pass %": 100 * passes / n, "eval bust %": 100 * busts / n,
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in firsts])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, w) for path, per in ((nsx, idx_p), (nq, nq_p)) for w in (False, True)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    print(df.round(1).to_string(index=False))
    ok = True
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        b = df[(df.period == label) & (df.setup == "bot")].iloc[0]
        c = df[(df.period == label) & (df.setup != "bot")].iloc[0]
        good = (c["eval pass %"] > b["eval pass %"] and c["$/week"] > b["$/week"] and
                c["$ paid per eval"] >= 0.9 * b["$ paid per eval"])
        ok &= good
        print(f"{label}: {'PASS' if good else 'FAIL'}")
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
