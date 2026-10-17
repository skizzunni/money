"""Round sixty-three: add contracts to a winner once its lock arms (pyramiding), on one 50K Apex account.

    python research/pyramid.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants more money a week from one account. The bot's profit comes from a few trend days. Once a trade has
gone +1 max loss in its favour the lock moves its stop to entry + 2.5 points: from then on the trade can't lose.
Adding contracts at that moment puts more size only on trades that are already working, the trend days, and the add
risks part of the open profit instead of the account's own money.

Base: the bot as it trades the 50K evaluation and funded account now (mnqbot.noise v1.6: 4 MNQ, $200 max loss, 3
losers a day, take-profit working from the fill), on 1-minute bars 09:30-16:00, $1.24 fees a contract, a tick of
slippage on every market and stop fill. The bot's own trades are unchanged; the add is a second leg:
  * the lock arms on the first minute of the trade (fill minute included) whose high (long) / low (short) reaches
    entry + 25 points (+1 max loss at 4 MNQ, $200), and that the trade survives;
  * the add buys (sells) N MNQ at the next minute's open plus a tick of slippage;
  * the add exits with the bot's trade at the trade's exit price (take-profit, stop, 16:00), unless its own stop
    is reached first; stops fill at the stop minus a tick, or at the minute's open minus a tick when the open is
    past it; in the trade's exit minute the add's stop counts first (worst case);
  * add stop "locked": the bot's locked stop, entry + 2.5 points (the bot's stop is never looser than that once
    locked, so the add leaves with the trade); add stop "25": the add price - 25 points;
  * one add a trade; the daily loser count is the bot's (the add doesn't change which trades the bot takes).
Equity minute by minute (open profit included) is the bot's leg plus the add's, so the evaluation's and the funded
account's trailing threshold follow the adds too.

Candidates, fixed before running: N = 2, 4 or 8 MNQ, add stop "locked" or "25" (6 variants), and the bot without
adds. Measures per period: $ a week, win % of trades (bot leg + add), worst losing stretch of closed daily P/L, the
Apex 50K intraday-trail evaluation within 30 days (pass / bust %, research/apex25k.py attempt with the $3,000 target
and $2,000 drawdown), and expected payouts per evaluation bought with the funded account at the same setting
(research/apex_payouts.py rules, base caps).
Pass bar, fixed before running: the 2011-2018 variant with the highest expected payouts per evaluation must beat the
bot without adds by at least 10% in payouts per evaluation, with a 30-day pass rate no lower, on 2019-2026 and on the
NQ futures 2015-2025. Evaluations start every session up to 2018-12-31, 2025-06-30 (index) and 2024-12-31 (NQ).
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex_payouts as P  # noqa: E402  (sets the 50K evaluation constants in apex25k)
from apex25k import FED, FEE, PV, attempt, rth  # noqa: E402

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

Q, MAX_LOSS, LOSERS = 4, 200.0, 3
TRIG, LOCK_PLUS, SLIP = MAX_LOSS / Q / PV, 2.5, 0.25  # 25 points, entry + 2.5, a tick
VARIANTS = {"no add": None, "add 2 locked": (2, "locked"), "add 4 locked": (4, "locked"), "add 8 locked": (8, "locked"),
            "add 2, 25": (2, "25"), "add 4, 25": (4, "25"), "add 8, 25": (8, "25")}
PERIODS = {"2011-2018": ("2011-01-01", "2018-12-31", "2018-12-31"),
           "2019-2026": ("2019-01-01", "2026-12-31", "2025-06-30"),
           "NQ 2015-2025": ("2015-03-01", "2025-12-31", "2024-12-31")}


def bot_trades(path):
    bars = rth(path)
    cfg = NoiseConfig(qty=Q, max_loss_per_trade=MAX_LOSS, max_losers=LOSERS, fed_dates=FED, skip_dates="",
                      target_on_fill_bar=True)
    res = run(bars, cfg, minutes=1)
    return path, bars, res.trades


def legs(bars, trades, add):
    """Per trade: (day, P/L, running peak equity, low equity per minute), bot leg plus the add."""
    o, h, lo = (bars[k].to_numpy(float) for k in ("open", "high", "low"))
    out = []
    for t in trades:
        a, b, d, e = t.entry_bar, t.exit_bar, t.direction, t.entry
        best = (h[a:b] - e) if d > 0 else (e - lo[a:b])
        worst = (lo[a:b] - e) if d > 0 else (e - h[a:b])
        hi = np.append(best * PV * Q - FEE * Q, t.pnl)
        low = np.append(worst * PV * Q - FEE * Q, t.pnl)
        pnl = t.pnl
        if add is not None:
            n, kind = add
            arm = np.flatnonzero(best >= TRIG)  # minutes a..b-1, all survived by the trade
            if arm.size and a + arm[0] + 1 <= b:
                f = a + arm[0] + 1  # the add fills at this minute's open
                fill = o[f] + d * SLIP
                stop = e + d * LOCK_PLUS if kind == "locked" else fill - d * 25.0
                exit_px, exit_at = t.exit, b  # with the trade, unless its own stop first
                for j in range(f, b + 1):
                    if (d > 0 and lo[j] <= stop) or (d < 0 and h[j] >= stop):
                        px = (min(o[j], stop) if d > 0 else max(o[j], stop)) - d * SLIP
                        if j < b or d * (px - t.exit) < 0:  # in the exit minute, the worse of the two
                            exit_px, exit_at = px, j
                        break
                add_pnl = d * (exit_px - fill) * PV * n - FEE * n
                k = np.arange(a, b)
                live = (k >= f) & (k < exit_at)
                add_best = np.where(live, d * ((h[a:b] if d > 0 else lo[a:b]) - fill) * PV * n - FEE * n, 0.0)
                add_worst = np.where(live, d * ((lo[a:b] if d > 0 else h[a:b]) - fill) * PV * n - FEE * n, 0.0)
                done = k >= exit_at  # the add already closed: its P/L is banked
                add_best = np.where(done, add_pnl, add_best)
                add_worst = np.where(done, add_pnl, add_worst)
                hi = hi + np.append(add_best, add_pnl)
                low = low + np.append(add_worst, add_pnl)
                pnl += add_pnl
        day = t.entry_time.tz_convert(NY).normalize().tz_localize(None)
        out.append((day, pnl, np.maximum.accumulate(hi), low))
    return out


def sessions_of(bars):
    m = bars.index.tz_convert(NY)
    return list(pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))))


def _measure(args):
    name, label, tr, sess, last_start = args
    days = P.by_day(tr, sess)
    daily = np.array([sum(x[0] for x in ts) for _, ts in days])
    weeks = len({(d.isocalendar()[0], d.isocalendar()[1]) for d in sess})
    curve = np.cumsum(daily)
    stretch = float(np.max(np.maximum.accumulate(np.append(0, curve))[1:] - curve)) if len(curve) else 0.0
    outs, pay, memo = [], [], {}
    for s, day in enumerate(sess):
        if day > last_start:
            break
        res, used = attempt(days[s:], 1, "intraday", 30)
        outs.append(res)
        if res != "passed":
            pay.append(0.0)
            continue
        first = s + used
        if first not in memo:
            memo[first] = sum(x for _, x in P.pa_run(days[first:], 1, P.CAPS["base"])[0])
        pay.append(memo[first])
    n = len(outs)
    return {"period": label, "variant": name, "trades": len(tr), "$/week": daily.sum() / weeks,
            "win %": 100 * np.mean([x[1] > 0 for x in tr]), "worst stretch $": stretch,
            "eval pass %": 100 * outs.count("passed") / n, "eval bust %": 100 * outs.count("failed") / n,
            "$/eval": float(np.mean(pay))}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 200)
    with ProcessPoolExecutor(max_workers=3) as pool:
        runs = {p: (bars, trades) for p, bars, trades in pool.map(bot_trades, [nsx, nq])}
        jobs = []
        for label, (first, last, last_start) in PERIODS.items():
            bars, trades = runs[nq if label.startswith("NQ") else nsx]
            sess = [d for d in sessions_of(bars) if pd.Timestamp(first) <= d <= pd.Timestamp(last)]
            for name, add in VARIANTS.items():
                tr = [x for x in legs(bars, trades, add) if sess[0] <= x[0] <= sess[-1]]
                jobs.append((name, label, tr, sess, pd.Timestamp(last_start)))
        rows = pd.DataFrame(list(pool.map(_measure, jobs)))
    for label in PERIODS:
        print(f"\n{label}")
        print(rows[rows.period == label].drop(columns="period").round(1).to_string(index=False))
    disc = rows[(rows.period == "2011-2018") & (rows.variant != "no add")]
    best = disc.sort_values("$/eval", ascending=False).iloc[0].variant
    print(f"\nbest on 2011-2018 by payouts per evaluation: {best}")
    ok = True
    for label in PERIODS:
        d = rows[rows.period == label].set_index("variant")
        b, c = d.loc[best], d.loc["no add"]
        good = b["$/eval"] >= 1.1 * c["$/eval"] and b["eval pass %"] >= c["eval pass %"]
        if label != "2011-2018":
            ok &= good
        print(f"  {label}: ${b['$/eval']:.0f} per evaluation, {b['eval pass %']:.1f}% pass against "
              f"${c['$/eval']:.0f}, {c['eval pass %']:.1f}% without adds: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
