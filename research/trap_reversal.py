"""Round ninety-three: a trap reversal after a failed breakout, added to the bot (MNQ, one 50K Apex account).

    python research/trap_reversal.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds 39-42: half of the bot's losers are stopped within 2 minutes of the fill, by the bounce right after the
breakout. A failed breakout traps the traders who bought it; the move back may run. Never tested here: a STOP-AND-
REVERSE after a quick failure (ghost trades, entry delay, pullback limits, the quiet-day fade and the VWAP fade were).

Rules, fixed before running (12):
  The bot as it trades the evaluation: v1.6 on 1-minute bars, 25-point max loss, take-profit 1.5 noise units from the
  fill, lock 1.0 / +2.5, 3 losers a day.
  A failed trade: a bot trade closed by its line stop or max loss ("Back inside" / "Max loss") within N minutes of its
  fill, N = 3, 10 or any time.
  The reversal: the opposite direction, entered at the open of the minute after the failed trade's exit (+1 tick of
  slippage), only if that minute starts before 15:59 and on the same session; at most one reversal a day (the day's
  first failed trade that qualifies).
  Stop: 'swing' = one tick beyond the failed trade's best price between its entry and exit minutes (the high for a
  failed long), or 'fixed' = 25 points from the reversal's fill. No trade if the stop is not beyond the fill or more
  than 40 points from it.
  Target: the reversal's fill +/- 1.0 or 2.0 times its risk (the stop distance) - the brief's 'failed trade's entry
  -/+ k x risk' is read this way, since that entry sits about a stop away on the wrong side. A limit, filled at its
  price once a minute trades a tick through it, working from the fill minute; the stop counts first when a minute
  reaches both.
  Stop fills at the stop less a tick, or at the minute's open less a tick if the open is past it. Flat at the close of
  the last minute before 16:00, less a tick.
  Size 4 MNQ; $1.24 round-trip fees a contract. The bot's own trading is unchanged; the reversal is a separate
  position (if the bot trades while it is open, their minute equity adds up).
  (The brief's third target, the opposite noise line, was dropped to keep the count at 12: 3 x 2 x 2.)
Protocol, fixed before running: discovery on the index 2011-2018: the reversal trades alone, $ a trade, t on the daily
P/L (every session, 0 on days without a reversal), two-sided p, Benjamini-Hochberg at q = 0.05 across the 12 rules.
Survivors: one look at the index 2019 - Sep 2026 (t >= 2, same sign), then NQ futures 2015-2025 (t >= 1.5, same sign).
For a final survivor: bot + reversal against the bot alone - winners, $ a week, worst losing stretch, green / red days,
the 50K intraday-trail evaluation pass / bust % (research/apex25k.py attempt, $3,000 target, $2,000 drawdown, minute
equity of both positions summed), payouts per evaluation (research/apex_payouts.py rules, base caps; funded bot with
lock 0.5 / +6.25 and 2 losers) and the funded first payout within 20 and 40 sessions (research/fast_payout.py).
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

from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
TICK, CAP, Q, MAX_RISK = 0.25, 25.0, 4, 40.0
NS = (3, 10, None)
STOPS = ("swing", "fixed")
KS = (1.0, 2.0)
RULES = list(itertools.product(NS, STOPS, KS))


def rule_name(rule):
    n, stop, k = rule
    return f"N={n if n else 'any'} {stop} {k:.0f}R"


def incomplete_sessions(bars):
    """Sessions whose 09:30-16:00 data ends early or misses minutes (half days, holidays, data holes), as
    "YYYY-MM-DD,..." - traded on only when MNQ_COMPLETE_ONLY is not set (the audit's data treatment)."""
    import os
    if os.environ.get("MNQ_COMPLETE_ONLY") != "1":
        return ""
    m = bars.index.tz_convert(A.NY)
    t = (m.hour * 60 + m.minute).to_numpy()
    inside = (t >= 570) & (t < 960)
    n = pd.Series(inside, index=m.normalize()).groupby(level=0).sum()
    return ",".join(d.strftime("%Y-%m-%d") for d in n[n < 390].index)


def bot_trades(bars, losers, lock_at, lock_plus):
    cfg = NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED,
                      skip_dates=incomplete_sessions(bars), target_on_fill_bar=True, lock_at=lock_at,
                      lock_plus=lock_plus)
    return run(bars, cfg, minutes=1).trades


