"""A learned filter on the noise strategy's signals (docs/RESULTS.md, after v2.8): every half-hour check whose close is
past a noise line is described by what was known at that close (the time, how far past the line, the gap, the
previous days' moves, the day's range so far, ...), and a model trained only on earlier years' trades scores it. Low
scores are skipped: the strategy's own run (daily budget included) gets a per-check veto through confirm_map.

Walk-forward: on NQ futures 2015-2025 and the Nasdaq-100 index 2011-2026 each year's checks are scored by a model fit
on that set's earlier years (from its fourth year). The 2025-2026 stand-in and the user's MNQ window are scored by a
model fit on both histories before 2025. The labels come from a run without the daily budget (every signal taken
while flat); the cut-off for "low" is a quantile of the training rows' own scores.

    python research/v29_meta.py <out.csv> '<base: JSON overrides>' '<label base: JSON overrides>' <data dir> \
        <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
SCAN_MINUTES=30 (environment): 30-minute bars. META_KINDS (logit,gbc,gbr), META_Q (the skipped shares) and META_HP
(the regressor's depth,iterations,leaf size) pick the runs.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as S  # noqa: E402
from v21_streak_scan import streak  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
FEATS = ["tod", "d", "exc", "sig_rel", "move", "gap", "prev_ret", "r5", "r20", "rng", "pos", "last", "twap", "calm",
         "dow", "prev_rng", "seen"]


def config(kw: dict, skip) -> NoiseConfig:
    cfg = NoiseConfig(**{**S.V23, **kw})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    return cfg


def features(bars: pd.DataFrame, bands: list, m: int) -> pd.DataFrame:
    """One row per check whose close is past a line: what was known at that close."""
    t = bars.index.tz_convert(NY)
    day = np.asarray(t.strftime("%Y-%m-%d"))
    o, h, lo_, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(bars)] - 1
    sess = pd.DataFrame({"a": starts, "b": ends, "open": o[starts], "close": c[ends]},
                        index=day[starts])
    sess["high"] = [h[a:b + 1].max() for a, b in zip(starts, ends, strict=True)]
    sess["low"] = [lo_[a:b + 1].min() for a, b in zip(starts, ends, strict=True)]
    sess["rng"] = (sess.high - sess.low) / sess.close
    sess["dr10"] = sess.rng.rolling(10).mean().shift(1)  # the 10 sessions before this one
    sess["dr40"] = sess.rng.rolling(40).mean().shift(1)
    sess["pc"] = sess.close.shift(1)
    sess["ppc"] = sess.close.shift(2)
    sess["pc5"] = sess.close.shift(6)
    sess["pc20"] = sess.close.shift(21)
    sess["prev_rng"] = sess.rng.shift(1)
    pos_of = {d: k for k, d in enumerate(sess.index)}
    rows = []
    seen: dict = {}
    step = max(1, 30 // m)
    for i, up, lw in bands:
        if not (c[i] > up or c[i] < lw):
            continue
        dd = day[i]
        s = sess.iloc[pos_of[dd]]
        if not np.isfinite(s.dr10) or not np.isfinite(s.dr40) or not np.isfinite(s.pc20):
            continue
        d = 1 if c[i] > up else -1
        line = up if d > 0 else lw
        base = max(s.open, s.pc) if d > 0 else min(s.open, s.pc)
        sig = abs(line / base - 1)
        a = int(s.a)
        hi, lw2 = h[a:i + 1].max(), lo_[a:i + 1].min()
        r = s.dr10
        key = (dd, d)
        end = t[i].hour * 60 + t[i].minute + m
        rows.append({
            "i": i, "key": (dd, end), "year": int(dd[:4]), "tod": end, "d": d,
            "exc": d * (c[i] - line) / line / max(sig, 1e-9), "sig_rel": sig / r,
            "move": d * (c[i] / s.open - 1) / r, "gap": d * (s.open / s.pc - 1) / r,
            "prev_ret": d * (s.pc / s.ppc - 1) / r, "r5": d * (s.pc / s.pc5 - 1) / r,
            "r20": d * (s.pc / s.pc20 - 1) / r, "rng": (hi - lw2) / c[i] / r,
            "pos": (c[i] - lw2) / max(hi - lw2, 1e-9) if d > 0 else (hi - c[i]) / max(hi - lw2, 1e-9),
            "last": d * (c[i] / c[max(a, i - step)] - 1) / r, "twap": d * (c[i] / c[a:i + 1].mean() - 1) / r,
            "calm": r / s.dr40, "dow": t[i].dayofweek, "prev_rng": s.prev_rng / r, "seen": seen.get(key, 0)})
        seen[key] = seen.get(key, 0) + 1
    return pd.DataFrame(rows)


def labelled(bars: pd.DataFrame, cfg: NoiseConfig, m: int) -> pd.DataFrame:
    res = run(bars, cfg, minutes=m)
    f = features(bars, res.bands, m)
    tf = res.trades_frame()
    if tf.empty:
        return f.assign(pnl=np.nan)
    pnl = tf.groupby("entry_bar").pnl.sum()
    sig = pd.Series(pnl.to_numpy(), index=pnl.index - 1)  # the fill is the bar after the signal check
    return f.assign(pnl=f.i.map(sig))


def models(kind: str):
    if kind == "logit":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000))
    if kind == "gbc":
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=60,
                                              l2_regularization=1.0)
    depth, iters, leaf = (int(x) for x in os.environ.get("META_HP", "3,150,60").split(","))
    return HistGradientBoostingRegressor(max_depth=depth, learning_rate=0.05, max_iter=iters, min_samples_leaf=leaf,
                                         l2_regularization=1.0, loss="absolute_error", random_state=0)


def fit_score(train: pd.DataFrame, test: pd.DataFrame, kind: str) -> tuple[np.ndarray, np.ndarray]:
    tr = train.dropna(subset=["pnl"])
    x, xt = tr[FEATS].to_numpy(float), test[FEATS].to_numpy(float)
    mdl = models(kind)
    if kind == "gbr":
        y = np.clip(tr.pnl.to_numpy(), *np.percentile(tr.pnl, [2, 98]))
        mdl.fit(x, y)
        return mdl.predict(x), mdl.predict(xt)
    mdl.fit(x, (tr.pnl > 0).astype(int))
    return mdl.predict_proba(x)[:, 1], mdl.predict_proba(xt)[:, 1]


def metrics(name: str, tf: pd.DataFrame, first) -> dict:
    if first:
        tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
    p = tf.groupby("exit_bar", sort=True).pnl.sum().to_numpy()
    lg = tf.pnl.to_numpy()
    e = np.r_[0, np.cumsum(p)]
    out = {f"{name} net": round(p.sum()), f"{name} dd": round((np.maximum.accumulate(e) - e).max()),
           f"{name} win": round(100 * (lg > 0).mean(), 1) if len(lg) else 0,
           f"{name} pf": round(lg[lg > 0].sum() / max(1e-9, -lg[lg < 0].sum()), 3), f"{name} n": len(lg),
           f"{name} streak": streak(p),
           f"{name} wday": round(tf.groupby(tf.exit_time.dt.date).pnl.sum().min()) if len(tf) else 0}
    if name in ("nq", "index"):
        out[f"{name} yrs"] = json.dumps(tf.groupby(tf.entry_time.dt.year).pnl.sum().round().astype(int).tolist())
    return out


def main() -> None:
    out, base, lab = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
    m = int(os.environ.get("SCAN_MINUTES", "5"))
    S.init({}, *sys.argv[4:7])
    rows = {name: labelled(bars, config({**base, **lab}, skip), m) for name, (bars, _, skip) in S.D.items()}
    for name, f in rows.items():
        print(name, len(f), int(f.pnl.notna().sum()), f.year.min(), f.year.max(), flush=True)
    results = [{"rule": "base", **{k: v for name, (bars, first, skip) in S.D.items()
                                   for k, v in metrics(name, run(bars, config(base, skip), minutes=m)
                                                       .trades_frame(), first).items()}}]
    for kind in os.environ.get("META_KINDS", "logit,gbc,gbr").split(","):
        scores = {}  # per set: (test score, cut-offs per quantile) for every row
        for name in ("nq", "index"):
            f = rows[name]
            sc = pd.Series(np.nan, index=f.index)
            cuts = {}
            years = sorted(f.year.unique())
            for y in years[3:]:
                tr, te = f[f.year < y], f[f.year == y]
                s_tr, s_te = fit_score(tr, te, kind)
                sc[te.index] = s_te
                cuts[y] = s_tr
            scores[name] = (sc, cuts)
        pool = pd.concat([rows["nq"][rows["nq"].year < 2025], rows["index"][rows["index"].year < 2025]])
        for name in ("proxy", "win"):
            s_tr, s_te = fit_score(pool, rows[name], kind)
            scores[name] = (pd.Series(s_te, index=rows[name].index), {y: s_tr for y in rows[name].year.unique()})
        for q in (float(x) for x in os.environ.get("META_Q", "0.2,0.35,0.5").split(",")):
            r = {"rule": f"{kind} skip {int(q * 100)}%"}
            for name, (bars, first, skip) in S.D.items():
                f = rows[name]
                sc, cuts = scores[name]
                thr = f.year.map({y: np.quantile(v, q) for y, v in cuts.items()})
                keep = sc >= thr
                cmap = {k: (d if (ok or not np.isfinite(s)) else 0)
                        for k, d, ok, s in zip(f.key, f.d, keep, sc, strict=True)}
                cfg = config({**base, "confirm_map": cmap, "confirm_mode": "with"}, skip)
                r.update(metrics(name, run(bars, cfg, minutes=m).trades_frame(), first))
            results.append(r)
            print(r["rule"], {k: r[k] for k in ("proxy net", "proxy dd", "proxy win", "proxy pf", "nq net",
                                                "nq pf", "index net", "index pf")}, flush=True)
    d = pd.DataFrame(results)
    b = d.iloc[0]
    for k in ("nq", "index"):
        d[f"{k} r/b"] = ((d[f"{k} net"] / d[f"{k} dd"]) / (b[f"{k} net"] / b[f"{k} dd"])).round(2)
        d[f"{k} net/b"] = (d[f"{k} net"] / b[f"{k} net"]).round(2)
        by = np.array(json.loads(b[f"{k} yrs"]))
        d[f"{k} yrs+"] = [int((np.array(json.loads(x)) > by).sum()) for x in d[f"{k} yrs"]]
    d.to_csv(out, index=False)
    pd.set_option("display.width", 320)
    print(d[["rule", "win net", "proxy net", "proxy dd", "proxy win", "proxy pf", "proxy wday", "nq net/b", "nq r/b",
             "nq pf", "nq yrs+", "index net/b", "index r/b", "index pf", "index yrs+"]].to_string(index=False))


if __name__ == "__main__":
    main()
