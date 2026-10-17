"""Round ninety-nine (description): Larry Williams' volatility breakout with range-scaled stops and fixed-$ risk.

    python research/williams_sized.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds ninety-seven and ninety-eight (research/classic_systems.py, research/williams_combo.py): the breakout (k 0.5,
first side only, out at the close) is positive in all three data sets with WIDE stops (at the open or the opposite
level; 95th percentile risk $1,300-1,800 a trade at 1 MNQ) and loses with a fixed 25-point stop; added to the bot its
wide stops bust more 50K evaluations. The middle ground: a stop scaled to yesterday's range, and contracts scaled to a
fixed $ risk. Every period has been seen for the W family, so this round is DESCRIPTIVE and read strictly.

Variants, fixed before running (12):
  entry: buy stop at today's open + k x yesterday's regular-hours range, sell stop at the open - k x range, the first
    side triggered only, entries by 15:00 (classic_systems.williams / williams_combo.williams_trade, copied);
  stop: entry -/+ s x yesterday's range;
  contracts: floor($R / (stop distance x $2)), 1-10 MNQ; when even 1 contract risks more than $R, it trades 1 if the
    risk is at most 1.5 x $R, else the day is skipped;
  exit: the 15:59 close, or a target of 1R / 2R (the stop distance x 1 or 2 from the entry).
  Close exit: k 0.3 / 0.5 x s 0.25 / 0.5 x R $200 / $400 (8). Targets: k 0.3 / 0.5 x s 0.5 x R $200 x 1R / 2R (4).
Fills as setups.fill_from with the stop counting on the fill bar (a stop entry) and the target not on it; a minute
reaching both the stop and the target is a stop; stop fills less a tick; the close less a tick; $1.24 fees a contract;
both entry levels in one bar is a long that is stopped. Sessions, the first-of-month drop and the 20-session warm-up as
williams_combo.w_trades.
Alone (index 2011-18, 2019-26, NQ futures 2015-25): $ a trade (at its contracts), winners, t on daily P/L, trades a
week, worst losing stretch, risk at entry ($, max and 95th percentile).
Combined, only for variants positive with t >= 2 in all three: with the bot as the NinjaTrader strategy trades it
(williams_combo machinery: evaluation 4 MNQ, 3 losers, lock 1.0 / +2.5; funded 4 MNQ, 2 losers, lock 0.5 / +6.25;
minute equity of overlapping legs summed), index 2011-18, 2019-25 and NQ 2015-24: evaluation pass / bust %, payouts per
evaluation, first payout within 20 / 40 sessions, $ a week, green / red days.
"""
from __future__ import annotations

import itertools
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
import setups as SU  # noqa: E402
import trap_reversal as T  # noqa: E402
import williams_combo as WC  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
TICK, PV, FEE, N = SU.TICK, SU.PV, SU.FEE, SU.N
LAST_ENTRY = 330  # 15:00
VARIANTS = [(k, s, r, None) for k, s, r in itertools.product((0.3, 0.5), (0.25, 0.5), (200.0, 400.0))]
VARIANTS += [(k, 0.5, 200.0, m) for k, m in itertools.product((0.3, 0.5), (1.0, 2.0))]


def name(v):
    k, s, r, m = v
    return f"k{k} s{s} ${r:.0f} " + ("close" if m is None else f"{m:.0f}R")


def walk(o, h, lo, c, j0, d, stop, target):
    """(exit minute, exit price) from the fill bar j0: the stop counts on j0 (at the stop), the target from j0 + 1."""
    for j in range(j0, N):
        if (d > 0 and lo[j] <= stop) or (d < 0 and h[j] >= stop):
            px = stop if j == j0 else (min(o[j], stop) if d > 0 else max(o[j], stop))
            return j, px - d * TICK
        if target is not None and j > j0 and ((d > 0 and h[j] >= target + TICK) or (d < 0 and lo[j] <= target - TICK)):
            return j, target
    return N - 1, c[N - 1] - d * TICK


