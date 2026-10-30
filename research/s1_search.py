"""Search S1, pre-registered in docs/SEARCH_S1.md: 1,260 one-trade-a-day rules (12 entry families x 3 trend filters x
35 target/stop exits), at 1 MNQ.

Settings are picked on development (index 2011-2022, NQ 2015-2022). The 5 finalists are then tested once on 2023 -
mid-2025 and on the user's window.

    python research/s1_search.py <data dir> <out prefix>
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h1_dip as H  # noqa: E402

TICK, PV, FEE, LEVEL = H.TICK, H.PV, H.FEE, H.LEVEL
CHECKS = np.arange(5, 66, 6)  # bars closing at 10:00, 10:30, ..., 15:00
FAMILIES = ["MOM 0.5", "MOM 1.0", "MOM 1.5", "REV 0.5", "REV 1.0", "REV 1.5", "ORB", "ORB-R", "GAP", "GAP-R", "PREV",
            "PREV-R"]
FILTERS = ["none", "with-trend", "counter-trend"]
TARGETS = [0.05, 0.1, 0.2, 0.35, 0.5, 1.0, None]
STOPS = [0.1, 0.25, 0.5, 1.0, None]
DEV = [("index", "2011-01-01", "2022-12-31"), ("nq", "2015-01-01", "2022-12-31")]
TEST = [("index", "2023-01-01", "2024-12-31"), ("nq", "2023-01-01", "2025-07-31")]
USER = [("proxy", "2025-01-02", "2026-12-31")]


def arrays(sess: list, scaled: bool) -> dict:
    keep = [s for s in sess if len(s[2]) == 78 and s[2][0] == 570]
    day = np.array([s[0] for s in keep])
    o, h, lo, c = (np.vstack([s[k] for s in keep]) for k in (3, 4, 5, 6))
    pc = np.array([s[1] for s in keep], float)
    f = LEVEL / o[:, 0] if scaled else np.ones(len(keep))
    rng = pd.Series(h.max(1) - lo.min(1)).rolling(14).mean().shift(1).to_numpy()
    m = c / o[:, :1] - 1
    sig = pd.DataFrame(np.abs(m)).rolling(14).mean().shift(1).to_numpy()
    dclose = pd.Series(c[:, -1])
    sma = dclose.rolling(50).mean()
    trend = np.sign((dclose - sma).shift(1).to_numpy())
    gapday = np.r_[99, np.diff(pd.to_datetime(day).values).astype("timedelta64[D]").astype(int)]
    prev_ret = np.r_[0.0, c[:-1, -1] / o[:-1, 0] - 1]
    prev_ret[gapday > 4] = 0.0
    orh, orl = h[:, :6].max(1), lo[:, :6].min(1)
    return {"day": day, "o": o, "h": h, "lo": lo, "c": c, "pc": pc, "f": f, "rng": rng, "m": m, "sig": sig,
            "trend": np.nan_to_num(trend), "gap": np.sign(o[:, 0] - pc), "prev": np.sign(prev_ret), "orh": orh,
            "orl": orl}


def signals(a: dict, fam: str, filt: str) -> np.ndarray:
    n = len(a["day"])
    d = np.zeros((n, len(CHECKS)))
    if fam.startswith(("MOM", "REV")):
        k = float(fam.split()[1])
        v = a["m"][:, CHECKS] / a["sig"][:, CHECKS]
        d = np.where(np.abs(v) >= k, np.sign(a["m"][:, CHECKS]), 0.0)
        if fam.startswith("REV"):
            d = -d
    elif fam.startswith("ORB"):
        cc = a["c"][:, CHECKS]
        d = np.where(cc > a["orh"][:, None], 1.0, np.where(cc < a["orl"][:, None], -1.0, 0.0))
        if fam == "ORB-R":
            d = -d
    else:
        x = a["gap"] if fam.startswith("GAP") else a["prev"]
        d[:, 0] = -x if fam.endswith("-R") else x
    d = np.nan_to_num(d)
    if filt == "with-trend":
        d = np.where(d == a["trend"][:, None], d, 0.0)
    elif filt == "counter-trend":
        d = np.where(d == -a["trend"][:, None], d, 0.0)
    ok = np.isfinite(a["rng"]) & np.isfinite(a["sig"][:, CHECKS]).all(1)
    d[~ok] = 0.0
    return d


def trades(a: dict, d: np.ndarray, rows: np.ndarray) -> dict | None:
    """The forward paths of the first signal of each day in `rows`."""
    sub = d[rows]
    has = (sub != 0).any(1)
    if not has.any():
        return None
    r = rows[has]
    first = (sub[has] != 0).argmax(1)
    dirn = sub[has][np.arange(len(r)), first]
    e = CHECKS[first] + 1
    cols = e[:, None] + np.arange(72)[None, :]
    valid = cols <= 77
    cols = np.minimum(cols, 77)
    f = a["f"][r][:, None]
    o, h, lo = a["o"][r[:, None], cols] * f, a["h"][r[:, None], cols] * f, a["lo"][r[:, None], cols] * f
    dd = dirn[:, None]
    entry = o[:, :1] + dd * TICK
    fav = np.where(dd > 0, h - entry, entry - lo)
    adv = np.where(dd > 0, entry - lo, h - entry)
    open_adv = np.where(dd > 0, entry - o, o - entry)
    fav[~valid], adv[~valid] = -np.inf, -np.inf
    last = valid.sum(1) - 1
    close = a["c"][r, 77] * f[:, 0] - dirn * TICK
    return {"rows": r, "d": dirn, "entry": entry[:, 0], "fav": fav, "adv": adv, "open_adv": open_adv, "last": last,
            "close": close, "R": a["rng"][r] * f[:, 0], "cumadv": np.maximum.accumulate(adv, 1)}


def exits(t: dict, tgt: float | None, stp: float | None) -> tuple[np.ndarray, np.ndarray]:
    n = len(t["d"])
    big = 10 ** 6
    idx = np.arange(n)
    if tgt is not None:
        hit = t["fav"] >= (tgt * t["R"])[:, None]
        th = np.where(hit.any(1), hit.argmax(1), big)
    else:
        th = np.full(n, big)
    if stp is not None:
        hit = t["adv"] >= (stp * t["R"])[:, None]
        sh = np.where(hit.any(1), hit.argmax(1), big)
    else:
        sh = np.full(n, big)
    stop_first = (sh < big) & (sh <= th)
    tgt_first = (th < big) & ~stop_first
    d, entry = t["d"], t["entry"]
    px = t["close"].copy()
    xi = t["last"].copy()
    if stp is not None:
        s_pts = stp * t["R"]
        oa = t["open_adv"][idx, np.minimum(sh, 71)]
        px = np.where(stop_first, entry - d * np.maximum(s_pts, oa) - d * TICK, px)
        xi = np.where(stop_first, sh, xi)
    if tgt is not None:
        px = np.where(tgt_first, entry + d * tgt * t["R"], px)
        xi = np.where(tgt_first, th, xi)
    pnl = d * (px - entry) * PV - 2 * FEE
    worst = -t["cumadv"][idx, np.minimum(xi, 71)] * PV - FEE
    return pnl, np.minimum(worst, pnl)


def stats(pnl: np.ndarray, worst: np.ndarray, n_sess: int) -> dict:
    if len(pnl) == 0:
        return {"n": 0, "per yr": 0.0, "win": 0.0, "pf": 0.0, "net": 0.0, "avg": 0.0, "t": 0.0, "mdd": 0.0}
    e = np.cumsum(pnl)
    before = np.r_[0.0, e[:-1]]
    peak = np.maximum.accumulate(np.r_[0.0, e])[:-1]
    mdd = float(max(0.0, (peak - (before + worst)).max(), (np.maximum.accumulate(e) - e).max()))
    w, l_ = pnl[pnl > 0].sum(), -pnl[pnl <= 0].sum()
    sd = pnl.std(ddof=1) if len(pnl) > 1 else 0.0
    return {"n": len(pnl), "per yr": round(len(pnl) / (n_sess / 252), 1), "win": round(100 * (pnl > 0).mean(), 1),
            "pf": round(float(w / l_) if l_ > 0 else 99.0, 3), "net": round(float(pnl.sum())),
            "avg": round(float(pnl.mean()), 2), "t": round(float(pnl.mean() / (sd / np.sqrt(len(pnl)))) if sd else 0, 2),
            "mdd": round(mdd)}


def evaluate(arr: dict, windows: list, rules: list) -> list[dict]:
    out = []
    for fam, filt in sorted({(r[0], r[1]) for r in rules}):
        per_win = {}
        for name, a0, b0 in windows:
            a = arr[name]
            rows = np.flatnonzero((a["day"] >= a0) & (a["day"] <= b0))
            per_win[(name, a0)] = (trades(a, signals(a, fam, filt), rows), len(rows))
        for _f, _g, tgt, stp in [r for r in rules if r[0] == fam and r[1] == filt]:
            row = {"family": fam, "filter": filt, "target": tgt, "stop": stp}
            for (name, a0), (t, n_sess) in per_win.items():
                pnl, worst = exits(t, tgt, stp) if t is not None else (np.array([]), np.array([]))
                row.update({f"{name}{a0[:4]} {k}": v for k, v in stats(pnl, worst, n_sess).items()})
            out.append(row)
    return out


def main() -> None:
    data, prefix = Path(sys.argv[1]), sys.argv[2]
    sets, _ = H.load(data)
    arr = {k: arrays(v, scaled=k != "proxy") for k, v in sets.items()}
    rules = list(itertools.product(FAMILIES, FILTERS, TARGETS, STOPS))
    dev = pd.DataFrame(evaluate(arr, DEV, rules))
    keys = [("index2011", "nq2015")]
    i_, n_ = keys[0]
    dev["dev pass"] = ((dev[f"{i_} win"] >= 80) & (dev[f"{n_} win"] >= 80) & (dev[f"{i_} pf"] >= 2) &
                       (dev[f"{n_} pf"] >= 2) & (dev[f"{i_} net"] > 0) & (dev[f"{n_} net"] > 0) &
                       (dev[f"{i_} per yr"] >= 20) & (dev[f"{n_} per yr"] >= 20))
    dev["min win"] = dev[[f"{i_} win", f"{n_} win"]].min(1)
    dev["min pf"] = dev[[f"{i_} pf", f"{n_} pf"]].min(1)
    dev["min per yr"] = dev[[f"{i_} per yr", f"{n_} per yr"]].min(1)
    dev.to_csv(f"{prefix}_dev.csv", index=False)
    print("rules", len(dev), "dev pass", int(dev["dev pass"].sum()), flush=True)
    for w in (60, 70, 80, 90):
        sub = dev[(dev["min win"] >= w) & (dev["min per yr"] >= 20)]
        best = sub.sort_values("min pf", ascending=False).head(1)
        print(f"frontier: min net win >= {w}%: {len(sub)} rules; best min PF",
              best[["family", "filter", "target", "stop", "min win", "min pf"]].to_dict("records"), flush=True)
    elig = dev[(dev["min per yr"] >= 20) & (dev[f"{i_} net"] > 0) & (dev[f"{n_} net"] > 0)]
    fin = elig[elig["min win"] >= 80].sort_values("min pf", ascending=False).head(5)
    if len(fin) < 5:
        rest = elig[(elig["min win"] >= 70) & ~elig.index.isin(fin.index)].sort_values("min pf", ascending=False)
        fin = pd.concat([fin, rest.head(5 - len(fin))])
    finalists = [tuple(x) for x in fin[["family", "filter", "target", "stop"]].itertuples(index=False)]
    finalists = [(a, b, None if pd.isna(c) else c, None if pd.isna(d) else d) for a, b, c, d in finalists]
    print("finalists", finalists, flush=True)
    test = pd.DataFrame(evaluate(arr, TEST + USER, finalists))
    test.to_csv(f"{prefix}_test.csv", index=False)
    print(test.T.to_string(), flush=True)


if __name__ == "__main__":
    main()
