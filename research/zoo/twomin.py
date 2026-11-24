# ruff: noqa: E501
"""2-minute day sets for research/zoo (2026-11-24, the user's MambaFx video "The ONLY 2 Minute Trading Strategy").

    python research/zoo/twomin.py <data dir>     # writes zoo_days2.pkl next to zoo_days.pkl
"""
from __future__ import annotations

import os
import pickle
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import harness as H  # noqa: E402

NY = H.NY


def rth2(df: pd.DataFrame) -> list[dict]:
    t = df.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    df = df[(m >= 570) & (m < 960)]
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if "scale" in df.columns:
        agg["scale"] = "last"
    b = df.resample("2min", label="left", closed="left", origin="start_day").agg(agg).dropna(subset=["open"])
    out = []
    tt = b.index.tz_convert(NY)
    for d, g in b.groupby(tt.date):
        if len(g) < 190:  # 195 two-minute bars in a session
            continue
        gt = g.index.tz_convert(NY)
        rec = {"d": d, "mm": (gt.hour * 60 + gt.minute).to_numpy()}
        for k in ("open", "high", "low", "close", "volume"):
            rec[k[0] if k != "low" else "l"] = g[k].to_numpy(float)
        rec["s"] = float(g["scale"].iloc[-1]) if "scale" in g.columns else 1.0
        out.append(rec)
    return out


def build(ddir: str) -> None:
    import mnq_bars as M
    nq = pd.read_pickle(os.path.join(ddir, "nq1m_scaled.pkl"))
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)]
    nd = rth2(nq)
    es = pd.read_parquet(os.path.join(ddir, "es", "es_continuous_1m.parquet"))[["open", "high", "low", "close", "volume"]]
    es.index = es.index.tz_convert(NY)
    sep, dec = M.load(os.path.join(ddir, "MNQ_09-26.Last.txt")), M.load(os.path.join(ddir, "MNQ_12-26_nt_to_1117.Last.txt"))
    mnq, _ = M.traded_series(sep, dec)
    live = rth2(mnq)
    have = {r["d"] for r in live}
    y = pd.read_pickle(os.path.join(ddir, "yahoo_mnq_2m.pkl"))
    live = sorted(live + [r for r in H.despike(rth2(y)) if r["d"] not in have and r["d"] >= live[0]["d"]], key=lambda r: r["d"])
    sets = {"dev": ([r for r in nd if r["d"].year <= 2019], "MNQ"), "unseen_nq": ([r for r in nd if r["d"].year >= 2020], "MNQ"),
            "unseen_es": (rth2(es), "MES"), "live": (live, "MNQ")}
    for k, (v, _) in sets.items():
        print(k, len(v), v[0]["d"], v[-1]["d"])
    with open(os.path.join(ddir, "zoo_days2.pkl"), "wb") as f:
        pickle.dump(sets, f)


if __name__ == "__main__":
    build(sys.argv[1])
