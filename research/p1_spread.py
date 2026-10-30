"""Candidate P1, pre-registered in docs/CANDIDATE_P1.md: a hedged intraday Nasdaq-100 / S&P 500 spread, 2 MNQ against
beta-weighted MES.

z is the session's spread move (Nasdaq log return since 09:30 minus beta x the S&P's) over its expected size. At a bar
close from 10:00 to 15:00 with |z| >= Z, the gap is faded at the next open. The trade exits at the next open after z
comes back to Zexit or reaches Z + Zstop, else at 15:55.

    python research/p1_spread.py <data dir> dev <out.csv>
    python research/p1_spread.py <data dir> dev2 <out.csv>        # P2, following the gap
    python research/p1_spread.py <data dir> holdout <out.csv> '<frozen setting as JSON>'
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h1_dip as H  # noqa: E402
import v38_gap as G  # noqa: E402

FEE = 0.62
PV_N, PV_S, TICK = 2.0, 5.0, 0.25
QN = 2
GRID = {"Z": (1.5, 2.0, 2.5), "Zstop": (1.0, 2.0, 99.0), "Zexit": (0.0, 0.5)}
GRID_P2 = {"mode": ("follow",), "Z": (1.5, 2.0, 2.5), "Zback": (0.0, 1.0, -99.0)}  # P2: follow the gap; -99 = no exit
WINDOWS = {"dev": [("2011-2018", "2011-01-01", "2018-12-31")],
           "holdout": [("2019-2024", "2019-01-01", "2024-12-31"), ("user window", "2025-01-02", "2026-09-30")]}


def load(data: Path) -> list[dict]:
    n = G.rth5(pd.read_pickle(data / "nsx1m_scaled.pkl"))
    s = G.rth5(pd.read_pickle(data / "spx1m_scaled.pkl"))
    j = n.join(s, how="inner", lsuffix="_n", rsuffix="_s")
    t = j.index.tz_convert("America/New_York")
    day = np.asarray(t.strftime("%Y-%m-%d"))
    mins = np.asarray(t.hour * 60 + t.minute)
    out = []
    for d in pd.unique(day):
        m = day == d
        mi = mins[m]
        if mi[0] != 570 or mi[-1] != 955 or m.sum() < 70:
            continue
        g = j[m]
        r = {"day": d, "mi": mi}
        for leg in ("n", "s"):
            for col in ("open", "high", "low", "close"):
                r[f"{leg}{col[0]}"] = g[f"{col}_{leg}"].to_numpy(float)
            px = np.r_[r[f"{leg}o"][0], r[f"{leg}c"]]
            r[f"r{leg}"] = np.diff(np.log(px))
        out.append(r)
    for i, r in enumerate(out):  # beta and the 5-minute spread volatility from the previous 20 sessions
        if i < 20:
            r["ok"] = False
            continue
        rn = np.concatenate([out[k]["rn"] for k in range(i - 20, i)])
        rs = np.concatenate([out[k]["rs"] for k in range(i - 20, i)])
        beta = float(np.cov(rn, rs)[0, 1] / np.var(rs, ddof=1))
        s5 = float(np.std(rn - beta * rs, ddof=1))
        k = np.arange(1, len(r["mi"]) + 1)
        x = np.log(r["nc"] / r["no"][0]) - beta * np.log(r["sc"] / r["so"][0])
        r.update({"ok": s5 > 0, "beta": beta, "z": x / (s5 * np.sqrt(k))})
    return out


def simulate(sess: list[dict], start: str, end: str, p: dict) -> tuple[pd.DataFrame, dict]:
    days = [s["day"] for s in sess]
    first = int(np.searchsorted(days, start))
    last = int(np.searchsorted(days, end, side="right"))
    rows, marks = [], []
    follow = p.get("mode") == "follow"
    max_trades = 1 if follow else 2
    for i in range(first, last):
        s = sess[i]
        if not s["ok"]:
            continue
        mi, z = s["mi"], s["z"]
        n_trades, pos = 0, None
        for j in range(len(mi)):
            if pos is not None:
                dn, ss, qs = pos["dn"], -pos["dn"], pos["qs"]
                sign = pos["sign"]
                last_bar = j == len(mi) - 1
                if follow:
                    trig = z[j] * sign <= p["Zback"]
                else:
                    trig = z[j] * sign <= p["Zexit"] or z[j] * sign >= p["Z"] + p["Zstop"]
                if trig or last_bar:
                    if last_bar:
                        n_px, s_px, reason = s["nc"][j], s["sc"][j], "close"
                        jx = j
                    else:
                        n_px, s_px = s["no"][j + 1], s["so"][j + 1]
                        reason = "stop" if follow else ("mean" if z[j] * sign <= p["Zexit"] else "stop")
                        jx = j + 1
                    n_exit, s_exit = n_px - dn * TICK, s_px - ss * TICK
                    gross_px = QN * PV_N * dn * (n_exit - pos["n_in"]) + qs * PV_S * ss * (s_exit - pos["s_in"])
                    fees = (QN + qs) * 2 * FEE
                    slip = QN * 2 * TICK * PV_N + qs * 2 * TICK * PV_S
                    pnl = gross_px - fees
                    rows.append({"day": s["day"], "dn": dn, "qs": qs, "reason": reason, "pnl": pnl,
                                 "gross": pnl + fees + slip, "i_exit": i, "j_exit": jx, "sessions": 0})
                    pos = None
                    if jx > j:
                        continue
                else:
                    nadv = s["nl"][j] if dn > 0 else s["nh"][j]
                    sadv = s["sl"][j] if ss > 0 else s["sh"][j]
                    w = QN * PV_N * dn * (nadv - pos["n_in"]) + qs * PV_S * ss * (sadv - pos["s_in"]) - (QN + qs) * FEE
                    c = (QN * PV_N * dn * (s["nc"][j] - pos["n_in"]) + qs * PV_S * ss * (s["sc"][j] - pos["s_in"])
                         - (QN + qs) * FEE)
                    marks.append((i, j, w, c))
                    continue
            if pos is None and n_trades < max_trades and 595 <= mi[j] <= 895 and j + 1 < len(mi) and abs(z[j]) >= p["Z"]:
                sign = 1 if z[j] > 0 else -1
                dn = sign if follow else -sign
                qs = max(1, int(round(QN * s["beta"] * PV_N * s["nc"][j] / (PV_S * s["sc"][j]))))
                pos = {"dn": dn, "sign": sign, "qs": qs, "n_in": s["no"][j + 1] + dn * TICK,
                       "s_in": s["so"][j + 1] - dn * TICK}
                n_trades += 1
    book_sess = [(x["day"], None, x["mi"]) for x in sess]
    return pd.DataFrame(rows), {"marks": marks, "sess": book_sess, "first": first, "last": last}


def run(sess: list[dict], stage: str, p: dict) -> list[dict]:
    out = []
    for name, a, b in WINDOWS[stage]:
        tf, book = simulate(sess, a, b, p)
        n_sess = sum(a <= s["day"] <= b for s in sess)
        r = {**p, "window": name, "sessions": n_sess, **H.stats(tf, book, n_sess / 252)}
        if len(tf):
            r.update({"days with a trade %": round(100 * tf.day.nunique() / n_sess, 1),
                      "avg MES": round(float(tf.qs.mean()), 2),
                      **{f"{k} %": round(100 * float((tf.reason == k).mean()), 1) for k in ("mean", "stop", "close")}})
        if name == "user window":
            r.update({"pass net": r.get("net $", 0) >= 75000, "pass win": r.get("net win %", 0) >= 80,
                      "pass pf": r.get("pf", 0) >= 2.0, "pass marked dd": r.get("marked dd $", 1e9) < 4000})
        out.append(r)
        print({k: v for k, v in r.items()}, flush=True)
    return out


def main() -> None:
    data, stage, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    sess = load(data)
    print("sessions", len(sess), sess[0]["day"], sess[-1]["day"], flush=True)
    rows = []
    if stage in ("dev", "dev2"):
        grid = GRID if stage == "dev" else GRID_P2
        best = None
        for combo in itertools.product(*grid.values()):
            p = dict(zip(grid, combo, strict=True))
            r = run(sess, "dev", p)[0]
            r["qualifies"] = r.get("trades/yr", 0) >= 25 and r.get("net $/trade", -1) > 0
            if r["qualifies"] and (best is None or r["t"] > best[0]):
                best = (r["t"], p)
            rows.append(r)
        print("SELECTED", best, flush=True)
    else:
        rows += run(sess, "holdout", json.loads(sys.argv[4]))
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
