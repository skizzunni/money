"""docs/V2_STOPS.md, Phase 4b: noise-only v2 against noise + Williams on one account, NQ 2015-2025 (5-minute).

Noise: the v2 defaults at 2 MNQ (research/v2_stops_eval.py's data, closures and costs). Williams:
research/combo_live.py's
breakout (levels at the open +/- half of yesterday's range, first side only, stop a quarter of the range, $200 of risk
a trade at 1-10 MNQ, out at the close), on the same 5-minute bars, with the plan's 2 ticks a side (one more than
combo_live's). Shared: one position at a time (the first entry owns the account until flat) and one daily loss
limit: no new trade once the day's closed P/L is at or below -$400. $ a day, max end-of-day drawdown, profit /
drawdown, profit factor.

    python research/v2_combo.py <data dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import combo_live as W  # noqa: E402
import v2_stops_eval as V  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

LIMIT = -400.0


def legs_noise(b):
    cfg = NoiseConfig(**{**V.BASE, **V.GATES["v2, limit -400, buffer 0.24, gap guard on"]})
    return [(t.entry_bar, t.exit_bar, t.direction, t.entry, t.exit, t.pnl, t.qty, "noise") for t in run(b, cfg,
        5).trades]


def legs_williams(b):
    skip = [x for x in V.BASE["skip_dates"].split(",") if x]
    out = []
    for a, x, d, en, ex, pnl, q in W.williams_legs(b, month_skip=True, skip_dates=skip):
        out.append((a, x, d, en, ex, pnl - q * 2 * 0.25 * 2.0, q, "williams"))  # one more tick a side
    return out


def account(b, legs):
    """One position at a time, and the shared daily loss limit (no new leg once today's closed P/L <= LIMIT)."""
    day = np.asarray(b.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    taken, busy, cur, closed_today, pend = [], -1, None, 0.0, []
    for leg in sorted(legs, key=lambda x: (x[0], x[1])):
        a = leg[0]
        if day[a] != cur:
            cur, closed_today = day[a], 0.0
        closed_today += sum(p[5] for p in pend if p[1] < a and day[p[1]] == cur)  # legs closed before this start
        pend = [p for p in pend if not (p[1] < a)]
        if a > busy and closed_today > LIMIT:
            taken.append(leg)
            pend.append(leg)
            busy = leg[1]
    return taken


def stats(b, legs, name):
    t = b.index.tz_convert(V.NY)
    day = np.asarray(t.strftime("%Y-%m-%d"))
    m = t.hour * 60 + t.minute
    sessions = sorted(set(day[(m >= 570) & (m <= 960)]))
    p = np.array([x[5] for x in legs])
    by = pd.Series(0.0, index=sessions).add(pd.Series(p, index=[day[x[1]] for x in legs]).groupby(level=0).sum(),
                                            fill_value=0)
    eq = by.cumsum().to_numpy()
    mdd = float((np.maximum.accumulate(np.r_[0.0, eq])[1:] - eq).max())
    kinds = pd.Series([x[7] for x in legs]).value_counts().to_dict()
    return {"set": name, "trades": len(p), **{f"n_{k}": v for k, v in kinds.items()}, "per_day": by.mean(),
            "max_dd": mdd, "profit_dd": by.sum() / mdd, "pf": p[p > 0].sum() / -p[p < 0].sum(),
            "worst_day": by.min(), "win_rate": (p > 0).mean()}


def main() -> None:
    b = V.load(sys.argv[1])
    n, w = legs_noise(b), legs_williams(b)
    rows = [stats(b, account(b, n), "noise-only v2 (2 MNQ)"), stats(b, account(b, w), "Williams only"),
            stats(b, account(b, n + w), "noise v2 + Williams, one account")]
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
