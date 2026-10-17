"""Round eighty-one: the NinjaTrader strategy on a 5-minute chart against a 1-minute chart (description).

    python research/chart_minutes.py nsx1m_scaled.pkl nq1m_scaled.pkl

The strategy works on bar closes: on a 5-minute chart the lock (stop to entry + 2.5 once a trade is +1 max loss up)
arms only when the 5-minute bar closes, and the stop and target move every 5 minutes; on a 1-minute chart, every
minute. Every Apex simulation (rounds fifty-nine to eighty) used the 1-minute engine. The same bot at the account's
settings (4 MNQ, $200, 3 losers, take-profit from the fill) on both bar lengths, the 5-minute bars built from the same
1-minute data: trades, winners, $ a week, worst losing stretch, and the 50K intraday-trail evaluation pass / bust %
(research/apex25k.py attempt, minute equity from the 1-minute bars between each trade's entry and exit).
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

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0


def paths(bars1, trades, step):
    """Per trade: (session, pnl, running max of minute equity, minute equity), the path from the 1-minute bars."""
    idx = bars1.index
    h, lo = bars1.high.to_numpy(float), bars1.low.to_numpy(float)
    out = []
    for t in trades:
        a = idx.searchsorted(t.entry_time)
        b = idx.searchsorted(t.exit_time + pd.Timedelta(minutes=step - 1), side="right")
        if t.direction > 0:
            hi, lp = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hi, lp = t.entry - lo[a:b], t.entry - h[a:b]
        hi = np.append(hi * A.PV - A.FEE, t.pnl)
        lp = np.append(lp * A.PV - A.FEE, t.pnl)
        out.append((t.entry_time.tz_convert(A.NY).normalize().tz_localize(None), t.pnl, np.maximum.accumulate(hi), lp))
    return out


def job(args):
    path, step, periods = args
    bars1 = A.rth(path)
    bars = bars1 if step == 1 else resample(bars1, f"{step}min")
    cfg = NoiseConfig(qty=1, max_loss_per_trade=25.0 * A.PV, max_losers=3, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True)
    trades = run(bars, cfg, minutes=step).trades
    pt = paths(bars1, trades, step)
    m = bars1.index.tz_convert(A.NY)
    sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, y0, y1, last in periods:
        ss = [x for x in sess if y0 <= x.year <= y1]
        d = {}
        for day, pnl, hi, lp in pt:
            if y0 <= day.year <= y1:
                d.setdefault(day, []).append((pnl, hi, lp))
        days = [(x, d.get(x, [])) for x in ss]
        res = [A.attempt(days[s:], 4, "intraday", 30)[0] for s, x in enumerate(ss) if x <= pd.Timestamp(last)]
        pnl = np.array([4 * x[1] for x in pt if y0 <= x[0].year <= y1])
        daily = pd.Series({x: 4 * sum(p for p, _, _ in d.get(x, [])) for x in ss})
        eq = daily.cumsum()
        rows.append({"data": label, "chart": f"{step}-minute", "trades": len(pnl), "winners %": 100 * (pnl > 0).mean(),
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "eval pass %": 100 * res.count("passed") / len(res),
                     "eval bust %": 100 * res.count("failed") / len(res)})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", 2011, 2018, "2018-11-30"), ("2019-2026", 2019, 2026, "2026-08-15"))
    nq_p = (("NQ 2015-2025", 2015, 2025, "2025-06-15"),)
    jobs = [(nsx, s, idx_p) for s in (5, 1)] + [(nq, s, nq_p) for s in (5, 1)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = [r for rs in pool.map(job, jobs) for r in rs]
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).sort_values(["data", "chart"]).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