def session_last(idx_ny) -> np.ndarray:
    """For each minute, the index of the last minute before 16:00 on its session."""
    day = idx_ny.normalize()
    tmin = idx_ny.hour * 60 + idx_ny.minute
    last = np.full(len(idx_ny), -1)
    pos = np.arange(len(idx_ny))
    ok = tmin < 960
    s = pd.Series(np.where(ok, pos, -1), index=pos)
    grp = s.groupby(day.to_numpy()).transform("max").to_numpy()
    last[:] = grp
    return last


def simulate(o, h, lo, c, e, last, d, stop, k):
    """One reversal entered at minute e in direction d with the given stop: (entry, exit_bar, exit, pnl a contract,
    hi path, lo path) or None when not taken."""
    slip = TICK
    entry = o[e] + d * slip
    risk = d * (entry - stop)
    if not risk > 0 or risk > MAX_RISK:
        return None
    tgt = entry + d * k * risk
    x_end = last[e]
    if x_end < e:
        return None
    ex = None
    for i in range(e, x_end + 1):
        if i == e:
            hit = lo[i] <= stop if d > 0 else h[i] >= stop
            px = (min(o[i], stop) if d > 0 else max(o[i], stop)) - d * slip
        elif (d > 0 and o[i] <= stop) or (d < 0 and o[i] >= stop):
            hit, px = True, o[i] - d * slip
        else:
            hit = lo[i] <= stop if d > 0 else h[i] >= stop
            px = stop - d * slip
        if hit:
            ex = (i, px)
            break
        if (d > 0 and h[i] >= tgt + TICK) or (d < 0 and lo[i] <= tgt - TICK):
            ex = (i, tgt)
            break
    if ex is None:
        ex = (x_end, c[x_end] - d * slip)
    b, xp = ex
    pnl = d * (xp - entry) * A.PV - A.FEE
    if d > 0:
        hi_p, lo_p = h[e:b] - entry, lo[e:b] - entry
    else:
        hi_p, lo_p = entry - lo[e:b], entry - h[e:b]
    hi_p = np.append(hi_p * A.PV - A.FEE, pnl)
    lo_p = np.append(lo_p * A.PV - A.FEE, pnl)
    return entry, b, xp, pnl, hi_p, lo_p


def reversals(bars, trades, rule):
    """The reversal trades for one rule: list of dicts."""
    n, stop_kind, k = rule
    o, h = bars.open.to_numpy(float), bars.high.to_numpy(float)
    lo, c = bars.low.to_numpy(float), bars.close.to_numpy(float)
    idx = bars.index.tz_convert(A.NY)
    last = session_last(idx)
    days = idx.normalize().tz_localize(None)
    tmin = idx.hour * 60 + idx.minute
    out, done = [], set()
    for t in trades:
        if t.reason not in ("Back inside", "Max loss"):
            continue
        mins = (t.exit_time - t.entry_time).total_seconds() / 60
        if n is not None and mins > n:
            continue
        e = t.exit_bar + 1
        if e >= len(bars) or days[e] != days[t.exit_bar] or tmin[e] >= 959:
            continue
        day = days[e]
        if day in done:
            continue
        d = -t.direction
        if stop_kind == "swing":
            seg = slice(t.entry_bar, t.exit_bar + 1)
            stop = (h[seg].max() + TICK) if d < 0 else (lo[seg].min() - TICK)
        else:
            stop = o[e] + d * TICK - d * CAP
        r = simulate(o, h, lo, c, e, last, d, stop, k)
        done.add(day)  # one reversal a day: the first qualifying failure, taken or not
        if r is None:
            continue
        entry, b, xp, pnl, hi_p, lo_p = r
        out.append({"day": day, "entry_bar": e, "exit_bar": b, "dir": d, "entry": entry, "exit": xp, "pnl": pnl,
                    "hi": hi_p, "lo": lo_p})
    return out


