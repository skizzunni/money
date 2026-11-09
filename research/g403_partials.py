"""G403 (docs/NINJATRADER_V38.md): more green days on the 50K: U48 taking half off at a small profit (`partial_at`,
R = the max loss a contract), 36 months, development (index starts 2011-2016) and unseen (index 2017-2023,
NQ 2015-2022): $ a session, lost, trades a session, green days of traded days, green weeks / months, longest losing-week
run, worst month.

    python research/g403_partials.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import g250_test_week as G
from mnqbot.noise import NoiseConfig, run

VARIANTS = {"U48": {}, "half off at 0.5R": {"partial_at": 0.5, "partial_next_bar": True}, "half off at 1R": {"partial_at": 1.0, "partial_next_bar": True}, "half off at 0.5R, rest to break-even": {"partial_at": 0.5, "partial_be": True, "partial_next_bar": True}}


def job(a):
    tag, name, start = a
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=1102))]
    if b.index[-1] < s0 + pd.Timedelta(days=1090):
        return None
    cfg = NoiseConfig(**{**G.S.V23, **G.T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE, **VARIANTS[tag]})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    bt = b.index.tz_convert(G.NY)
    bd = np.array(bt.date)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute) if d >= s0.date() and 570 <= m < 960})
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    adv, closed = np.zeros(len(b)), np.zeros(len(b))
    pnl = {d: 0.0 for d in days}
    nt = {d: 0 for d in days}
    for t in res.trades:
        d = t.exit_time.tz_convert(G.NY).date()
        if t.entry_time < s0 or d not in pnl:
            continue
        sl = slice(t.entry_bar + 1, t.exit_bar + 1)
        adv[sl] += t.qty * ((lo[sl] - t.entry) if t.direction > 0 else (t.entry - hi[sl])) * G.PV
        closed[t.exit_bar] += t.pnl
        pnl[d] += t.pnl
        nt[d] += 1
    before = np.r_[0.0, np.cumsum(closed)[:-1]]
    eod, peak, lost, rows = 0.0, 0.0, False, []
    for d in days:
        fl = min(peak - cfg.trail_dd, 0.0)
        m = bd == d
        lost = lost or bool((before[m] + adv[m] <= fl).any() or (before[m] + closed[m] <= fl).any())
        eod += pnl[d]
        peak = max(peak, eod)
        month = (pd.Timestamp(d).year - s0.year) * 12 + pd.Timestamp(d).month - s0.month + 1
        if month <= 36:
            rows.append({"tag": tag, "set": name, "start": start, "month": month, "pnl": 0.0 if lost else pnl[d], "n": 0 if lost else nt[d], "date": str(d),
                         "lost": lost})
    return rows


def table(d):
    d = d.assign(date=pd.to_datetime(d.date))
    out = {}
    for tag, x in d.groupby("tag"):
        per = []
        for (_, _), y in x.groupby(["set", "start"]):
            y = y.sort_values("date")
            wk = y.groupby(y.date.dt.to_period("W")).pnl.sum()
            mo = y.groupby(y.date.dt.to_period("M")).pnl.sum()
            run = best = 0
            for v in wk:
                run = run + 1 if v < 0 else 0
                best = max(best, run)
            tr = y[y.n > 0]
            per.append({"green_days": (tr.pnl > 0).mean() if len(tr) else 0, "green_weeks": (wk > 0).mean(),
                        "green_months": (mo > 0).mean(), "longest_losing_weeks": best, "worst_month": mo.min(),
                        "lost": bool(y.lost.any())})
        p = pd.DataFrame(per)
        out[tag] = {"per_session": x.pnl.mean(), "trades_per_session": x.n.mean(), "lost": p.lost.mean(),
                    **p.drop(columns="lost").mean().to_dict()}
    return pd.DataFrame(out).T


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    dev = [("index", mon(d)) for d in pd.date_range("2011-04-01", "2016-10-01", freq="QS")]
    unseen = [("index", mon(d)) for d in pd.date_range("2017-01-01", "2023-07-01", freq="QS")]
    unseen += [("nq", mon(d)) for d in pd.date_range("2015-04-01", "2022-07-01", freq="QS")]
    pd.set_option("display.width", 250)
    for label, starts in (("development", dev), ("unseen", unseen)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            rows = [x for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts]) if r for x in r]
        print(label + ":\n" + table(pd.DataFrame(rows)).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
