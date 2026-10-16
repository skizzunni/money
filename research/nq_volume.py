"""Round thirty-two: volume at the signal, from real NQ futures 1-minute bars (2015 - July 2025).

    Data: huggingface.co/datasets/mdelcristo/NQ-F_1min_OHLCV_Parquet (MIT licence), NQ_1min_<year>.parquet,
    timestamps in UTC, unadjusted front-contract prices, volume per minute.
    python research/nq_volume.py path/to/parquet_dir

Fixed before running. The bot runs on these bars (5-minute, prices rescaled to today's level month by month
as in timeframes.py, the 1.5-noise-unit take-profit, $116.67 max loss live from the fill, 1 contract). At each
trade's signal (the half-hour check that triggered it), four facts, each against the same window at the same
time of day over the previous 20 sessions (a session runs 18:00 to 17:00 New York time):
  1 busy half hour:  volume in the 30 minutes before the signal above that average
  2 volume surge:    volume in the 5 minutes before the signal above that average
  3 busy day so far: volume from 09:30 to the signal above that average
  4 busy overnight:  volume from 18:00 to 09:30 above that average
Quarterly roll weeks (10 days before to 3 after expiry) are left out of the tests.
Discovery 2015-2019: Welch t-test of $ per trade, yes against no; Benjamini-Hochberg 5% over the four.
Confirmation 2020-2022: same sign, one-sided p < 5%. Final test 2023 - July 2025, run once, for a filter that
skips the losing side of every confirmed fact: higher win rate, more $ per day per dollar of worst losing
stretch, and at least 90% of the bot's $ per day.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import timeframes as TF  # noqa: E402
import volume_days as V  # noqa: E402

from mnqbot.data import NY  # noqa: E402

FACTS = ["busy half hour", "volume surge", "busy day so far", "busy overnight"]
SESSION_START = 18 * 60  # 18:00 New York
RTH_OPEN = 570
PERIODS = (("2015-2019", 2015, 2019), ("2020-2022", 2020, 2022))


def load(folder: str) -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(Path(folder).glob("NQ_1min_*.parquet"))]
    df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
    df.index = pd.DatetimeIndex(df.pop("timestamp")).tz_localize("UTC").tz_convert(NY)
    return df.astype(float)


def volume_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Session date x minutes since 18:00, volume per minute (0 where no trade)."""
    t = df.index
    mins = t.hour * 60 + t.minute
    session = (t + pd.Timedelta(hours=6)).tz_localize(None).normalize()
    pos = (mins - SESSION_START) % 1440
    grid = pd.DataFrame({"s": session, "p": pos, "v": df.volume.to_numpy()}).pivot_table(
        index="s", columns="p", values="v", aggfunc="sum", fill_value=0.0)
    return grid.reindex(columns=range(1440), fill_value=0.0)


def facts(grid: pd.DataFrame, cum: np.ndarray, day: pd.Timestamp, signal_min: int) -> dict | None:
    """cum: grid's volume summed along each session (computed once)."""
    if day not in grid.index:
        return None
    k = grid.index.get_loc(day)
    if k < 20:
        return None
    e = (signal_min - SESSION_START) % 1440
    o = (RTH_OPEN - SESSION_START) % 1440
    windows = {"busy half hour": (e - 30, e), "volume surge": (e - 5, e), "busy day so far": (o, e),
               "busy overnight": (0, o)}

    def window_sum(rows, a, b):
        return cum[rows, b - 1] - (cum[rows, a - 1] if a > 0 else 0.0)

    out = {}
    past = np.arange(k - 20, k)
    for name, (a, b) in windows.items():
        now = window_sum(np.array([k]), a, b)[0]
        base = window_sum(past, a, b).mean()
        out[name] = bool(now > base) if base > 0 else None
    return out if None not in out.values() else None