def sessions_of(bars):
    m = bars.index.tz_convert(A.NY)
    return pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None))))


def stat(revs, sess, y0, y1):
    ss = sess[(sess.year >= y0) & (sess.year <= y1)]
    daily = pd.Series(0.0, index=ss)
    pnl = []
    for r in revs:
        if r["day"] in daily.index:
            daily[r["day"]] += Q * r["pnl"]
            pnl.append(Q * r["pnl"])
    sd = daily.std(ddof=1)
    t = daily.mean() / sd * math.sqrt(len(daily)) if sd > 0 else 0.0
    p = math.erfc(abs(t) / math.sqrt(2))
    return {"trades": len(pnl), "$/trade": float(np.mean(pnl)) if pnl else 0.0,
            "win %": 100 * float(np.mean([x > 0 for x in pnl])) if pnl else 0.0, "$/day": daily.mean(), "t": t, "p": p}


def bh(pvals, q=0.05):
    m = len(pvals)
    order = np.argsort(pvals)
    passed = np.zeros(m, bool)
    kmax = -1
    for rank, i in enumerate(order, 1):
        if pvals[i] <= q * rank / m:
            kmax = rank
    for rank, i in enumerate(order, 1):
        passed[i] = rank <= kmax
    return passed


def disc_job(args):
    path, periods = args
    bars = A.rth(path)
    trades = bot_trades(bars, 3, 1.0, 2.5)
    sess = sessions_of(bars)
    out = []
    for rule in RULES:
        revs = reversals(bars, trades, rule)
        for label, y0, y1 in periods:
            out.append({"period": label, "rule": rule_name(rule), **stat(revs, sess, y0, y1)})
    return out


# ── combined measures for a final survivor ──
def leg_paths(bars, legs):
    """Per day: one combined 'trade' (pnl, running max of minute equity, minute equity) from legs given as
    (day, entry_bar, exit_bar, hi path, lo path, pnl) with the paths per contract already scaled to $."""
    by_day = {}
    for leg in legs:
        by_day.setdefault(leg[0], []).append(leg)
    out = []
    for day, ls in by_day.items():
        a0, b0 = min(x[1] for x in ls), max(x[2] for x in ls)
        n = b0 - a0 + 1
        hi = np.zeros(n)
        lo = np.zeros(n)
        for _, a, b, hp, lp, pnl in ls:
            hh, ll = np.zeros(n), np.zeros(n)
            seg = slice(a - a0, b - a0 + 1)
            hh[seg], ll[seg] = hp[: b - a + 1], lp[: b - a + 1]
            hh[b - a0 + 1:] = ll[b - a0 + 1:] = pnl
            hi += hh
            lo += ll
        out.append((day, float(lo[-1]), np.maximum.accumulate(hi), lo))
    return out


def bot_legs(bars, trades, q):
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    idx = bars.index.tz_convert(A.NY).normalize().tz_localize(None)
    legs = []
    for t in trades:
        a, b = t.entry_bar, t.exit_bar
        if t.direction > 0:
            hp, lp = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hp, lp = t.entry - lo[a:b], t.entry - h[a:b]
        hp = np.append(hp * A.PV - A.FEE, t.pnl) * q
        lp = np.append(lp * A.PV - A.FEE, t.pnl) * q
        legs.append((idx[a], a, b, hp, lp, q * t.pnl))
    return legs


def rev_legs(revs, q):
    return [(r["day"], r["entry_bar"], r["exit_bar"], q * r["hi"], q * r["lo"], q * r["pnl"]) for r in revs]


