"""Round one hundred and one: the bot first, the Williams breakout only in its gaps.

    python research/combo_priority.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round one hundred: one position at a time, first come first served, blocked some of the bot's trend days. Here the bot
keeps every trade: a Williams trade is taken only when the bot is flat, and when the bot enters while a Williams trade
is open, the Williams trade is closed at that minute's open (less a tick) first. Everything else as round one hundred
(research/combo_live.py). Chosen after seeing round one hundred, so the bar is round one hundred's, unchanged: higher
evaluation pass rate and more $ a week than the bot alone in all three periods, payouts per evaluation at least 90%.
"""
from __future__ import annotations

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


def priority(bars, bot, w):
    """The bot's legs all kept; each Williams leg kept only if it starts while the bot is flat, and cut at the open of
    the next bot entry that comes while it's open."""
    o = bars.open.to_numpy(float)
    out = list(bot)
    spans = sorted((a, b) for a, b, *_ in bot)
    for a, b, d, entry, px, pnl, q in w:
        if any(s <= a <= e for s, e in spans):
            continue  # the bot is in a trade
        nxt = [s for s, _ in spans if a < s <= b]
        if nxt:
            b = nxt[0]
            px = o[b] - d * C.TICK
            pnl = q * (d * (px - entry) * C.PV - C.FEE)
            b -= 1  # flat before the bot's entry minute
        out.append((a, b, d, entry, px, pnl, q))
    return out


def job(args):
    path, periods = args
    bars = A.rth(path)
    w = C.williams_legs(bars)
    ev = priority(bars, C.bot_legs(bars, 3, 1.0, 2.5), w)
    pa = priority(bars, C.bot_legs(bars, 2, 0.5, 6.25), w)
    ev_p, pa_p = C.paths(bars, ev), C.paths(bars, pa)
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
        eq = daily.cumsum()
        rows.append({"period": label, "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "winners %": 100 * np.mean(np.array(pn) > 0), "red days %": 100 * (daily < 0).mean(),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "eval pass %": 100 * passes / n, "eval bust %": 100 * busts / n,
                     "$ paid per eval": float(np.mean(paid)),
                     "paid in 20 %": 100 * np.mean([r[0] == "paid" for r in firsts])})
    return rows


BOT = {"2011-2018": (272.2, 27.5, 1134.5), "2019-2025": (270.0, 22.9, 585.3), "NQ 2015-2024": (245.3, 25.3, 627.5)}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 200)
    print(df.round(1).to_string(index=False))
    ok = True
    for _, r in df.iterrows():
        wk, pr, pe = BOT[r.period]  # the bot alone, round one hundred, same machinery
        good = r["eval pass %"] > pr and r["$/week"] > wk and r["$ paid per eval"] >= 0.9 * pe
        ok &= good
        print(f"{r.period}: {'PASS' if good else 'FAIL'}")
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
