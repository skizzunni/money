"""Other markets for the band (2026-11-24, the user: "if the market is chopped that day we look at another market"):
spot gold (XAUUSD, for MGC / GC) and WTI crude (WTIUSD, for MCL / CL), 1-minute bars from histdata (Hugging Face
elthariel/histdata_fx_1m; UTC; no volume). Each market's main session (`start`, New York, 390 minutes) is shifted onto
the 09:30-16:00 clock harness.rth5 and the strategies use, so a day's bar k is `start` + 5k minutes. Prices are rescaled
month by month to `target` (today's level), as the NQ history was, a day's prices on one scale (`s`).

    python research/zoo/markets.py <data dir>     # caches markets.pkl
"""
from __future__ import annotations

import os
import pickle
import sys

import harness as H
import numpy as np
import pandas as pd

MARKETS = {  # name: (file, session start minutes New York, target price, tick, $ a point)
    "gold": ("hf_xau/ticks.parquet", 510, 4500.0, 0.1, 10.0),
    "gold930": ("hf_xau/ticks.parquet", 570, 4500.0, 0.1, 10.0),
    "crude": ("hf_wti/ticks.parquet", 540, 70.0, 0.01, 100.0),
    "crude930": ("hf_wti/ticks.parquet", 570, 70.0, 0.01, 100.0),
    "euro": ("hf_eur/ticks.parquet", 510, 1.10, 0.0001, 12500.0),  # M6E: 12,500 euros, $1.25 a tick
}


def build_market(ddir: str, f: str, start: int, target: float) -> list:
    df = pd.read_parquet(os.path.join(ddir, f))
    df = df.set_index(pd.to_datetime(df["ts"], utc=True))[["open", "high", "low", "close", "volume"]].astype(float)
    m = df["close"].resample("MS").mean().reindex(df.index, method="ffill")
    s = (target / m).to_numpy()
    for k in ("open", "high", "low", "close"):
        df[k] = df[k].to_numpy() * s
    df["scale"] = s
    df.index = df.index + pd.Timedelta(minutes=570 - start)  # the session's open on the 09:30 clock
    return H.rth5(df)


if __name__ == "__main__":
    ddir = sys.argv[1]
    out = {}
    for name, (f, start, target, _tick, _pv) in MARKETS.items():
        days = build_market(ddir, f, start, target)
        rng = np.median([(d["h"].max() - d["l"].min()) for d in days[-250:]])
        print(name, len(days), days[0]["d"], days[-1]["d"], f"median range last year {rng:.2f}")
        out[name] = days
    with open(os.path.join(ddir, "markets.pkl"), "wb") as fh:
        pickle.dump(out, fh)