def welch(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def main() -> None:
    raw = load(sys.argv[1])
    rth = raw[(raw.index.hour * 60 + raw.index.minute >= RTH_OPEN) & (raw.index.hour < 16)]
    by_min = rth.volume.groupby(rth.index.hour * 60 + rth.index.minute).mean()
    print(f"{len(raw):,} one-minute bars, {raw.index[0]} to {raw.index[-1]}; average volume 09:25-09:29 "
          f"{raw.volume[(raw.index.hour == 9) & (raw.index.minute.isin(range(25, 30)))].mean():.0f}, "
          f"09:30-09:34 {by_min.loc[570:574].mean():.0f} (the open should jump)")
    grid = volume_grid(raw)
    scaled = TF.scaled(raw[["open", "high", "low", "close", "volume"]])
    bars = scaled.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == RTH_OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2015-03-01") & ~sessions.isin(list(first_sessions))]
    tf = MT.clean(P.simulate(bars, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True), first_sessions)
    tf = tf[tf.entry_time.dt.tz_localize(None) >= sessions[0]].reset_index(drop=True)
    tf["day"] = tf.entry_time.dt.tz_localize(None).dt.normalize()
    rows = []
    cum = grid.to_numpy().cumsum(axis=1)
    for t in tf.itertuples():
        f = None if V.roll_window(t.day) else facts(grid, cum, t.day, t.entry_time.hour * 60 + t.entry_time.minute)
        rows.append(f or dict.fromkeys(FACTS))
    tf = pd.concat([tf, pd.DataFrame(rows, index=tf.index)], axis=1)
    year = tf.entry_time.dt.year
    s_all = MT.stats(tf, sessions)
    print(f"the bot on NQ futures 2015-2025: {len(tf)} trades, win {s_all['win %']:.1f}%, $/day {s_all['$/day']:.2f}, "
          f"t {s_all['t']:.2f}; trades with volume facts {tf[FACTS[0]].notna().sum()}")
    tested = tf.dropna(subset=FACTS)
    ty = tested.entry_time.dt.year
    parts = {label: tested[(ty >= y0) & (ty <= y1)] for label, y0, y1 in PERIODS}
    out = []
    for f in FACTS:
        r = [f]
        for part in parts.values():
            yes, no = part[part[f].astype(bool)].pnl.to_numpy(), part[~part[f].astype(bool)].pnl.to_numpy()
            r += [len(yes), len(no), yes.mean(), no.mean(), welch(yes, no)]
        out.append(r)
    df = pd.DataFrame(out, columns=["fact", "n yes 15-19", "n no 15-19", "yes $ 15-19", "no $ 15-19", "t 15-19",
                                    "n yes 20-22", "n no 20-22", "yes $ 20-22", "no $ 20-22", "t 20-22"])
    df["p 15-19"] = D.two_sided_p(df["t 15-19"].to_numpy())
    df["luck filter"] = D.bh(df["p 15-19"], 0.05)
    df["confirmed"] = df["luck filter"] & (np.sign(df["t 15-19"]) == np.sign(df["t 20-22"])) & (
        df["t 20-22"].abs() >= 1.645)
    print(df.round(2).to_string(index=False))
    confirmed = df[df.confirmed]
    if confirmed.empty:
        print("No fact passed the luck filter and confirmation: nothing goes to the final test.")
        return
    keep = pd.Series(True, index=tf.index)
    for _, r in confirmed.iterrows():
        has = tf[r.fact].notna()
        keep &= ~has | (tf[r.fact] == (r["t 15-19"] > 0))
    ss = sessions[sessions.year >= 2023]
    a, b = MT.stats(tf[keep & (year >= 2023)], ss), MT.stats(tf[year >= 2023], ss)
    for name, s in (("bot", b), ("filtered", a)):
        print(f"  2023-25 {name:9s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}  trades/day {s['trades/day']:.2f}")
    ok = (a["win %"] > b["win %"] and a["$/day"] / a["worst stretch"] > b["$/day"] / b["worst stretch"]
          and a["$/day"] >= 0.9 * b["$/day"])
    print(f"FINAL TEST 2023 - July 2025: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