def apex_job(args):
    path, periods, rule = args
    bars = A.rth(path)
    sess = list(sessions_of(bars))
    ev_trades, pa_trades = bot_trades(bars, 3, 1.0, 2.5), bot_trades(bars, 2, 0.5, 6.25)
    rows = []
    for with_rev in (False, True):
        ev_legs, pa_legs = bot_legs(bars, ev_trades, Q), bot_legs(bars, pa_trades, Q)
        if with_rev:
            ev_legs += rev_legs(reversals(bars, ev_trades, rule), Q)
            pa_legs += rev_legs(reversals(bars, pa_trades, rule), Q)
        ev_days_all, pa_days_all = leg_paths(bars, ev_legs), leg_paths(bars, pa_legs)
        for label, first, last_start in periods:
            ss = [d for d in sess if d >= pd.Timestamp(first)]
            last = pd.Timestamp(last_start)
            ev_days, pa_days = P.by_day(ev_days_all, ss), P.by_day(pa_days_all, ss)
            outs = [A.attempt(ev_days[s:], 1, "intraday", 30) for s, d in enumerate(ss) if d <= last]
            memo, paid = {}, []
            for s, (res, used) in enumerate(outs):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = sum(a for _, a in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
                paid.append(memo[fp])
            starts = [s for s, d in enumerate(ss) if d <= last]
            f40 = [F.first_payout(pa_days[s:], 1, None, None, 40) for s in starts]
            ev_legs_p = [x for x in ev_legs if pd.Timestamp(first) <= x[0] <= last]
            daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in ss if d <= last]))
            for x in ev_days_all:
                if x[0] in daily.index:
                    daily[x[0]] += x[1]
            eq = daily.cumsum()
            rows.append({"period": label, "setup": "bot + reversal" if with_rev else "bot",
                         "winners %": 100 * np.mean([x[5] > 0 for x in ev_legs_p]),
                         "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                         "worst stretch": float((eq.cummax() - eq).max()),
                         "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                         "eval pass %": 100 * [o[0] for o in outs].count("passed") / len(outs),
                         "eval bust %": 100 * [o[0] for o in outs].count("failed") / len(outs),
                         "$ paid per eval": float(np.mean(paid)),
                         "1st pay in 20 %": 100 * np.mean([r[0] == "paid" and r[1] <= 20 for r in f40]),
                         "1st pay in 40 %": 100 * np.mean([r[0] == "paid" for r in f40])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 220)
    idx_p = (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026))
    nq_p = (("NQ 2015-2025", 2015, 2025),)
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(disc_job, [(nsx, idx_p), (nq, nq_p)]) for r in rows])
    disc = df[df.period == "2011-2018"].reset_index(drop=True)
    disc["BH pass"] = bh(disc.p.to_list())
    print("Discovery, index 2011-2018 (reversal trades alone, 4 MNQ)")
    print(disc.drop(columns="period").round(3).to_string(index=False))
    surv = disc[disc["BH pass"]].rule.to_list()
    print(f"\nBH survivors: {surv or 'none'}")
    final = []
    for name in surv:
        sign = np.sign(disc.set_index("rule").loc[name, "t"])
        h = df[(df.period == "2019-2026") & (df.rule == name)].iloc[0]
        ok2 = np.sign(h.t) == sign and abs(h.t) >= 2
        print(f"  {name}: 2019-2026 t {h.t:.2f} ({'PASS' if ok2 else 'FAIL'})")
        if not ok2:
            continue
        nqr = df[(df.period == "NQ 2015-2025") & (df.rule == name)].iloc[0]
        ok3 = np.sign(nqr.t) == sign and abs(nqr.t) >= 1.5
        print(f"  {name}: NQ 2015-2025 t {nqr.t:.2f} ({'PASS' if ok3 else 'FAIL'})")
        if ok3:
            final.append(name)
    print("\nAll rules, every period (description):")
    print(df.pivot_table(index="rule", columns="period", values=["$/trade", "t"]).round(2).to_string())
    print(f"\nFinal survivors: {final or 'none'}")
    for name in final:
        rule = next(r for r in RULES if rule_name(r) == name)
        jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30")), rule),
                (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),), rule)]
        with ProcessPoolExecutor(max_workers=2) as pool:
            comb = pd.DataFrame([r for rows in pool.map(apex_job, jobs) for r in rows])
        print(f"\n{name}: bot + reversal against the bot alone")
        print(comb.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
