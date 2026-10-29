"""Candidate H1, pre-registered in docs/CANDIDATE_H1.md: a daily pullback in an uptrend, traded in regular hours.

The signal comes from the Nasdaq-100 index's daily regular-hours closes: close above its 200-session average and a
2-session RSI under L. The next session buys 1 MNQ at the 09:30 or 10:00 open, with a stop k x ATR14 below and an
optional 0.5 ATR target. It exits at that day's close ("day") or at the first close above the 5-session average, after
5 sessions at the latest ("swing").

Stage "dev" runs the 72 settings on the development years and picks one by the frozen rule. Stage "holdout" runs only
that setting on the holdout years and the stand-in. Points are scaled to a 30,000 price level on the histories, and are
unscaled on the stand-in. $0.62 a side, a tick on market and stop fills, none on target limits.

    python research/h1_dip.py <data dir> dev <out.csv>
    python research/h1_dip.py <data dir> holdout <out.csv> '<frozen setting as JSON>'
"""
from __future__ import annotations

import glob
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v38_gap as G  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

TICK, PV, FEE, LEVEL = 0.25, 2.0, 0.62, 30000.0
GRID = {"L": (10, 20, 30), "entry": (570, 600), "k": (0.5, 1.0, 2.0), "exit": ("day", "swing"), "target": (0.0, 0.5)}
WINDOWS = {"dev": [("nq", "2015-01-01", "2019-12-31"), ("index", "2011-01-01", "2018-12-31")],
           "holdout": [("nq", "2020-01-01", "2025-07-31"), ("index", "2019-01-01", "2026-09-30"),
                       ("proxy", "2025-01-02", "2026-12-31")]}


def load(data: Path) -> tuple[dict, pd.Series]:
    nq = G.sessions(G.rth5(pd.read_pickle(data / "nq1m_all.pkl")), True)
    ix_raw = pd.concat([load_histdata(f) for f in sorted(glob.glob(str(data / "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv")))])
    ix_raw = ix_raw[~ix_raw.index.duplicated()].sort_index()
    ix = G.sessions(G.rth5(ix_raw), False)
    px = G.sessions(G.rth5(pd.read_pickle(data / "proxy_5m.pkl")), False)
    closes = pd.Series({s[0]: s[6][-1] for s in ix})
    pc = pd.Series({s[0]: s[6][-1] for s in px})
    common = closes.index.intersection(pc.index)
    ratio = closes[common[-1]] / pc[common[-1]]
    closes = pd.concat([closes, pc[pc.index > closes.index[-1]] * ratio]).sort_index()
    return {"nq": nq, "index": ix, "proxy": px}, closes


def signals(closes: pd.Series) -> pd.DataFrame:
    d = closes.diff()
    up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    rsi = rsi.fillna(100.0)
    return pd.DataFrame({"trend": closes > closes.rolling(200).mean(), "rsi": rsi})


def simulate(sess: list, sig: pd.DataFrame, start: str, end: str, p: dict, scaled: bool) -> tuple[pd.DataFrame, dict]:
    """Trades and the marked-equity bookkeeping for one window. Entries only on days in [start, end]."""
    days = [s[0] for s in sess]
    first = int(np.searchsorted(days, start))
    last = int(np.searchsorted(days, end, side="right"))
    sig_days = sig.index.to_numpy()
    rng = np.array([s[4].max() - s[5].min() for s in sess])
    dclose = np.array([s[6][-1] for s in sess])
    rows, marks = [], []  # marks: (session, bar, worst, close) while a position is open at the bar's end
    pos = None
    for i in range(max(first, 14), len(sess)):
        day, _pc, mi, o, h, lo, c = sess[i]
        if pos is None:
            if i >= last:
                break
            k_sig = int(np.searchsorted(sig_days, day)) - 1  # the last signal day before this session
            if k_sig < 0 or not (sig.trend.iloc[k_sig] and sig.rsi.iloc[k_sig] < p["L"]):
                continue
            j0 = np.flatnonzero(mi == p["entry"])
            if not len(j0):
                continue
            j0 = int(j0[0])
            atr = rng[i - 14:i].mean()
            f = LEVEL / o[j0] if scaled else 1.0
            entry = o[j0] * f + TICK
            pos = {"i0": i, "j0": j0, "day": day, "f": f, "entry": entry, "stop": entry - p["k"] * atr * f,
                   "tgt": entry + p["target"] * atr * f if p["target"] else None, "held": 0}
            j_start = j0
        else:
            j_start = 0
        f, entry, stop, tgt = pos["f"], pos["entry"], pos["stop"], pos["tgt"]
        out = reason = None
        for j in range(j_start, len(mi)):
            if lo[j] * f <= stop:
                out, reason = min(o[j] * f, stop) - TICK, "stop"
            elif tgt is not None and h[j] * f >= tgt:
                out, reason = tgt, "target"
            elif j == len(mi) - 1:
                pos["held"] += 1
                if p["exit"] == "day":
                    out, reason = c[j] * f - TICK, "close"
                else:
                    sma5 = dclose[i - 4:i + 1].mean()
                    gap = i + 1 >= len(sess) or (pd.Timestamp(sess[i + 1][0]) - pd.Timestamp(day)).days > 5
                    if c[j] > sma5 or pos["held"] >= 5 or gap:
                        out, reason = c[j] * f - TICK, "sma5" if c[j] > sma5 else "time"
            if out is not None:
                pnl = (out - entry) * PV - 2 * FEE
                rows.append({"day": pos["day"], "exit_day": day, "sessions": pos["held"], "reason": reason,
                             "gross": (out - entry + (0 if reason == "target" else TICK) + TICK) * PV + 2 * FEE,
                             "pnl": pnl, "i_exit": i, "j_exit": j})
                pos = None
                break
            marks.append((i, j, (lo[j] * f - entry) * PV - FEE, (c[j] * f - entry) * PV - FEE))
    return pd.DataFrame(rows), {"marks": marks, "sess": sess, "first": first, "last": last}


