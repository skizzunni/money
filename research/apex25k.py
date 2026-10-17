"""Round fifty-nine: the max loss, contracts and daily loser limit for an Apex 25K evaluation.

    python research/apex25k.py nsx1m_scaled.pkl nq1m_scaled.pkl

Question (the user): is $350 a trade too much on a 25K evaluation, "we don't want to reach max drawdown instantly"?

Apex 25K evaluation (4.0, March 2026), from Apex's help center as search results quote it (the site itself refuses
this machine): $1,500 profit target, $1,000 trailing drawdown, 30 calendar days, no minimum days, no consistency rule
in the evaluation, up to 40 MNQ. Two plans, chosen at purchase:
  intraday trail: the threshold trails the highest equity INCLUDING open profit, minute by minute; no daily limit;
  end-of-day trail: the threshold is set from the closing balance and enforced during the next session; a $500 daily
    loss limit closes the position and stops trading for the day (not a fail).
Modelled on 1-minute bars with the bot itself (mnqbot.noise.run, v1.6 rules: line stop 0.24 noise units, take-profit
1.5 working from the fill as the NinjaTrader bracket does, lock at +1 max loss to entry + 2.5, 16:00 flat, Fed rule
with the FOMC dates of research/fomc_dates.csv), $1.24 fees a contract and a tick of slippage per fill. Equity inside
a trade: each minute's high and low, fees taken at entry. Inside a minute the worse order is assumed: the intraday
peak rises to the high first, then the low is checked against it. The threshold is not capped at the start balance
(Apex caps it at +$100 on funded accounts; inside a $1,500 evaluation that matters only after a $1,100 peak).
An evaluation starts on every session; it passes when the closed balance reaches +$1,500, fails when equity touches
the threshold, and times out after 30 calendar days. Also shown: pass within a year (no time limit), and how often
the unconstrained bot's day reaches -$500 and -$1,000 at its worst point.

Candidates, fixed before running (contracts, max loss a trade): the tested 17.5-point cap at 3, 5, 6, 7, 8 and 10 MNQ
($105 - $350); a 25-point cap at 2, 3, 4, 5 MNQ ($100 - $250); 3 MNQ at $200 and $250; 2 MNQ at $150 and $200; and
the current evaluation setting, 3 MNQ at $350 (58.3 points). Each with no new entries after 1, 2, 3 or 4 losers.
Pass bar, fixed before running, for each plan: the variant with the highest 30-day pass rate on 2011-2018 must beat
the current setting (3 MNQ, $350, 4 losers) by at least 5 points of pass rate, with a bust rate no higher, on
2019 - Sep 2026 and on the NQ futures 2015 - July 2025.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

PV, FEE = 2.0, 1.24  # $ a point a contract; round-trip fees a contract
TARGET, DD, DLL, DAYS = 1500.0, 1000.0, 500.0, 30
COMBOS = [(3, 17.5), (5, 17.5), (6, 17.5), (7, 17.5), (8, 17.5), (10, 17.5), (2, 25.0), (3, 25.0), (4, 25.0),
          (5, 25.0), (3, 100 / 3), (3, 125 / 3), (2, 37.5), (2, 50.0), (3, 175 / 3)]
LOSERS = (1, 2, 3, 4)
CURRENT = (3, 175 / 3, 4)
FED = ",".join(pd.read_csv(Path(__file__).with_name("fomc_dates.csv")).date)


def rth(path: str) -> pd.DataFrame:
    bars = pd.read_pickle(path)
    m = bars.index.tz_convert(NY)
    t = m.hour * 60 + m.minute
    return bars[(t >= 570) & (t < 961)]  # 09:30 - 16:00, and the 16:00 bar


def trades_for(args):
    """The bot at 1 contract with a cap_pts max loss: per trade, its session, P/L and its minute-by-minute equity."""
    path, cap, losers = args
    bars = rth(path)
    cfg = NoiseConfig(qty=1, max_loss_per_trade=cap * PV, max_losers=losers, fed_dates=FED, skip_dates="",
                      target_on_fill_bar=True)
    res = run(bars, cfg, minutes=1)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for t in res.trades:
        a, b = t.entry_bar, t.exit_bar
        if t.direction > 0:
            hi_path, lo_path = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hi_path, lo_path = t.entry - lo[a:b], t.entry - h[a:b]
        pnl = t.pnl  # the exit minute counts at the exit price
        hi_path = np.append(hi_path * PV - FEE, pnl)
        lo_path = np.append(lo_path * PV - FEE, pnl)
        out.append((t.entry_time.tz_convert(NY).normalize().tz_localize(None), pnl, np.maximum.accumulate(hi_path),
                    lo_path))
    return (cap, losers), out


def attempt(days, q, plan, horizon_days):
    """One evaluation from days[0]: 'passed', 'failed' or 'timeout', and sessions used."""
    bal = peak = 0.0
    thr = -DD
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon_days:
            return "timeout", n
        day_start = bal
        for pnl, hi_run, lo_path in trades:
            if plan == "intraday":
                run_peak = np.maximum(peak - bal, q * hi_run)  # the peak, open profit included, minute by minute
                if (q * lo_path - run_peak <= -DD).any():
                    return "failed", n + 1
                peak = max(peak, bal + q * hi_run[-1])
            else:  # whichever comes first: the threshold (a fail) or the daily loss limit (closed, done for today)
                eq = bal + q * lo_path
                bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -DLL)
                if bust.size and (not stop.size or bust[0] <= stop[0]):
                    return "failed", n + 1
                if stop.size:
                    bal = day_start - DLL
                    if bal <= thr:
                        return "failed", n + 1
                    break
            bal += q * pnl
            peak = max(peak, bal)
            if bal >= TARGET:
                return "passed", n + 1
        if plan == "eod":
            peak = max(peak, bal)
            thr = peak - DD
    return "timeout", len(days)


def odds(by_day, sessions, q, plan, horizon_days=DAYS):
    days = [(d, by_day.get(d, [])) for d in sessions]
    res = [attempt(days[s:], q, plan, horizon_days) for s in range(len(days))]
    # attempts whose window runs past the data are dropped
    last = sessions[-1]
    keep = [r for s, r in enumerate(res) if r[0] != "timeout" or (last - sessions[s]).days >= horizon_days]
    n = len(keep)
    outs = [r[0] for r in keep]
    used = [r[1] for r in keep if r[0] == "passed"]
    return (100 * outs.count("passed") / n, 100 * outs.count("failed") / n, 100 * outs.count("timeout") / n,
            float(np.median(used)) if used else float("nan"))


def worst_days(by_day, sessions, q):
    worst = []
    for d in sessions:
        bal, low = 0.0, 0.0
        for pnl, _, lo_path in by_day.get(d, []):
            low = min(low, bal + q * lo_path.min())
            bal += q * pnl
        worst.append(low)
    w = np.array(worst)
    return 100 * (w <= -DLL).mean(), 100 * (w <= -DD).mean()


def _eval(args):
    key, trades, sessions, q, label = args
    by_day = {}
    for day, pnl, hi_run, lo_path in trades:
        by_day.setdefault(day, []).append((pnl, hi_run, lo_path))
    row = {"period": label, "MNQ": q, "max loss $": round(q * key[0] * PV), "losers": key[1]}
    for plan in ("intraday", "eod"):
        p, f, t, med = odds(by_day, sessions, q, plan)
        row.update({f"{plan} pass %": p, f"{plan} bust %": f, f"{plan} timeout %": t, f"{plan} days": med})
    row["eod pass 1y %"] = odds(by_day, sessions, q, "eod", 365)[0]
    row["intraday pass 1y %"] = odds(by_day, sessions, q, "intraday", 365)[0]
    row["day <= -500 %"], row["day <= -1000 %"] = worst_days(by_day, sessions, q)
    row["$/day"] = q * sum(x[1] for x in trades) / len(sessions)
    return row


def table(path, periods, combos, pool):
    keys = sorted({(cap, lz) for _, cap in combos for lz in LOSERS})
    runs = dict(pool.map(trades_for, [(path, cap, lz) for cap, lz in keys]))
    bars = rth(path)
    m = bars.index.tz_convert(NY)
    sess = pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None))))
    jobs = []
    for label, y0, y1 in periods:
        ss = list(sess[(sess.year >= y0) & (sess.year <= y1)])
        for q, cap in combos:
            for lz in LOSERS:
                tr = [x for x in runs[(cap, lz)] if y0 <= x[0].year <= y1]
                jobs.append(((cap, lz), tr, ss, q, label))
    return pd.DataFrame(list(pool.map(_eval, jobs)))


COLS = ["MNQ", "max loss $", "losers", "intraday pass %", "intraday bust %", "intraday timeout %", "intraday days",
        "eod pass %", "eod bust %", "eod timeout %", "eod days", "intraday pass 1y %", "eod pass 1y %",
        "day <= -500 %", "day <= -1000 %", "$/day"]


def is_current(df):
    return (df.MNQ == 3) & (df["max loss $"] == 350) & (df.losers == 4)


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=4) as pool:
        idx = table(nsx, (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026)), COMBOS, pool)
        fut = table(nq, (("NQ 2015-2025", 2015, 2025),), COMBOS, pool)
    allr = pd.concat([idx, fut])
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        d = allr[allr.period == label]
        print(f"\n{label}, sorted by the end-of-day plan's 30-day pass rate")
        print(d.sort_values("eod pass %", ascending=False)[COLS].round(1).to_string(index=False))
    for plan in ("intraday", "eod"):
        disc = allr[allr.period == "2011-2018"]
        best = disc.sort_values(f"{plan} pass %", ascending=False).iloc[0]
        key = (best.MNQ, best["max loss $"], best.losers)
        print(f"\n{plan} plan: best on 2011-2018 is {key[0]} MNQ, ${key[1]}, {key[2]} losers "
              f"({best[f'{plan} pass %']:.1f}% pass)")
        ok = True
        for label in ("2019-2026", "NQ 2015-2025"):
            d = allr[allr.period == label]
            b = d[(d.MNQ == key[0]) & (d["max loss $"] == key[1]) & (d.losers == key[2])].iloc[0]
            c = d[is_current(d)].iloc[0]
            good = b[f"{plan} pass %"] >= c[f"{plan} pass %"] + 5 and b[f"{plan} bust %"] <= c[f"{plan} bust %"]
            ok &= good
            print(f"  {label}: {b[f'{plan} pass %']:.1f}% pass / {b[f'{plan} bust %']:.1f}% bust against the current "
                  f"{c[f'{plan} pass %']:.1f}% / {c[f'{plan} bust %']:.1f}%: {'PASS' if good else 'FAIL'}")
        print(f"  {plan} plan: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
