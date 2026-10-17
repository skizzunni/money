"""Round ninety-eight (description): Larry Williams' volatility breakout added to the bot on one 50K Apex account.

    python research/williams_combo.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round ninety-seven (research/classic_systems.py) found W5 (k 0.5: buy stop at today's open + 0.5 x yesterday's
regular-hours range, sell stop at the open - 0.5 x range, the first side triggered only, stop at the opposite entry
level, out at the close) positive at 1 MNQ in all three data sets (t 2.75 / 2.97 / 2.99, 52-55% winners, about 3
trades a week), and W2 (the same with the stop at today's open) t 2.53 / 2.50 / 3.07. It narrowly failed the
discovery gate, and every period has now been seen: this round only DESCRIBES what W adds to the bot on the account.
Nothing here is a test.

Combinations, fixed before running:
  bot                the bot as the NinjaTrader strategy trades it: evaluation 4 MNQ, 3 losers, lock 1.0 / +2.5;
                     funded 4 MNQ, 2 losers, lock 0.5 / +6.25 (research/trap_reversal.bot_trades, 1-minute bars,
                     25-point max loss, take-profit 1.5 from the fill)
  bot + W5 x1        the bot plus W5 at 1 MNQ (in the evaluation and the funded account)
  bot + W2 x1        the bot plus W2 at 1 MNQ
  bot + W5 x2        the bot plus W5 at 2 MNQ
  W5 x1, W5 x2       W5 alone at 1 and 2 MNQ
W rules exactly as research/classic_systems.py (williams() and setups.fill_from(), copied here with the entry and exit
minutes kept): sessions from setups.sessions (>= 370 of 390 minutes, a missing minute repeats the last close), the first
session of each month dropped (the rescaling gap), from the 20th session on; entries by 15:00; stop entries fill at
their level or the minute's open if past it, plus a tick; stop fills less a tick; out at the 15:59 close less a tick;
$1.24 fees a contract; a minute reaching both levels is a long that is stopped.
Each W trade becomes a leg on the bot's 1-minute bars (entry at its entry minute, exit at its exit minute; its open
profit and loss minute by minute from those bars, as the bot's legs), and the minute equity of every leg open on a day
is summed into one equity path per day (research/trap_reversal.leg_paths), so the trailing drawdown sees the bot and W
together. Risk check: the $ distance from each W entry to its stop, at 1 and 2 MNQ (max and 95th percentile).
Measures, index 2011-18 and 2019-25 and NQ futures 2015-24 (evaluation starts as rounds sixty-one to ninety-five):
winners (all legs), $ a week, worst losing stretch, green / red days, the correlation of the bot's and W's daily P/L,
the 50K intraday-trail evaluation pass / bust / timeout % (apex25k.attempt, $3,000 target, $2,000 drawdown, 30 days),
payouts per evaluation (apex_payouts.pa_run, base caps), and the funded account's first payout within 20 and 40
sessions (fast_payout.first_payout, no profit or loss stop).
"""
from __future__ import annotations

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

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
TICK, PV, FEE, N = SU.TICK, SU.PV, SU.FEE, SU.N
LAST_ENTRY = 330  # 15:00
BOT_Q = 4
COMBOS = {"bot": (True, None, 0), "bot + W5 x1": (True, "range", 1), "bot + W2 x1": (True, "open", 1),
          "bot + W5 x2": (True, "range", 2), "W5 x1": (False, "range", 1), "W5 x2": (False, "range", 2)}


def fill_exit(o, h, lo, c, j0, d, stop, exit_idx):
    """setups.fill_from with no target and the stop counting on the fill bar, returning (exit minute, exit price)."""
    for j in range(j0, exit_idx + 1):
        if (d > 0 and lo[j] <= stop) or (d < 0 and h[j] >= stop):
            px = stop if j == j0 else (min(o[j], stop) if d > 0 else max(o[j], stop))
            return j, px - d * TICK
    return exit_idx, c[exit_idx] - d * TICK


