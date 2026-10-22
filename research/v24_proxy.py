"""A stand-in for the user's long TradingView view (MNQ1!, Jan 2025 - Oct 2026; docs/RESULTS.md, v2.4): raw-price RTH
bars, 5- and 30-minute, from NQ futures (1-minute, to 2025-07-23), the Nasdaq-100 index (HistData NSXUSD 1-minute, to
2026-06-30) and the user's MNQ bars (after), each later piece scaled to meet the earlier one at the splice.

    python research/v24_proxy.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>

<data dir> holds nq1m/NQ_1min_2024.parquet, nq1m/NQ_1min_2025.parquet (UTC timestamps) and
histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv (New York clock); writes proxy_5m.pkl and proxy_30m.pkl there.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.data import resample  # noqa: E402

NY = "America/New_York"
COLS = ["open", "high", "low", "close"]


def rth(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df.index >= pd.Timestamp("2024-10-01", tz=NY)]
    tm = df.index.hour * 60 + df.index.minute
    return df[(tm >= 570) & (tm < 960)]


def main() -> None:
    d, sep, dec = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    nq = pd.concat([pd.read_parquet(d / f"nq1m/NQ_1min_{y}.parquet") for y in (2024, 2025)])
    nq = nq.set_index(pd.to_datetime(nq.timestamp).dt.tz_localize("UTC").dt.tz_convert(NY)).drop(columns="timestamp")
    nq = rth(nq.astype(float))
    files = [f for f in glob.glob(str(d / "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv"))
             if any(y in f for y in ("2024", "2025", "2026"))]
    ix = pd.concat([load_histdata(f) for f in sorted(files)]).sort_index()
    ix = rth(ix[~ix.index.duplicated()]).assign(volume=0.0)
    series, _ = M.traded_series(M.load(sep), M.load(dec))
    one = K.rth(series)
    one = one.assign(volume=one.get("volume", 0.0))
    s1, s2 = pd.Timestamp("2025-07-24", tz=NY), pd.Timestamp("2026-07-01", tz=NY)
    for m in (5, 30):
        a, b, c = (resample(x, f"{m}min") for x in (nq, ix, one))
        first = a[a.index < s1]
        mid = b[(b.index >= s1) & (b.index < s2)].copy()
        mid[COLS] *= first.close.iloc[-1] / b[b.index < s1].close.iloc[-1]
        last = c[c.index >= s2].copy()
        last[COLS] *= mid.close.iloc[-1] / c[c.index < s2].close.iloc[-1]
        p = pd.concat([first, mid, last])[COLS + ["volume"]].fillna(0.0)
        p.to_pickle(d / f"proxy_{m}m.pkl")
        print(m, p.index[0], p.index[-1], len(p))


if __name__ == "__main__":
    main()
