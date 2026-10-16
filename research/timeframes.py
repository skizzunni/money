"""Round twelve: does the chart's bar length change the bot? 5 vs 15 vs 30-minute bars, same rules.

    python research/timeframes.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

The rules are the same on any bar length that divides 30 minutes, except for one thing: the max-loss
stop needs the entry fill, so it starts on the bar after the fill. On a 5-minute chart that is 5 minutes
after the entry; on a 30-minute chart it is 30 minutes, and the first half hour of every trade has only
the line stop. To test the $350 cap at today's distance in points, each calendar month's prices are
multiplied by (30,661 / that month's first close). The noise area is built from ratios, so only the first
session of each month sees a fake gap; trades entered on it, or held across a month end, are dropped from
every run. 3 MNQ, $1.24 fees + 1 tick each way per contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nsx_study import load_histdata  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

REF = 30661.0
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026), ("2026", 2026, 2026),
           ("all", 2011, 2026))


def scaled(raw: pd.DataFrame) -> pd.DataFrame:
    month = raw.index.tz_localize(None).to_period("M")
    f = (REF / raw.close.groupby(month).transform("first")).to_numpy()
    out = raw.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = ((raw[col].to_numpy() * f) / 0.25).round() * 0.25
    return out


def trades(raw: pd.DataFrame, minutes: int, cap: float, qty: int = 3) -> pd.DataFrame:
    b = raw if minutes == 1 else raw.resample(f"{minutes}min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    days = pd.Series(b.index.tz_localize(None).normalize()).drop_duplicates()
    first_sessions = set(days.groupby(days.dt.to_period("M")).min())
    tf = run(b, NoiseConfig(qty=qty, max_loss_per_trade=cap), minutes=minutes).trades_frame()
    entry_day = tf.entry_time.dt.tz_localize(None).dt.normalize()
    month_in = tf.entry_time.dt.tz_localize(None).dt.to_period("M")
    same_month = month_in == tf.exit_time.dt.tz_localize(None).dt.to_period("M")
    return tf[~entry_day.isin(first_sessions) & same_month & (entry_day >= "2011-01-01")]


def main() -> None:
    raw = load_histdata(sys.argv[1])
    raw = scaled(raw[raw.index >= pd.Timestamp("2010-11-01", tz=raw.index.tz)])
    rows = []
    for minutes in (5, 15, 30):
        for cap in (0.0, 350.0):
            tf = trades(raw, minutes, cap)
            year = tf.entry_time.dt.year
            for label, y0, y1 in PERIODS:
                t = tf[(year >= y0) & (year <= y1)]
                eq = t.pnl.cumsum()
                rows.append((label, minutes, int(cap), len(t), t.pnl.sum(), (eq.cummax() - eq).max(), t.pnl.min(),
                             int((t.pnl < -400).sum())))
    df = pd.DataFrame(rows, columns=["period", "bar min", "cap $", "trades", "net $", "worst stretch $",
                                     "worst trade $", "trades lost > $400"])
    print(df.sort_values(["period", "cap $", "bar min"]).round(0).to_string(index=False))


if __name__ == "__main__":
    main()