def williams_trade(o, h, lo, c, rng, k, mode):
    """classic_systems.williams for modes 'open' and 'range' (1 contract), with the minutes: (entry minute, direction,
    entry, stop, exit minute, exit price, pnl) or None."""
    up, dn = o[0] + k * rng, o[0] - k * rng
    for j in range(0, LAST_ENTRY + 1):
        hit_up, hit_dn = h[j] >= up, lo[j] <= dn
        if not (hit_up or hit_dn):
            continue
        d = 1 if hit_up else -1
        lvl = up if d > 0 else dn
        entry = (max(o[j], lvl) if d > 0 else min(o[j], lvl)) + d * TICK
        stop = o[0] if mode == "open" else (dn if d > 0 else up)
        if hit_up and hit_dn:  # both levels in one bar: a long that is stopped
            xp = stop - TICK
            return j, 1, entry, stop, j, xp, (xp - entry) * PV - FEE
        jx, xp = fill_exit(o, h, lo, c, j, d, stop, N - 1)
        return j, d, entry, stop, jx, xp, d * (xp - entry) * PV - FEE
    return None


def w_trades(path, mode):
    """Every W trade of the rule on the data: dicts with day, minutes, direction, entry, stop, exit, pnl a contract."""
    S = SU.sessions(path)
    out = []
    for k in range(20, len(S)):
        if S[k][1] == 1:
            continue
        o, h, lo, c = S[k][2], S[k][3], S[k][4], S[k][5]
        yh, yl = S[k - 1][3].max(), S[k - 1][4].min()
        r = williams_trade(o, h, lo, c, yh - yl, 0.5, mode)
        if r is not None:
            j, d, entry, stop, jx, xp, pnl = r
            out.append({"day": S[k][0], "j": j, "jx": jx, "dir": d, "entry": entry, "stop": stop, "exit": xp,
                        "pnl": pnl})
    return out


def w_legs(bars, trades, q):
    """W trades as legs on the bot's bars: (day, entry bar, exit bar, hi path, lo path, pnl), $ at q contracts."""
    idx = bars.index.tz_convert(A.NY)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    legs = []
    for t in trades:
        t0 = (t["day"] + pd.Timedelta(minutes=570 + t["j"])).tz_localize(A.NY)
        t1 = (t["day"] + pd.Timedelta(minutes=570 + t["jx"])).tz_localize(A.NY)
        a = int(idx.searchsorted(t0))  # a filled (missing) minute: the next bar
        b = int(idx.searchsorted(t1, side="right")) - 1
        if a >= len(idx) or idx[a].normalize().tz_localize(None) != t["day"]:
            continue
        b = max(a, b)
        d, e = t["dir"], t["entry"]
        hp, lp = (h[a:b] - e, lo[a:b] - e) if d > 0 else (e - lo[a:b], e - h[a:b])
        hp = np.append(hp * PV - FEE, t["pnl"]) * q
        lp = np.append(lp * PV - FEE, t["pnl"]) * q
        legs.append((t["day"], a, b, hp, lp, q * t["pnl"]))
    return legs


