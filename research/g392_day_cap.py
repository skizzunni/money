"""G392 (docs/NINJATRADER_V38.md): a measurement of what caps U48: G391 with the daily loss budget at $900 / $2,000
/ $3,000 (hypothetical). G391: U48 funded from fresh starts on the first Monday of every quarter, run
36 months: $ a session by month since the start, the share of starts lost (G372's intraday check), and the share of
starts averaging $750 a session in that month.

    python research/g392_day_cap.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import numpy as np
import pandas as pd

from mnqbot.noise import NoiseConfig, run

VARIANTS = {"U48": {}, "day budget $2,000": {"daily_loss_limit": 2000.0},
    "day budget $3,000": {"daily_loss_limit": 3000.0}}


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
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute,
        strict=False) if d >= s0.date() and 570 <= m < 960})
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    adv, closed = np.zeros(len(b)), np.zeros(len(b))
    pnl = {d: 0.0 for d in days}
    for t in res.trades:
        d = t.exit_time.tz_convert(G.NY).date()
        if t.entry_time < s0 or d not in pnl:
            continue
        sl = slice(t.entry_bar + 1, t.exit_bar + 1)
        adv[sl] += t.qty * ((lo[sl] - t.entry) if t.direction > 0 else (t.entry - hi[sl])) * G.PV
        closed[t.exit_bar] += t.pnl
        pnl[d] += t.pnl
    before = np.r_[0.0, np.cumsum(closed)[:-1]]
    eod, peak, lost, rows = 0.0, 0.0, False, []
    for d in days:
        fl = min(peak - G.DD, 0.0)
        m = bd == d
        lost = lost or bool((before[m] + adv[m] <= fl).any() or (before[m] + closed[m] <= fl).any())
        eod += pnl[d]
        peak = max(peak, eod)
        month = (pd.Timestamp(d).year - s0.year) * 12 + pd.Timestamp(d).month - s0.month + 1
        if month <= 36:
            rows.append({"tag": tag, "set": name, "start": start, "month": month, "pnl": 0.0 if lost else pnl[d],
                         "lost": lost})
    return rows


def table(d):
    y3 = d[d.month >= 25]
    m = y3.groupby(["tag", "start", "set", "month"]).agg(pnl=("pnl", "mean"), lost=("lost", "max")).reset_index()
    return m.groupby("tag").agg(per_session_year3=("pnl", "mean"), at_750=("pnl", lambda x: (x >= 750).mean()),
                                lost=("lost", "mean"))


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    starts = [("index", mon(d)) for d in pd.date_range("2011-04-01", "2023-07-01", freq="QS")]
    starts += [("nq", mon(d)) for d in pd.date_range("2015-04-01", "2022-07-01", freq="QS")]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        rows = [x for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts]) if r for x in r]
    print(f"{len(starts)} starts\n" + table(pd.DataFrame(rows)).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
