"""Round one hundred and two: more from the Williams breakout next to the bot (together, and stop-and-reverse).

    python research/combo_more.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round one hundred and one (research/combo_priority.py, now in the NinjaTrader strategy): the bot first, a Williams
trade only while the bot is flat, cut at the bot's next entry. Two ways to get more from it, fixed before running:
  together  a Williams trigger while the bot is in a trade IN THE SAME DIRECTION is taken too (adding to a position
            is not hedging), at most 6 MNQ so the account never holds more than 10 (the bot's 4 + 6); a bot entry in
            the same direction while a Williams trade is open trims it to 6 instead of closing it; a bot entry the
            other way still closes it. A trigger while the bot is in the other direction: no trade, as now.
  reverse   Larry Williams' stop-and-reverse: after a Williams trade is stopped out, a later touch of the other level
            (bar starting 15:00 at the latest) gives one more trade that day, the other way, sized and stopped the same.
            It obeys the same rules as the first (bot first).
  both      together + reverse.
Everything else as round one hundred and one (research/combo_live.py: k 0.5, stop a quarter of yesterday's range
from the fill, $200 of risk, 1-10 MNQ, out at the close, market entry the minute after the touch, a bar touching both
levels: no trade). Overlapping positions are summed minute by minute (research/trap_reversal.leg_paths) for every
setup here, round one hundred and one's included, so all are measured the same way.
Bar, fixed before running (every period has been seen for this family, so the bar is against the strategy as it is
now, on all three): a variant is adopted if, against round one hundred and one, it has more $ a week, an evaluation
pass rate at least as high, payouts per evaluation at least as high, and a first payout within 20 sessions at least
as often, in all three periods. If more than one passes, the one with the most $ paid per evaluation summed over the
three periods.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_live as C  # noqa: E402
import fast_payout as F  # noqa: E402
import trap_reversal as T  # noqa: E402

MAXQ, BOTQ = 10, 4
FORCE_ONE = True  # one contract when it costs 1-1.5x the risk (the strategy); False: skip (round 139)
SETUPS = ("round 101", "together", "reverse", "both")


def w_candidates(bars, reverse, mgmt=None):
    """Per session, the Williams trades it could take, in time order: dicts with entry bar a, stop-or-close exit bar
    x, direction, entry, exit price, contracts, and whether it was stopped. The second (reverse) one only after the
    first was stopped, on a later touch of the other level. mgmt (lock_at, lock_plus, target), in yesterday's ranges
    (None: none): once a bar's best price reaches lock_at from the entry, the stop moves to entry + lock_plus from the
    next bar; a take-profit at target fills at its price when a bar trades a tick through it (the stop counts first
    in a bar that reaches both)."""
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o, h, lo, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(tmin == 570)
    out, prev_rng = [], None
    for n, a in enumerate(starts):
        b = starts[n + 1] if n + 1 < len(starts) else len(bars)
        b = a + int(np.searchsorted(day[a:b], day[a], side="right"))
        rng = prev_rng
        prev_rng = h[a:b].max() - lo[a:b].min()
        if rng is None or rng <= 0 or n == 0 or day[starts[n - 1]].month != day[a].month:
            continue
        up, dn = o[a] + C.K * rng, o[a] - C.K * rng
        dist = C.S * rng
        q = math.floor(C.RISK / (dist * C.PV))
        if q < 1:
            if dist * C.PV > 1.5 * C.RISK or not FORCE_ONE:
                continue
            q = 1
        q = min(q, MAXQ)
        last = b - 1 if tmin[b - 1] < 960 else b - 2
        day_legs, j, want = [], a, 0  # want: 0 either level, +1 / -1 only that side (the reverse)
        while j < b - 1 and tmin[j] <= C.LAST_ENTRY:
            hu, hd = h[j] >= up, lo[j] <= dn
            if want == 0 and hu and hd:
                break
            if want > 0:
                hd = False
            if want < 0:
                hu = False
            if not (hu or hd):
                j += 1
                continue
            d = 1 if hu else -1
            e = j + 1
            entry = o[e] + d * C.TICK
            stop = entry - d * dist
            x, px, stopped = last, c[last] - d * C.TICK, False
            lk = tg = None
            if mgmt:
                lk = (entry + d * mgmt[0] * rng, entry + d * mgmt[1] * rng)
                tg = entry + d * mgmt[2] * rng if mgmt[2] else None
            for m in range(e, last + 1):
                if (d > 0 and lo[m] <= stop) or (d < 0 and h[m] >= stop):
                    px, x = (min(o[m], stop) if d > 0 else max(o[m], stop)) - d * C.TICK, m
                    stopped = d * (px - entry) < 0  # a locked stop is a win, not a stop-out for the reverse
                    break
                if tg is not None and ((d > 0 and h[m] >= tg + C.TICK) or (d < 0 and lo[m] <= tg - C.TICK)):
                    px, x = tg, m
                    break
                if lk and d * ((h[m] if d > 0 else lo[m]) - lk[0]) >= 0 and d * (lk[1] - stop) > 0:
                    stop = lk[1]
            day_legs.append({"a": e, "x": x, "d": d, "entry": entry, "px": px, "q": q, "stopped": stopped})
            if not (reverse and stopped and len(day_legs) == 1):
                break
            want, j = -d, x + 1  # the stop bar's own touch of the other level counts from the next bar
        if day_legs:
            out.append(day_legs)
    return out


def piece(bars, a, b, d, entry, px, q):
    """A position of q contracts from bar a to its exit at bar b (price px), as a leg for leg_paths."""
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    day = bars.index[a].tz_convert(A.NY).normalize().tz_localize(None)
    hp, lp = (h[a:b] - entry, lo[a:b] - entry) if d > 0 else (entry - lo[a:b], entry - h[a:b])
    pnl = d * (px - entry) * C.PV - C.FEE
    return (day, a, b, np.append(hp * C.PV - C.FEE, pnl) * q, np.append(lp * C.PV - C.FEE, pnl) * q, q * pnl)


def combine(bars, bot, cands, together):
    """The bot's legs all kept; the Williams trades by the rules above. Returns legs for leg_paths and the trades
    as (session, $, a Williams trade?)."""
    o = bars.open.to_numpy(float)
    spans = sorted((t.entry_bar, t.exit_bar, t.direction) for t in bot)
    starts = [s for s, _, _ in spans]
    legs = T.bot_legs(bars, bot, BOTQ)
    trades = [(leg[0], leg[5], False) for leg in legs]
    for day_legs in cands:
        prev_stopped = True
        for w in day_legs:
            if not prev_stopped:
                break
            a, x, d, entry, px, q = w["a"], w["x"], w["d"], w["entry"], w["px"], w["q"]
            k = int(np.searchsorted(starts, a, side="right")) - 1
            cover = spans[k] if k >= 0 and spans[k][0] <= a <= spans[k][1] else None
            if cover and not (together and cover[2] == d):
                prev_stopped = False  # not taken: no reverse after it either
                continue
            if cover:
                q = min(q, MAXQ - BOTQ)
            pnl_w, cut = 0.0, False
            k0 = int(np.searchsorted(starts, a, side="right"))
            for s, _, bd in spans[k0:]:
                if s > x:
                    break
                if bd != d or not together:  # closed at the bot's entry minute's open
                    cpx = o[s] - d * C.TICK
                    legs.append(piece(bars, a, s - 1, d, entry, cpx, q))
                    pnl_w += legs[-1][5]
                    cut = True
                    break
                if q > MAXQ - BOTQ:  # trimmed to 6 at the bot's entry
                    extra = q - (MAXQ - BOTQ)
                    legs.append(piece(bars, a, s - 1, d, entry, o[s] - d * C.TICK, extra))
                    pnl_w += legs[-1][5]
                    q -= extra
            if not cut:
                legs.append(piece(bars, a, x, d, entry, px, q))
                pnl_w += legs[-1][5]
            trades.append((legs[-1][0], pnl_w, True))
            prev_stopped = w["stopped"] and not cut
    return legs, trades


def job(args):
    path, periods = args
    bars = A.rth(path)
    ev_bot = T.bot_trades(bars, 3, 1.0, 2.5)
    pa_bot = T.bot_trades(bars, 2, 0.5, 6.25)
    cand = {r: w_candidates(bars, r) for r in (False, True)}
    sess = list(T.sessions_of(bars))
    rows = []
    for name in SETUPS:
        tog, rev = name in ("together", "both"), name in ("reverse", "both")
        rows += evaluate(bars, sess, ev_bot, pa_bot, cand[rev], tog, periods, name)
    return rows


def evaluate(bars, sess, ev_bot, pa_bot, cands, tog, periods, name):
    """The measures, per period, of the bot plus these Williams candidates."""
    ev_legs, ev_tr = combine(bars, ev_bot, cands, tog)
    pa_legs, _ = combine(bars, pa_bot, cands, tog)
    return evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name)


def evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name):
    """The measures, per period, from the evaluation's and the funded account's legs (combine's output)."""
    rows = []
    ev_all, pa_all = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
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
        f20 = [F.first_payout(pa_days[s:], 1, None, None, 20) for s in starts]
        ss_p = [d for d in ss if d <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex(ss_p))
        for dday, pnl, _, _ in ev_all:
            if dday in daily.index:
                daily[dday] += pnl
        eq = daily.cumsum()
        res = [r for r, _ in outs]
        in_p = [t for t in ev_tr if pd.Timestamp(first) <= t[0] <= last]
        w_p = [t[1] for t in in_p if t[2]]
        rows.append({"period": label, "setup": name, "winners %": 100 * np.mean([t[1] > 0 for t in in_p]),
                     "W winners %": 100 * np.mean(np.array(w_p) > 0),
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean(),
                     "trades/week": len(in_p) / max(1, len(set(daily.index.to_period("W")))),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "eval pass %": 100 * res.count("passed") / len(res),
                     "eval bust %": 100 * res.count("failed") / len(res),
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in f20])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    winners = []
    for name in SETUPS[1:]:
        ok = True
        for p in ("2011-2018", "2019-2025", "NQ 2015-2024"):
            v, b = key.loc[(name, p)], key.loc[("round 101", p)]
            ok &= bool(v["$/week"] > b["$/week"] and v["eval pass %"] >= b["eval pass %"] and
                       v["$ paid per eval"] >= b["$ paid per eval"] and v["paid in 20 %"] >= b["paid in 20 %"])
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            winners.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in df.period.unique()), name))
    print(f"ADOPT {max(winners)[1]}" if winners else "NOT ADOPTED")


if __name__ == "__main__":
    main()