def sized_trade(o, h, lo, c, rng, v):
    """One day's trade or None: (entry minute, direction, entry, stop, exit minute, exit price, contracts, pnl $)."""
    k, s, r, m = v
    up, dn = o[0] + k * rng, o[0] - k * rng
    for j in range(0, LAST_ENTRY + 1):
        hit_up, hit_dn = h[j] >= up, lo[j] <= dn
        if not (hit_up or hit_dn):
            continue
        d = 1 if hit_up else -1
        lvl = up if d > 0 else dn
        entry = (max(o[j], lvl) if d > 0 else min(o[j], lvl)) + d * TICK
        dist = s * rng
        if dist <= 0:
            return None
        q = math.floor(r / (dist * PV))
        if q < 1:
            if dist * PV > 1.5 * r:
                return None
            q = 1
        q = min(q, 10)
        stop = entry - d * dist
        target = None if m is None else entry + d * m * dist
        if hit_up and hit_dn:  # both levels in one bar: a long that is stopped
            xp = entry - dist - TICK
            return j, 1, entry, entry - dist, j, xp, q, q * ((xp - entry) * PV - FEE)
        jx, xp = walk(o, h, lo, c, j, d, stop, target)
        return j, d, entry, stop, jx, xp, q, q * (d * (xp - entry) * PV - FEE)
    return None


def trades_of(path, v):
    S = SU.sessions(path)
    out = []
    for k in range(20, len(S)):
        if S[k][1] == 1:
            continue
        o, h, lo, c = S[k][2], S[k][3], S[k][4], S[k][5]
        r = sized_trade(o, h, lo, c, S[k - 1][3].max() - S[k - 1][4].min(), v)
        if r is not None:
            j, d, entry, stop, jx, xp, q, pnl = r
            out.append({"day": S[k][0], "j": j, "jx": jx, "dir": d, "entry": entry, "stop": stop, "exit": xp,
                        "q": q, "pnl": pnl, "risk": q * abs(entry - stop) * PV})
    return out, [x[0] for x in S[20:] if x[1] != 1]


def alone(args):
    path, v, periods = args
    tr, days = trades_of(path, v)
    rows = []
    for label, y0, y1 in periods:
        dd = [d for d in days if y0 <= d.year <= y1]
        t_in = [t for t in tr if y0 <= t["day"].year <= y1]
        daily = pd.Series(0.0, index=pd.DatetimeIndex(dd))
        for t in t_in:
            daily[t["day"]] += t["pnl"]
        eq = daily.cumsum()
        se = daily.std(ddof=1) / math.sqrt(len(daily))
        risk = [t["risk"] for t in t_in]
        rows.append({"period": label, "variant": name(v), "trades": len(t_in),
                     "trades/week": len(t_in) / (len(dd) / 5), "$/trade": float(np.mean([t["pnl"] for t in t_in])),
                     "winners %": 100 * np.mean([t["pnl"] > 0 for t in t_in]), "t": daily.mean() / se,
                     "$/day": daily.mean(), "worst stretch": float((eq.cummax() - eq).max()),
                     "avg MNQ": float(np.mean([t["q"] for t in t_in])), "risk 95% $": float(np.percentile(risk, 95)),
                     "risk max $": max(risk)})
    return rows


def legs_of(bars, trades):
    """W trades as legs on the bot's bars at each trade's own contracts (williams_combo.w_legs with q per trade)."""
    out = []
    for t in trades:
        q = t["q"]
        one = dict(t, pnl=t["pnl"] / q)
        out += WC.w_legs(bars, [one], q)
    return out


