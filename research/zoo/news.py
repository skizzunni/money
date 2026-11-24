# ruff: noqa: E501
"""News days for research/zoo (2026-11-24, the user: "it's all about signals and news"). A day's news flag is read from
the market itself, not a calendar: the 08:30-08:34 New York volume against 08:20-08:29 (the 08:30 releases - jobs, CPI,
PPI, retail sales, claims - spike it; first Fridays median 8x, Mondays 1.2x). Also the pre-open move: the 08:29 close
(the last price before the news) to the 09:29 close (the last before the cash open).

    python research/zoo/news.py <data dir>     # writes zoo_days_news.pkl: zoo_days.pkl's sets with d["news"] = (spike, pre, move)
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import harness as H  # noqa: E402


def news_map(df: pd.DataFrame, minutes: int) -> dict:
    t = df.index.tz_convert(H.NY)
    m = t.hour * 60 + t.minute
    out = {}
    pre_v = df[(m >= 500) & (m < 510)].groupby(t[(m >= 500) & (m < 510)].date).volume.mean()
    at_v = df[(m >= 510) & (m < 515)].groupby(t[(m >= 510) & (m < 515)].date).volume.mean()
    last_pre = df[(m >= 510 - minutes) & (m < 510)].groupby(t[(m >= 510 - minutes) & (m < 510)].date).close.last()
    last_open = df[(m >= 570 - minutes) & (m < 570)].groupby(t[(m >= 570 - minutes) & (m < 570)].date).close.last()
    for d in at_v.index:
        if d in pre_v.index and d in last_pre.index and d in last_open.index and pre_v[d] > 0:
            out[d] = (float(at_v[d] / pre_v[d]), float(last_pre[d]), float(last_open[d] - last_pre[d]))
    return out


def build(ddir: str) -> None:
    import mnq_bars as M
    sets = H.load_sets(ddir)
    nq = pd.read_pickle(os.path.join(ddir, "nq1m_scaled.pkl"))
    es = pd.read_parquet(os.path.join(ddir, "es", "es_continuous_1m.parquet"))[["open", "high", "low", "close", "volume"]]
    es.index = es.index.tz_convert(H.NY)
    sep, dec = M.load(os.path.join(ddir, "MNQ_09-26.Last.txt")), M.load(os.path.join(ddir, "MNQ_12-26_nt_to_1117.Last.txt"))
    mnq, _ = M.traded_series(sep, dec)
    y = pd.read_pickle(os.path.join(ddir, "yahoo_mnq_5m.pkl"))
    maps = {"dev": news_map(nq, 1), "unseen_nq": news_map(nq, 1), "unseen_es": news_map(es, 1)}
    live = news_map(mnq, 1)
    for k, v in news_map(y, 5).items():
        live.setdefault(k, v)
    maps["live"] = live
    for name, (days, _) in sets.items():
        hit = 0
        for d in days:
            v = maps[name].get(d["d"])
            d["news"] = v if v is not None else (np.nan, np.nan, np.nan)
            hit += v is not None
        print(name, "days with pre-open data", hit, "of", len(days))
    with open(os.path.join(ddir, "zoo_days_news.pkl"), "wb") as f:
        pickle.dump(sets, f)


if __name__ == "__main__":
    build(sys.argv[1])