def daily_of(legs, ss):
    s = pd.Series(0.0, index=pd.DatetimeIndex(ss))
    for x in legs:
        if x[0] in s.index:
            s[x[0]] += x[5]
    return s


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot = T.bot_legs(bars, T.bot_trades(bars, 3, 1.0, 2.5), BOT_Q)
    pa_bot = T.bot_legs(bars, T.bot_trades(bars, 2, 0.5, 6.25), BOT_Q)
    wt = {m: w_trades(path, m) for m in ("range", "open")}
    rows, risk = [], []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ss_p = [d for d in ss if d <= last]
        for m in ("range", "open"):
            dist = [abs(t["entry"] - t["stop"]) * PV for t in wt[m] if pd.Timestamp(first) <= t["day"] <= last]
            risk.append({"period": label, "rule": "W5" if m == "range" else "W2", "trades": len(dist),
                         "max $ x1": max(dist), "95% $ x1": float(np.percentile(dist, 95)),
                         "max $ x2": 2 * max(dist), "95% $ x2": 2 * float(np.percentile(dist, 95))})
        bot_daily = daily_of(ev_bot, ss_p)
        for name, (with_bot, mode, q) in COMBOS.items():
            wl = w_legs(bars, wt[mode], q) if mode else []
            ev_legs = (ev_bot if with_bot else []) + wl
            pa_legs = (pa_bot if with_bot else []) + wl
            ev_all, pa_all = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
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
            daily = daily_of([(x[0], 0, 0, None, None, x[1]) for x in ev_all], ss_p)
            eq = daily.cumsum()
            in_p = [x for x in ev_legs if pd.Timestamp(first) <= x[0] <= last]
            corr = float(np.corrcoef(bot_daily, daily_of(wl, ss_p))[0, 1]) if (with_bot and mode) else np.nan
            res = [o[0] for o in outs]
            rows.append({"period": label, "setup": name, "winners %": 100 * np.mean([x[5] > 0 for x in in_p]),
                         "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                         "worst stretch": float((eq.cummax() - eq).max()),
                         "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                         "corr bot/W": corr, "eval pass %": 100 * res.count("passed") / len(res),
                         "eval bust %": 100 * res.count("failed") / len(res),
                         "timeout %": 100 * res.count("timeout") / len(res), "$ paid per eval": float(np.mean(paid)),
                         "1st pay in 20 %": 100 * np.mean([r[0] == "paid" and r[1] <= 20 for r in f40]),
                         "1st pay in 40 %": 100 * np.mean([r[0] == "paid" for r in f40])})
    return rows, risk


def checks() -> None:
    """The merge of overlapping legs on a hand-made day, and W against classic_systems.williams."""
    day = pd.Timestamp("2020-01-02")
    leg1 = (day, 0, 2, np.array([10.0, 30.0, 20.0]), np.array([-5.0, 5.0, 20.0]), 20.0)  # bars 0-2, exits +20
    leg2 = (day, 1, 3, np.array([0.0, 40.0, -10.0]), np.array([-30.0, -20.0, -10.0]), -10.0)  # bars 1-3, exits -10
    (d, pnl, hi, lo), = T.leg_paths(None, [leg1, leg2])
    assert d == day and pnl == 10.0
    assert np.allclose(lo, [-5.0, 5 - 30, 20 - 20, 20 - 10]), lo
    assert np.allclose(hi, np.maximum.accumulate([10.0, 30 + 0, 20 + 40, 20 - 10])), hi
    import classic_systems as CS
    rng = np.random.default_rng(3)
    for _ in range(300):
        c = 1000 + np.cumsum(rng.normal(0, 2, N))
        o = np.r_[1000.0, c[:-1]]
        h = np.maximum(o, c) + rng.random(N)
        lo = np.minimum(o, c) - rng.random(N)
        for mode in ("open", "range"):
            a = CS.williams(o, h, lo, c, 12.0, 0.5, mode)
            b = williams_trade(o, h, lo, c, 12.0, 0.5, mode)
            assert (a is None and b is None) or abs(a - b[6]) < 1e-9, (a, b)
    print("checks passed: the merge sums overlapping legs minute by minute; W matches classic_systems.williams")


def main() -> None:
    checks()
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"),)), (nsx, (("2019-2025", "2019-01-01", "2025-06-30"),)),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(job, jobs))
    df = pd.DataFrame([r for rows, _ in res for r in rows])
    rk = pd.DataFrame([r for _, risk in res for r in risk]).drop_duplicates(["period", "rule"])
    pd.set_option("display.width", 250)
    print("\nRisk of a W trade at entry ($ to its stop)")
    print(rk.round(0).to_string(index=False))
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    base = df[df.setup == "bot"].set_index("period")
    for name in ("bot + W5 x1", "bot + W2 x1", "bot + W5 x2"):
        d = df[df.setup == name].set_index("period")
        better = all(d.loc[p, "eval pass %"] > base.loc[p, "eval pass %"] and
                     d.loc[p, "$ paid per eval"] > base.loc[p, "$ paid per eval"] for p in base.index)
        print(f"{name}: {'improves' if better else 'does not improve'} both passes and payouts in all three periods")


if __name__ == "__main__":
    main()
