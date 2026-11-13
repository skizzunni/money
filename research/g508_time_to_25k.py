"""G508 (docs/NINJATRADER_V38.md), a measurement: how long a fresh 50K takes to reach +$25,000, over up to 24 months
(G372's development / unseen starts with 24 months of data). Per start, the first month whose cumulative net is at
+$25,000; the share there by 12, 18 and 24 months, the median month among those that get there, the share lost.
U58 (Funded growth), Funded growth plus, Funded aggressive.

    python research/g508_time_to_25k.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> unseen
"""
import sys

import g250_test_week as G
import g386_funded_chop_pause as R
import numpy as np
import pandas as pd
from g423_wide_when_wild import U58

from mnqbot.noise import NoiseConfig, run

V = {"U58 (Funded growth)": {**U58, "giveback_brake": 0.25},
     "Funded growth plus": {**U58, "giveback_brake": 0.25, "profit_step": 1250.0},
     "Funded aggressive": {**U58, "giveback_brake": 0.0, "profit_step": 1000.0, "early_daily_loss": 1000.0}}
MONTHS = 24


def job24(a):
    tag, name, start = a
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=31 * MONTHS + 7))]
    if b.index[-1] < s0 + pd.Timedelta(days=30.4 * MONTHS):
        return None
    cfg = NoiseConfig(**{**G.S.V23, **G.T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE, **V[tag]})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    bt = b.index.tz_convert(G.NY)
    bd = np.array(bt.date)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute, strict=False)
                   if d >= s0.date() and 570 <= m < 960})
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
        if month <= MONTHS:
            rows.append({"tag": tag, "set": name, "start": start, "month": month, "pnl": 0.0 if lost else pnl[d],
                         "lost": lost})
    return rows


def table(d):
    out = {}
    for tag, x in d.groupby("tag"):
        firsts, lost = [], []
        for _, y in x.groupby(["set", "start"]):
            cum = y.groupby("month").pnl.sum().cumsum()
            hit = cum[cum >= 25000.0]
            firsts.append(hit.index[0] if len(hit) else np.nan)
            lost.append(bool(y.lost.any()))
        f = pd.Series(firsts)
        out[tag] = {"starts": len(f), "by_12m": (f <= 12).mean(), "by_18m": (f <= 18).mean(),
                    "by_24m": (f <= 24).mean(), "median_month_if_reached": f.median(), "lost_24m": np.mean(lost)}
    return pd.DataFrame(out).T


if __name__ == "__main__":
    sys.argv.pop(5)
    R.VARIANTS.clear()
    R.VARIANTS.update(V)
    R.job = job24
    R.table = table
    pd.set_option("display.width", 250)
    R.main()
