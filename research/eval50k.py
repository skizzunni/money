"""Round thirteen: the $50K evaluation, at 1 to 10 MNQ, with the $350 max loss per trade.

    python research/eval50k.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Take Profit Trader's $50K Test as reviews describe it (check the firm's site): $3,000 target, $2,000
end-of-day trailing drawdown (only the closing balance counts), best day under 50% of the profit, at least
5 trading days, up to 60 MNQ. The bot on a 5-minute chart, prices rescaled to today's level month by month
as in timeframes.py. P&L is linear in contracts once the max loss is fixed per contract, so each run is
1 contract with the cap divided by the contracts: $350 on 10 MNQ is a $35 stop per contract.
Every start day from 2011 is an attempt; it passes, fails, or is still open after the horizon.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import timeframes as TF  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.config import PropRules  # noqa: E402
from mnqbot.report import run_eval  # noqa: E402

PROP = PropRules(start_balance=50_000, profit_target=3_000, max_drawdown=2_000)
QTYS = (1, 2, 3, 5, 6, 10)
HORIZONS = (60, 125, 250)


def daily(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    day = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum()
    out = pd.DataFrame(index=sessions)
    out["pnl"] = day.reindex(sessions).fillna(0.0)
    out["traded"] = out.index.isin(day.index)
    return out


def odds(d: pd.DataFrame, qty: int, horizon: int) -> tuple[float, float, float, float]:
    pnl = d.pnl.to_numpy() * qty
    # end-of-day drawdown: only the closing balance is checked, so the day's worst point is its close
    recs = [(p, min(p, 0.0), t) for p, t in zip(pnl, d.traded, strict=True)]
    res = [run_eval(recs[s : s + horizon], PROP) for s in range(len(recs) - horizon)]
    out = [r[0] for r in res]
    used = [r[1] for r in res if r[0] == "passed"]
    n = len(out)
    return out.count("passed") / n, out.count("failed") / n, out.count("timeout") / n, \
        float(np.median(used)) if used else float("nan")


def main() -> None:
    raw = load_histdata(sys.argv[1])
    raw = TF.scaled(raw[raw.index >= pd.Timestamp("2010-11-01", tz=raw.index.tz)])
    idx = raw.index.tz_localize(None)
    rth = (idx.hour * 60 + idx.minute == 570)
    sessions = pd.DatetimeIndex(sorted(set(idx[rth].normalize())))
    sessions = sessions[sessions >= "2011-01-01"]
    rows = []
    for label, caps in (("no max loss", {q: 0.0 for q in QTYS}), ("$350 per trade", {q: 350.0 / q for q in QTYS}),
                        ("$117 per contract", {q: 350.0 / 3 for q in QTYS})):
        cache: dict[float, pd.DataFrame] = {}
        for q in QTYS:
            cap = caps[q]
            if cap not in cache:
                cache[cap] = daily(TF.trades(raw, 5, cap, qty=1), sessions)
            d = cache[cap]
            for period, y0, y1 in (("2011-2022", 2011, 2022), ("2023-2026", 2023, 2026)):
                dd = d[(d.index.year >= y0) & (d.index.year <= y1)]
                for h in HORIZONS:
                    p, f, o, med = odds(dd, q, h)
                    rows.append((label, q, period, h, 100 * p, 100 * f, 100 * o, med, dd.pnl.mean() * q))
            print(label, q, "done", flush=True)
    df = pd.DataFrame(rows, columns=["max loss", "MNQ", "period", "sessions", "pass %", "fail %", "open %",
                                     "median sessions to pass", "$ per day"])
    print(df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