def combined(args):
    path, v, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot = T.bot_legs(bars, T.bot_trades(bars, 3, 1.0, 2.5), WC.BOT_Q)
    pa_bot = T.bot_legs(bars, T.bot_trades(bars, 2, 0.5, 6.25), WC.BOT_Q)
    wl = legs_of(bars, trades_of(path, v)[0]) if v is not None else []
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ss_p = [d for d in ss if d <= last]
        ev_all, pa_all = T.leg_paths(bars, ev_bot + wl), T.leg_paths(bars, pa_bot + wl)
        ev_days, pa_days = P.by_day(ev_all, ss), P.by_day(pa_all, ss)
        starts = [s for s, d in enumerate(ss) if d <= last]
        outs = [A.attempt(ev_days[s:], 1, "intraday", 30) for s in starts]
        memo, paid = {}, []
        for s, (res, used) in zip(starts, outs, strict=True):
            if res != "passed":
                paid.append(0.0)
                continue
            fp = s + used
            if fp not in memo:
                memo[fp] = sum(x for _, x in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
            paid.append(memo[fp])
        f40 = [F.first_payout(pa_days[s:], 1, None, None, 40) for s in starts]
        daily = WC.daily_of([(x[0], 0, 0, None, None, x[1]) for x in ev_all], ss_p)
        res = [o[0] for o in outs]
        rows.append({"period": label, "setup": "bot" if v is None else "bot + " + name(v),
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                     "eval pass %": 100 * res.count("passed") / len(res),
                     "eval bust %": 100 * res.count("failed") / len(res), "$ paid per eval": float(np.mean(paid)),
                     "1st pay in 20 %": 100 * np.mean([r[0] == "paid" and r[1] <= 20 for r in f40]),
                     "1st pay in 40 %": 100 * np.mean([r[0] == "paid" for r in f40])})
    return rows


def checks() -> None:
    """Sizing, stop, target and skip on hand-made days."""
    o = np.full(N, 1000.0)
    o[11:] = 1029.0
    c = o.copy()
    c[10] = 1029.0
    h, lo = np.maximum(o, c) + 0.5, np.minimum(o, c) - 0.5
    h[10] = 1030.0  # crosses up through open + 0.5 x 40 = 1020 at minute 10, then holds 1029
    lo[10] = 1015.0
    r = sized_trade(o, h, lo, c, 40.0, (0.5, 0.5, 200.0, None))  # stop 20 pts: $40 a contract -> 5 MNQ
    assert r[1] == 1 and r[6] == 5 and abs(r[2] - 1020.25) < 1e-9 and abs(r[3] - 1000.25) < 1e-9, r
    assert r[4] == N - 1 and abs(r[5] - (1029 - TICK)) < 1e-9, r
    h2 = h.copy()
    h2[20] = 1041.0  # 1R target 1040.25 + a tick reached at minute 20
    r = sized_trade(o, h2, lo, c, 40.0, (0.5, 0.5, 200.0, 1.0))
    assert r[4] == 20 and abs(r[5] - 1040.25) < 1e-9, r
    lo2 = lo.copy()
    lo2[15] = 1000.0  # through the stop (1000.25) at minute 15
    r = sized_trade(o, h, lo2, c, 40.0, (0.5, 0.5, 200.0, 1.0))
    assert r[4] == 15 and abs(r[5] - (1000.25 - TICK)) < 1e-9 and r[7] < 0, r
    assert sized_trade(o, h, lo, c, 400.0, (0.3, 0.5, 200.0, None)) is None  # 200 pts: $400 > 1.5 x $200, skipped
    print("checks passed")


def main() -> None:
    checks()
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026))
    nq_p = (("NQ 2015-2025", 2015, 2025),)
    jobs = [(nsx, v, idx_p) for v in VARIANTS] + [(nq, v, nq_p) for v in VARIANTS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(alone, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        print(f"\n{label}, alone")
        print(df[df.period == label].drop(columns="period").round(2).to_string(index=False))
    t = df.pivot(index="variant", columns="period", values="t")
    m = df.pivot(index="variant", columns="period", values="$/trade")
    keep = [nm for nm in t.index if (t.loc[nm] >= 2).all() and (m.loc[nm] > 0).all()]
    print(f"\npositive with t >= 2 in all three: {keep or 'none'}")
    if not keep:
        return
    chosen = [v for v in VARIANTS if name(v) in keep]
    cp_i = (("2011-2018", "2011-01-01", "2018-12-31"),)
    cp_i2 = (("2019-2025", "2019-01-01", "2025-06-30"),)
    cp_q = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    cj = [(nsx, v, p) for v in [None, *chosen] for p in (cp_i, cp_i2)] + [(nq, v, cp_q) for v in [None, *chosen]]
    with ProcessPoolExecutor(max_workers=4) as pool:
        cd = pd.DataFrame([r for rows in pool.map(combined, cj) for r in rows])
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}, with the bot")
        print(cd[cd.period == label].drop(columns="period").round(1).to_string(index=False))
    base = cd[cd.setup == "bot"].set_index("period")
    for nm in keep:
        d = cd[cd.setup == "bot + " + nm].set_index("period")
        better = all(d.loc[p, "eval pass %"] > base.loc[p, "eval pass %"] and
                     d.loc[p, "$ paid per eval"] > base.loc[p, "$ paid per eval"] for p in base.index)
        print(f"bot + {nm}: {'raises' if better else 'does not raise'} both pass rate and payouts in all three periods")


if __name__ == "__main__":
    main()
