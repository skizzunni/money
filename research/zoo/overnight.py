# ruff: noqa: E501
"""Each day's overnight (18:00 the evening before to 09:29) high and low for research/zoo's sets, in the day's price
scale; written as d["on"] = (high, low) into zoo_days_on.pkl (2026-11-24, for the TJR-style sweep model).

    python research/zoo/overnight.py <data dir>
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


def sess_map(df: pd.DataFrame) -> dict:
    """Per session: Asia (18:00-02:59), London (03:00-08:29) and pre-market (08:30-09:29) high / low, in the session's
    scale (TJR's session draws on liquidity)."""
    t = df.index.tz_convert(H.NY)
    m = np.asarray(t.hour * 60 + t.minute)
    sess = np.asarray((t + pd.Timedelta(hours=6)).date)
    part = np.where(m >= 1080, "asia", np.where(m < 180, "asia", np.where(m < 510, "london", np.where(m < 570, "pre", ""))))
    keep = part != ""
    hi, lo = df.high.to_numpy(float)[keep], df.low.to_numpy(float)[keep]
    if "scale" in df.columns:
        sc = df.scale.to_numpy(float)[keep]
        last = pd.Series(sc, index=sess[keep]).groupby(level=0).last()
        f = last.reindex(sess[keep]).to_numpy() / sc
        hi, lo = hi * f, lo * f
    g = pd.DataFrame({"s": sess[keep], "p": part[keep], "h": hi, "l": lo}).groupby(["s", "p"]).agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    out: dict = {}
    for (d, p), r in g.iterrows():
        if r.n >= 3:
            out.setdefault(d, {})[p] = (r.h, r.l)
    return out


def on_map(df: pd.DataFrame) -> dict:
    t = df.index.tz_convert(H.NY)
    m = t.hour * 60 + t.minute
    sess = (t + pd.Timedelta(hours=6)).date  # the session a bar belongs to (it starts at 18:00 the evening before)
    on = df[(m >= 1080) | (m < 570)]
    s_on = np.asarray(sess)[(m >= 1080) | (m < 570)]
    hi, lo = on.high.to_numpy(float), on.low.to_numpy(float)
    if "scale" in on.columns:  # in the session's own scale: the 09:29 bar's
        sc = on.scale.to_numpy(float)
        last = pd.Series(sc, index=s_on).groupby(level=0).last()
        f = last.reindex(s_on).to_numpy() / sc
        hi, lo = hi * f, lo * f
    g = pd.DataFrame({"s": s_on, "h": hi, "l": lo}).groupby("s").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    return {d: (r.h, r.l) for d, r in g.iterrows() if r.n >= 60}


def build(ddir: str) -> None:
    import mnq_bars as M
    sets = H.load_sets(ddir)
    nq = pd.read_pickle(os.path.join(ddir, "nq1m_scaled.pkl"))
    es = pd.read_parquet(os.path.join(ddir, "es", "es_continuous_1m.parquet"))[["open", "high", "low", "close", "volume"]]
    es.index = es.index.tz_convert(H.NY)
    sep, dec = M.load(os.path.join(ddir, "MNQ_09-26.Last.txt")), M.load(os.path.join(ddir, "MNQ_12-26_nt_to_1117.Last.txt"))
    mnq, _ = M.traded_series(sep, dec)
    y = pd.read_pickle(os.path.join(ddir, "yahoo_mnq_5m.pkl"))
    nqm, esm, live = on_map(nq), on_map(es), on_map(mnq)
    for k, v in on_map(y.assign(volume=y.volume)).items():
        live.setdefault(k, v)
    maps = {"dev": nqm, "unseen_nq": nqm, "unseen_es": esm, "live": live}
    nqs, ess, lvs = sess_map(nq), sess_map(es), sess_map(mnq)
    for k, v in sess_map(y).items():
        lvs.setdefault(k, v)
    smaps = {"dev": nqs, "unseen_nq": nqs, "unseen_es": ess, "live": lvs}
    for name, (days, _) in sets.items():
        hit = 0
        for d in days:
            v = maps[name].get(d["d"])
            d["on"] = v if v is not None else (np.nan, np.nan)
            d["sess"] = smaps[name].get(d["d"], {})
            hit += v is not None
        print(name, "days with an overnight range", hit, "of", len(days))
    with open(os.path.join(ddir, "zoo_days_on.pkl"), "wb") as f:
        pickle.dump(sets, f)


if __name__ == "__main__":
    build(sys.argv[1])
