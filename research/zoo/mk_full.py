"""Full 24-hour days for gold / crude (2026-11-24): per New York trading day (18:00 the evening before to 17:00),
1-minute bars rescaled month by month to today's level, as arrays of minutes from the day's 18:00 start (0-1379)."""
from __future__ import annotations

import os
import pickle
import sys

import pandas as pd

SRC = {"gold": ("hf_xau/ticks.parquet", 4500.0), "crude": ("hf_wti/ticks.parquet", 70.0)}


def build(ddir, f, target):
    df = pd.read_parquet(os.path.join(ddir, f))
    t = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York")
    df = df.set_index(t)[["open", "high", "low", "close"]].astype(float)
    m = df["close"].resample("MS").mean().reindex(df.index, method="ffill")
    s = (target / m).to_numpy()
    for k in df.columns:
        df[k] = df[k].to_numpy() * s
    shifted = df.index + pd.Timedelta(hours=6)  # 18:00 -> 00:00 of the trading day
    df["mm"] = (shifted.hour * 60 + shifted.minute).to_numpy()
    df["day"] = shifted.date
    days = []
    for d, g in df.groupby("day"):
        if len(g) < 900 or pd.Timestamp(d).dayofweek >= 5:
            continue
        days.append({"d": d, "mm": g["mm"].to_numpy(), "o": g["open"].to_numpy(), "h": g["high"].to_numpy(),
                     "l": g["low"].to_numpy(), "c": g["close"].to_numpy()})
    return days


if __name__ == "__main__":
    out = {k: build(sys.argv[1], f, tg) for k, (f, tg) in SRC.items()}
    for k, v in out.items():
        print(k, len(v), v[0]["d"], v[-1]["d"])
    with open(os.path.join(sys.argv[1], "markets_full.pkl"), "wb") as fh:
        pickle.dump(out, fh)
