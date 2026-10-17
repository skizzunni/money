"""Round sixty-two: a second strategy for the quiet days, a fade inside the noise area, next to the bot on one account.

    python research/quiet_fade.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants more trades in a week on one 50K account. The bot trades on about 57% of days: only when a half-hour
check closes outside the noise area. On the other days price stays inside it. The noise area is, by construction,
where price usually stays: a move to its outer part that has not broken out may be more likely to come back than to
go on. If that is true, fading it adds trades on exactly the days and hours the bot is idle, with a natural stop:
the point where the bot itself would buy (the breakout), so the two never fight for long.

Rules (5-minute bars, New York time, the bot's own check bars and noise: sigma = the 14-session average of
|close / day open - 1| at that half hour, anchors max(day open, previous close) above and min(...) below):
  * at a check from 10:00 to 15:00, if the fade is allowed (gate below) and the close is more than F x sigma above
    the upper anchor but not above the upper line (anchor x (1 + sigma)): SELL 4 MNQ at the next bar's open plus a
    tick of slippage. Mirror image below: BUY when the close is more than F x sigma under the lower anchor but not
    under the lower line;
  * target: back to the anchor ("anchor"), or halfway from the expected fill to the anchor ("half"); a limit, filled
    at its price once price trades a tick through it, from the fill bar;
  * stop: the line plus 0.24 sigma (where the bot's own line stop sits for a breakout), or the $200 max loss from
    the fill (25 points at 4 MNQ), whichever is closer; filled at the stop minus a tick, or at the open if the open
    is past it; when a bar reaches both the stop and the target, the stop (worst case);
  * when the bot signals an entry while a fade is open, the fade closes at the bot's fill (next bar's open, a tick
    of slippage) so the account never holds both; flat at the 16:00 close; at most M fades a day;
  * gate "fresh": the bot has not entered a trade today and is flat; gate "flat": the bot is flat at that moment
    (no position, no entry pending).
  * $1.24 fees a contract round trip. The bot alongside: 4 MNQ, $200 max loss, 3 losers a day, take-profit from the
    fill (the account's evaluation setting), Fed rule from research/fomc_dates.csv, no skip dates.
  * prices are rescaled month by month (HistData index data), so trades entered on each month's first session are
    left out, for the bot and the fade alike.

Variants, fixed before running (10): F in {0.5, 0.75} x target in {anchor, half} x gate in {fresh, flat}, at most 1
fade a day (8); and F 0.5 / anchor / flat and F 0.75 / anchor / flat with at most 2 fades a day (2).
Pass bar, fixed before running: on 2011-2018 the variant with the most $ a day must (a) make money on its own with a
t-stat of at least 2 (daily P/L), and (b) bot + fade must beat the bot alone on $ a day and on $ a day per $1,000 of
the worst losing stretch. The same variant must then pass (a) and (b) on 2019 - Sep 2026 and on NQ futures
2015 - July 2025. Also reported: trades a week, days with a trade, and the 50K intraday-trail evaluation pass rate
($3,000 target, $2,000 drawdown trailing open profit, 30 days; research/apex25k.py's attempt, open P/L minute by
minute from the 1-minute bars) for the bot alone and with the fade.
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

from mnqbot.data import NY, resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30
Q, PV, TICK, FEE = 4, 2.0, 0.25, 1.24  # contracts, $ a point, tick, round-trip fees a contract
CAP = 200.0 / Q / PV  # 25 points
BUF, LOOKBACK, NCHK = 0.24, 14, 12
FED = ",".join(pd.read_csv(Path(__file__).with_name("fomc_dates.csv")).date)
VARIANTS = {f"F{f} {t} {g} x{m}": (f, t, g, m) for f in (0.5, 0.75) for t in ("anchor", "half")
            for g in ("fresh", "flat") for m in (1,)}
VARIANTS.update({"F0.5 anchor flat x2": (0.5, "anchor", "flat", 2),
                 "F0.75 anchor flat x2": (0.75, "anchor", "flat", 2)})
BOT = NoiseConfig(qty=Q, max_loss_per_trade=200.0, max_losers=3, target_on_fill_bar=True, fed_dates=FED, skip_dates="")


def load(path):
    one = A.rth(path)
    five = resample(one, "5min")
    return one, five


def checks(five):
    """Per bar: sigma, upper/lower anchors at check bars (NaN elsewhere), the same way mnqbot.noise builds them."""
    idx = five.index.tz_convert(NY)
    o, c = five.open.to_numpy(float), five.close.to_numpy(float)
    n = len(five)
    sig, up_a, lo_a = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    ring = np.full(LOOKBACK * NCHK, np.nan)
    today = [np.nan] * NCHK
    filled = slot = 0
    day_open = prev_close = last = np.nan
    for i in range(n):
        t = idx[i]
        tm = t.hour * 60 + t.minute
        end = tm + 5
        rth = tm >= 570 and end <= 960
        if tm == 570:
            prev_close, day_open, today = last, o[i], [np.nan] * NCHK
        if rth:
            last = c[i]
        if rth and not math.isnan(day_open) and 600 <= end <= 930 and (end - 600) % 30 == 0:
            k = (end - 600) // 30
            today[k] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sig[i] = sum(ring[d * NCHK + k] for d in range(LOOKBACK)) / LOOKBACK
                up_a[i], lo_a[i] = max(day_open, prev_close), min(day_open, prev_close)
        if rth and end == 960:
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * NCHK:(slot + 1) * NCHK] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = np.nan
    return sig, up_a, lo_a


def fades(five, bot, sig, up_a, lo_a, f, tgt, gate, most):
    """The fade trades: (entry bar, exit bar, direction, entry, exit, pnl $ for Q contracts)."""
    idx = five.index.tz_convert(NY)
    o, h, l, c = (five[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(five)
    in_bot = np.zeros(n, bool)  # the bot holds a position during this bar
    pend = np.zeros(n, bool)  # the bot's entry fills at this bar's open
    bot_day = {}
    for t in bot.trades:
        in_bot[t.entry_bar:t.exit_bar + 1] = True
        pend[t.entry_bar] = True
        d = idx[t.entry_bar].date()
        bot_day[d] = min(bot_day.get(d, n), t.entry_bar)
    out, pos = [], 0
    count, day = 0, None
    eb, ep, stop, tp = 0, 0.0, 0.0, 0.0  # the open fade: fill bar, fill price, stop, target
    for i in range(n - 1):
        t = idx[i]
        tm = t.hour * 60 + t.minute
        if t.date() != day:
            day, count = t.date(), 0
        if pos:  # manage the open fade on bar i
            hit = px = None
            if pend[i]:  # the bot enters at this open: the fade goes out with it
                hit, px = "bot", o[i] - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = "stop", o[i] - pos * TICK
            elif (pos > 0 and l[i] <= stop) or (pos < 0 and h[i] >= stop):
                hit, px = "stop", stop - pos * TICK
            elif (pos > 0 and h[i] >= tp + TICK) or (pos < 0 and l[i] <= tp - TICK):
                hit, px = "target", tp
            elif tm + 5 == 960:
                hit, px = "close", c[i] - pos * TICK
            if hit:
                out.append((eb, i, pos, ep, px, pos * (px - ep) * Q * PV - FEE * Q))
                pos = 0
        if pos or math.isnan(sig[i]) or not (600 <= tm + 5 <= 900) or count >= most:
            continue
        if in_bot[i] or pend[i + 1] or in_bot[i + 1]:
            continue
        if gate == "fresh" and bot_day.get(t.date(), n) <= i:
            continue
        s, ua, la = sig[i], up_a[i], lo_a[i]
        upper, lower = ua * (1 + s), la * (1 - s)
        d = 0
        if ua * (1 + f * s) < c[i] <= upper:
            d, anchor, line_stop = -1, ua, upper * (1 + BUF * s)
        elif lower <= c[i] < la * (1 - f * s):
            d, anchor, line_stop = 1, la, lower * (1 - BUF * s)
        if not d:
            continue
        j = i + 1  # fill at the next bar's open
        ep = o[j] + d * TICK
        est = c[i] + d * TICK
        tp = anchor if tgt == "anchor" else (est + anchor) / 2
        if d * (tp - ep) <= TICK:  # the open already at the target: no trade
            continue
        stop = max(line_stop, ep - CAP) if d > 0 else min(line_stop, ep + CAP)
        if (d > 0 and stop >= ep) or (d < 0 and stop <= ep):
            continue
        pos, eb, count = d, j, count + 1
        # the fill bar itself: checked on the next loop pass (i = j), as every later bar
    return out


def paths(one, five, trades):
    """Per trade: (session, pnl, running max of open P/L, open P/L path) in $, minute by minute (research/apex25k)."""
    m_idx = one.index
    hi1, lo1 = one.high.to_numpy(float), one.low.to_numpy(float)
    f_idx = five.index
    res = []
    for eb, xb, d, ep, _, pnl in trades:
        a = m_idx.searchsorted(f_idx[eb])
        b = m_idx.searchsorted(f_idx[xb])
        if d > 0:
            hp, lp = hi1[a:b] - ep, lo1[a:b] - ep
        else:
            hp, lp = ep - lo1[a:b], ep - hi1[a:b]
        hp = np.append(hp * Q * PV - FEE * Q, pnl)
        lp = np.append(lp * Q * PV - FEE * Q, pnl)
        day = f_idx[eb].tz_convert(NY).normalize().tz_localize(None)
        res.append((day, pnl, np.maximum.accumulate(hp), lp, f_idx[eb]))
    return res


def _job(args):
    path, name = args
    one, five = load(path)
    bot = run(five, BOT, minutes=5)
    bot_tr = [(t.entry_bar, t.exit_bar, t.direction, t.entry, t.exit, t.pnl) for t in bot.trades]
    if name == "bot":
        return name, paths(one, five, bot_tr)
    sig, ua, la = checks(five)
    return name, paths(one, five, fades(five, bot, sig, ua, la, *VARIANTS[name]))


def sessions_of(path):
    one = A.rth(path)
    m = one.index.tz_convert(NY)
    s = pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None))))
    first = set(pd.Series(s).groupby(s.to_period("M")).min())
    return s, first


def stats(trs, sess):
    d = pd.Series(0.0, index=sess)
    for day, pnl, *_ in trs:
        if day in d.index:
            d[day] += pnl
    eq = d.cumsum()
    worst = (eq.cummax() - eq).max()
    wins = np.mean([x[1] > 0 for x in trs]) if trs else float("nan")
    return {"trades/week": 5 * len(trs) / len(sess), "win %": 100 * wins, "$/day": d.mean(),
            "t": d.mean() / d.std(ddof=1) * math.sqrt(len(d)) if d.std() > 0 else 0.0, "worst stretch": worst,
            "eff": 1000 * d.mean() / worst if worst > 0 else float("nan"),
            "days traded %": 100 * len({x[0] for x in trs}) / len(sess)}


def eval_pass(trs, sess):
    by = {}
    for day, pnl, hi, lo, _ in sorted(trs, key=lambda x: x[4]):
        by.setdefault(day, []).append((pnl, hi, lo))
    days = [(x, by.get(x, [])) for x in sess]
    res = [A.attempt(days[s:], 1, "intraday", 30)[0] for s in range(len(days))]
    last = sess[-1]
    keep = [r for s, r in enumerate(res) if r != "timeout" or (last - sess[s]).days >= 30]
    return 100 * keep.count("passed") / len(keep), 100 * keep.count("failed") / len(keep)


def report(path, periods, out):
    names = ["bot", *VARIANTS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = dict(ex.map(_job, [(path, n) for n in names]))
    sess_all, first = sessions_of(path)
    res = {}
    for label, y0, y1 in periods:
        sess = sess_all[(sess_all.year >= y0) & (sess_all.year <= y1) & ~sess_all.isin(list(first))]
        keep = set(sess)
        sel = {n: [x for x in runs[n] if x[0] in keep] for n in names}
        rows = []
        for n in names:
            s = stats(sel[n], sess)
            comb = stats(sel["bot"] + sel[n], sess) if n != "bot" else s
            rows.append({"variant": n, **{k: s[k] for k in ("trades/week", "win %", "$/day", "t")},
                         "with bot $/day": comb["$/day"], "with bot eff": comb["eff"],
                         "with bot trades/week": comb["trades/week"], "with bot days %": comb["days traded %"]})
        df = pd.DataFrame(rows)
        print(f"\n{label}: each variant alone (4 MNQ), and the bot + it", file=out)
        print(df.round(2).to_string(index=False), file=out)
        res[label] = (df, sel, sess)
    return res


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    out = sys.stdout
    idx = report(nsx, (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026)), out)
    fut = report(nq, (("NQ 2015-2025", 2015, 2025),), out)
    allr = {**idx, **fut}
    disc = allr["2011-2018"][0]
    best = disc[disc.variant != "bot"].sort_values("$/day", ascending=False).iloc[0].variant
    print(f"\nbest on 2011-2018: {best}", file=out)
    ok = True
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        df, sel, sess = allr[label]
        b, bot = df[df.variant == best].iloc[0], df[df.variant == "bot"].iloc[0]
        a_ok = b["$/day"] > 0 and b["t"] >= 2
        b_ok = b["with bot $/day"] > bot["$/day"] and b["with bot eff"] > bot["with bot eff"]
        ok &= a_ok and b_ok
        p_bot, f_bot = eval_pass(sel["bot"], sess)
        p_comb, f_comb = eval_pass(sel["bot"] + sel[best], sess)
        print(f"  {label}: alone ${b['$/day']:.2f}/day t {b['t']:.2f} ({'PASS' if a_ok else 'FAIL'}); with the bot "
              f"${b['with bot $/day']:.2f}/day eff {b['with bot eff']:.2f} against ${bot['$/day']:.2f} eff "
              f"{bot['with bot eff']:.2f} ({'PASS' if b_ok else 'FAIL'}); trades/week {bot['trades/week']:.2f} -> "
              f"{b['with bot trades/week']:.2f}, days traded {bot['with bot days %']:.0f}% -> "
              f"{b['with bot days %']:.0f}%; 50K intraday evaluation pass/bust {p_bot:.1f}/{f_bot:.1f}% -> "
              f"{p_comb:.1f}/{f_comb:.1f}%", file=out)
    print(f"  {'PASS' if ok else 'FAIL'}", file=out)


if __name__ == "__main__":
    main()