def drawdowns(tf: pd.DataFrame, book: dict) -> tuple[float, float]:
    sess, first, last = book["sess"], book["first"], book["last"]
    if tf.empty:
        return 0.0, 0.0
    e = np.r_[0.0, tf.pnl.cumsum().to_numpy()]
    closed_dd = float((np.maximum.accumulate(e) - e).max())
    end = max(last, int(tf.i_exit.max()) + 1)
    lens = np.array([len(s[2]) for s in sess[first:end]])
    off = np.r_[0, np.cumsum(lens)]
    n = int(off[-1])
    realized = np.zeros(n)
    for t in tf.itertuples():
        realized[off[t.i_exit - first] + t.j_exit] += t.pnl
    closed = np.cumsum(realized)
    worst, close = closed.copy(), closed.copy()
    for i, j, w, c in book["marks"]:
        g = off[i - first] + j
        worst[g], close[g] = closed[g] + w, closed[g] + c
    peak = np.maximum(np.maximum.accumulate(close), 0.0)
    return closed_dd, float(max(0.0, (peak - worst).max()))


def stats(tf: pd.DataFrame, book: dict, years: float) -> dict:
    if tf.empty:
        return {"trades": 0, "trades/yr": 0.0}
    p = tf.pnl.to_numpy()
    wins, losses = p[p > 0], -p[p <= 0]
    aw, al = (wins.mean() if len(wins) else 0.0), (losses.mean() if len(losses) else 0.0)
    closed_dd, marked_dd = drawdowns(tf, book)
    return {"trades": len(p), "trades/yr": round(len(p) / years, 1),
            "gross $/trade": round(float(tf.gross.mean()), 2), "cost $/trade": round(float((tf.gross - tf.pnl).mean()), 2),
            "net $/trade": round(float(p.mean()), 2),
            "t": round(float(p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))), 2) if len(p) > 1 else 0.0,
            "net win %": round(100 * len(wins) / len(p), 1),
            "breakeven win %": round(100 * al / (aw + al), 1) if aw + al > 0 else 0.0,
            "within $5": int((np.abs(p) <= 5).sum()),
            "pf": round(float(wins.sum() / max(1e-9, losses.sum())), 3), "net $": round(float(p.sum())),
            "closed dd $": round(closed_dd), "marked dd $": round(marked_dd), "worst trade $": round(float(p.min())),
            "avg sessions held": round(float(tf.sessions.mean()), 2)}


def run_windows(sets: dict, sig: pd.DataFrame, stage: str, p: dict) -> list[dict]:
    out = []
    for name, a, b in WINDOWS[stage]:
        tf, book = simulate(sets[name], sig, a, b, p, scaled=name != "proxy")
        n_sess = sum(a <= s[0] <= b for s in sets[name])
        r = {**p, "set": name, "from": a, "to": min(b, sets[name][-1][0]), "sessions": n_sess,
             **stats(tf, book, n_sess / 252)}
        r["_pnl"] = tf.pnl.to_numpy() if len(tf) else np.array([])
        out.append(r)
    return out


def pooled_t(rows: list[dict]) -> float:
    p = np.concatenate([r["_pnl"] for r in rows])
    return float(p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))) if len(p) > 1 else 0.0


def main() -> None:
    data, stage, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    sets, closes = load(data)
    sig = signals(closes)
    print({k: (v[0][0], v[-1][0], len(v)) for k, v in sets.items()}, flush=True)
    rows = []
    if stage == "dev":
        keys = list(GRID)
        best = None
        for combo in itertools.product(*GRID.values()):
            p = dict(zip(keys, combo, strict=True))
            rs = run_windows(sets, sig, "dev", p)
            t = pooled_t(rs)
            ok = all(r.get("trades/yr", 0) >= 25 and r.get("net $/trade", -1) > 0 for r in rs)
            for r in rs:
                r.update({"pooled t": round(t, 2), "qualifies": ok})
            rows += rs
            if ok and (best is None or t > best[0]):
                best = (t, p)
            print(p, [(r["set"], r.get("trades/yr"), r.get("net $/trade"), r.get("net win %"), r.get("pf")) for r in rs],
                  round(t, 2), ok, flush=True)
        print("SELECTED", best, flush=True)
    else:
        p = json.loads(sys.argv[4])
        rs = run_windows(sets, sig, "holdout", p)
        t = pooled_t(rs)
        for r in rs:
            r["pooled t"] = round(t, 2)
            print(r | {"_pnl": None}, flush=True)
        rows += rs
    pd.DataFrame([{k: v for k, v in r.items() if k != "_pnl"} for r in rows]).to_csv(out, index=False)


if __name__ == "__main__":
    main()
