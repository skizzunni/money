"""O4, pre-registered in docs/CANDIDATE_O4.md: a 486-setting grid around the ONYX Trend Follow replica (`trendpb` in
research/patterns.py), regular hours, chosen on NQ 2015-2019 and tested once on the held-out sets.

    python research/o4_trendpb.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out prefix>
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patterns as P  # noqa: E402

DEV = "NQ 15-19 (dev)"
HOLD = ["NQ 20-25", "index 11-26", "stand-in 25-26"]
BASE = {"L": 24, "K": 3.0, "S": 7, "last": 720, "R": 3.0, "trend": False}


def sigs(day: P.Day, L: int, K: float, S: int, last: int) -> list:
    h, l, c, n = day.h, day.l, day.c, day.n
    x = np.arange(L) - (L - 1) / 2
    out = []
    for i in range(max(L + 1, S), n - 1):
        if day.mins[i] + 5 > last:
            break
        a = day.atr[i]
        if not a > 0:
            continue
        slope = float(np.dot(x, c[i - L:i] - c[i - L:i].mean()) / np.dot(x, x))
        for d in (1, -1):
            if d * slope * L < K * a:
                continue
            pulled = (l[i - 1] < l[i - 2]) if d > 0 else (h[i - 1] > h[i - 2])
            if pulled and d * (c[i] - (h[i - 1] if d > 0 else l[i - 1])) > 0:
                ext = l[i - S + 1:i + 1].min() if d > 0 else h[i - S + 1:i + 1].max()
                out.append((i, d, ext - d * P.TICK, None, "R"))
    return out


def days_for(bars: pd.DataFrame) -> list:
    base = P.prepare(bars, "orb")  # the sessions; their own signals are replaced below
    return [(dy, tt, did) for dy, tt, did, _ in base]


def job(args: tuple) -> list[dict]:
    names, (L, K, S) = args
    rows = []
    prepared = {}
    for name in names:
        bars, first = P.D[name]
        prepared[name] = (days_for(bars), first)
    for last, R, trend in itertools.product((660, 720, 810), (2.0, 3.0, 4.0), (False, True)):
        row = {"L": L, "K": K, "S": S, "last": last, "R": R, "trend": trend}
        for name, (days, first) in prepared.items():
            ds = [(dy, tt, did, sigs(dy, L, K, S, last)) for dy, tt, did in days]
            for k, v in P.stats(P.execute(ds, trend, False, False, R, False), first).items():
                row[f"{name} {k}"] = v
        rows.append(row)
    return rows


def main() -> None:
    data, sep, dec, prefix = sys.argv[1:5]
    P.init(data, sep, dec)
    combos = list(itertools.product((12, 24, 36), (2.0, 3.0, 4.0), (3, 7, 12)))
    with ProcessPoolExecutor(4, initializer=P.init, initargs=(data, sep, dec)) as ex:
        dev = pd.DataFrame([r for rs in ex.map(job, [([DEV], c) for c in combos]) for r in rs])
    dev.to_csv(f"{prefix}_dev.csv", index=False)
    ok = dev[dev[f"{DEV} n/yr"] >= 50].sort_values(f"{DEV} pf", ascending=False)
    pick = ok.iloc[0][["L", "K", "S", "last", "R", "trend"]].to_dict()
    pick = {"L": int(pick["L"]), "K": float(pick["K"]), "S": int(pick["S"]), "last": int(pick["last"]),
            "R": float(pick["R"]), "trend": bool(pick["trend"])}
    print("development: settings", len(dev), "with >= 50 trades a year", len(ok), flush=True)
    print(ok.head(10)[["L", "K", "S", "last", "R", "trend", f"{DEV} n/yr", f"{DEV} win%", f"{DEV} pf",
                       f"{DEV} R"]].to_string(index=False), flush=True)
    print("SELECTED", pick, flush=True)
    rows = []
    for tag, p in (("base", BASE), ("selected", pick)):
        r = [x for x in job(([DEV] + HOLD, (p["L"], p["K"], p["S"])))
             if x["last"] == p["last"] and x["R"] == p["R"] and x["trend"] == p["trend"]][0]
        rows.append({"which": tag, **r})
    hold = pd.DataFrame(rows)
    hold.to_csv(f"{prefix}_holdout.csv", index=False)
    print(hold.T.to_string(), flush=True)


if __name__ == "__main__":
    main()
