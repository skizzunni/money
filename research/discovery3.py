"""Third search: the overnight session, regime-conditional patterns, and a nonlinear walk-forward model.

    python research/discovery3.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running:
  1. New measurements, added to discovery.py's 30: the overnight session split into Asia (18:00-03:00 ET)
     and Europe (03:00-09:30) moves, the 08:30-09:30 move, overnight volatility and trend consistency,
     the overnight high/low against yesterday's high/low, and yesterday's afternoon and last-30-minute
     moves. Tested one at a time like discovery.py (discovery 2011-2018 at a 5% false discovery rate,
     confirmation 2019-2022), over the family of new tests only.
  2. Regime-conditional patterns: 13 base measurements x 6 regimes (volatility high/low, last month up/
     down, overnight range wide/narrow; cut-offs from 2011-2018) x 12 half hours x 2 targets, same scheme.
  3. Walk-forward gradient boosting on all measurements pooled across half hours (time of day is a
     feature). For each year Y from 2015 to 2026 the model is trained on 2011..Y-1 and predicts Y, so
     every prediction is out of sample. Two targets (next 30 minutes, to the close). Primary trading
     rule, fixed here: at each half hour take the predicted direction and hold 30 minutes, only when the
     predicted move exceeds twice the round-trip cost; secondary rules (always, once the cost) are shown
     for information. 1 MNQ at the last price in the data, $1.24 fees + 1 tick each way per trade.
  Pass bar for any trading rule: t >= 2.5 on the out-of-sample years and positive in at least 75% of them.
  Model settings are fixed and not tuned: depth 3, 300 rounds, learning rate 0.05, min 200 rows per leaf.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

FIRST_OOS_YEAR = 2015
BASE_FOR_REGIMES = ["move_from_open", "last_30m_move", "last_5m_move", "distance_from_twap", "position_in_day_range",
                    "move_in_noise_units", "gap", "first_30m_move", "vs_prev_high", "vs_prev_low",
                    "up_minutes_last_30", "asia_move", "europe_move"]


def overnight_features(raw: pd.DataFrame, days: L.Days, n_checks: int) -> dict[str, np.ndarray]:
    idx = raw.index
    hhmm = (idx.hour * 100 + idx.minute).to_numpy()
    trade_date = pd.Index((idx + pd.Timedelta(hours=6)).date)
    on = (hhmm >= 1800) | (hhmm < 930)
    asia = (hhmm >= 1800) | (hhmm < 300)
    late = (hhmm >= 830) & (hhmm < 930)
    close = raw.close.to_numpy()
    df = pd.DataFrame({"date": trade_date, "close": close, "on": on, "asia": asia, "late": late,
                       "r": np.r_[np.nan, np.diff(np.log(close))]})
    g = df[df.on].groupby("date")
    first_on = g.close.first()
    asia_last = df[df.asia].groupby("date").close.last()
    late_first = df[df.late].groupby("date").close.first()
    on_last = g.close.last()
    rv = g.r.apply(lambda s: np.nansum(s.values**2))
    up_share = g.r.apply(lambda s: np.nanmean(s.values > 0))
    dates = pd.Index(days.dates)
    base = pd.DataFrame(index=dates)
    base["asia_move"] = (asia_last / first_on - 1).reindex(dates).to_numpy()
    base["europe_move"] = (on_last / asia_last - 1).reindex(dates).to_numpy()
    base["pre_open_move"] = (on_last / late_first - 1).reindex(dates).to_numpy()
    rv_s = rv.reindex(dates)
    base["overnight_vol_vs_normal"] = (rv_s / rv_s.rolling(20, min_periods=20).mean().shift(1)).to_numpy()
    base["overnight_up_share"] = up_share.reindex(dates).to_numpy()
    # overnight extremes against yesterday's day-session extremes
    rth_hi, rth_lo = np.nanmax(days.h, axis=1), np.nanmin(days.l, axis=1)
    prev_hi, prev_lo = np.r_[np.nan, rth_hi[:-1]], np.r_[np.nan, rth_lo[:-1]]
    on_hi = raw[on].groupby(trade_date[on]).high.max().reindex(dates).to_numpy()
    on_lo = raw[on].groupby(trade_date[on]).low.min().reindex(dates).to_numpy()
    base["overnight_above_prev_high"] = (on_hi > prev_hi).astype(float)
    base["overnight_below_prev_low"] = (on_lo < prev_lo).astype(float)
    base["overnight_high_vs_prev_high"] = on_hi / prev_hi - 1
    base["overnight_low_vs_prev_low"] = on_lo / prev_lo - 1
    # yesterday's afternoon (13:30 -> close) and last 30 minutes
    cf = days.cf
    base["prev_afternoon_move"] = np.r_[np.nan, (cf[:-1, -1] / cf[:-1, 239] - 1)]
    base["prev_last_30m_move"] = np.r_[np.nan, (cf[:-1, -1] / cf[:-1, 359] - 1)]
    valid_prev = ~np.isnan(days.prev_close)
    out = {}
    for c in base.columns:
        v = base[c].to_numpy(float)
        if c.startswith("prev_") or "prev" in c:
            v = np.where(valid_prev, v, np.nan)
        out[c] = np.repeat(v[:, None], n_checks, axis=1)
    return out


def regime_tests(feats, targets, rows, regimes) -> pd.DataFrame:
    out = []
    disc, conf = rows["discovery"], rows["confirm"]
    for rname, mask in regimes.items():
        for fname in BASE_FOR_REGIMES:
            F = feats[fname]
            for tname in ("30m", "close"):
                Y = targets[tname]
                for k, m in enumerate(D.CHECKS):
                    if tname != "close" and m + D.HORIZONS[tname] > L.MINUTES:
                        continue
                    res = []
                    for r in (disc, conf):
                        rr = r[mask[r]]
                        rho, n = D.spearman(F[rr, k], Y[rr, k])
                        t = rho * math.sqrt((n - 2) / max(1 - rho * rho, 1e-12)) if not math.isnan(rho) else math.nan
                        res += [rho, t, n]
                    out.append((rname, fname, tname, m, *res))
    df = pd.DataFrame(out, columns=["regime", "feature", "target", "minute", "rho", "t", "n", "rho_confirm",
                                    "t_confirm", "n_confirm"]).dropna(subset=["t"])
    df["p"] = D.two_sided_p(df.t.to_numpy())
    df["fdr_keep"] = D.bh(df.p, D.FDR)
    df["confirmed"] = df.fdr_keep & (np.sign(df.t) == np.sign(df.t_confirm)) & (df.t_confirm.abs() >= D.Z95)
    return df


def walk_forward(feats, targets, meta, cost_bps, notional):
    names = [f for f in feats if f != "constant"]
    n, T = feats[names[0]].shape
    year = meta.year.to_numpy()
    ok = meta.ok.to_numpy()
    X = np.stack([feats[f] for f in names], axis=2)  # (n, T, F)
    X = np.where(np.isfinite(X), X, np.nan)
    tod = np.broadcast_to(np.arange(T)[None, :, None] / T, (n, T, 1))
    X = np.concatenate([X, tod], axis=2)
    results = {}
    for tname in ("30m", "close"):
        Y = targets[tname] * 1e4
        pred = np.full((n, T), np.nan)
        for y in range(FIRST_OOS_YEAR, int(year.max()) + 1):
            tr = ok & (year >= 2011) & (year < y)
            te = ok & (year == y)
            if te.sum() == 0:
                continue
            Xtr, ytr = X[tr].reshape(-1, X.shape[2]), Y[tr].reshape(-1)
            good = ~np.isnan(ytr)
            lo, hi = np.percentile(ytr[good], [1, 99])
            model = HistGradientBoostingRegressor(max_depth=3, max_iter=300, learning_rate=0.05,
                                                  min_samples_leaf=200, l2_regularization=1.0, random_state=0)
            model.fit(Xtr[good], np.clip(ytr[good], lo, hi))
            pred[te] = model.predict(X[te].reshape(-1, X.shape[2])).reshape(te.sum(), T)
        results[tname] = pred
    R30 = targets["30m"] * 1e4
    oos = ok & (year >= FIRST_OOS_YEAR)
    rows = []
    for tname, pred in results.items():
        for label, thr in (("always", 0.0), ("> 1x cost", cost_bps), ("> 2x cost (primary)", 2 * cost_bps)):
            pos = np.where(np.abs(pred) > thr, np.sign(pred), 0.0)
            pnl = np.where(np.isnan(pred) | np.isnan(R30), 0.0, pos * R30 - np.abs(pos) * cost_bps)
            day = pnl[oos].sum(axis=1) * notional / 1e4
            t = day.mean() / day.std(ddof=1) * math.sqrt(len(day))
            yrs = pd.Series(day, index=year[oos]).groupby(level=0).sum()
            trades = np.abs(pos[oos]).sum(axis=1).mean()
            rows.append({"target": tname, "rule": label, "trades_per_day": trades, "avg_per_day": day.mean(), "t": t,
                         "years_up": int((yrs > 0).sum()), "years": len(yrs),
                         "pass": t >= 2.5 and (yrs > 0).sum() >= 0.75 * len(yrs),
                         "by_year": yrs.round(0).astype(int).to_dict()})
    return pd.DataFrame(rows)


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    cost_bps = (2 * 0.25 + 1.24 / 2.0) / ref * 1e4
    feats, targets, meta = D.build(raw)
    days = L.Days(raw)
    new = overnight_features(raw, days, len(D.CHECKS))
    feats.update(new)
    rows = {nm: np.flatnonzero(meta.ok & (meta.year >= a) & (meta.year < b)) for nm, (a, b) in D.PERIODS.items()}
    pd.set_option("display.width", 220)

    # 1. new measurements one at a time
    one = D.test_all({k: v for k, v in feats.items() if k in new}, targets, rows["discovery"]).dropna(subset=["t"])
    one["fdr_keep"] = D.bh(one.p, D.FDR)
    conf = D.test_all({k: v for k, v in feats.items() if k in new}, targets, rows["confirm"])
    conf = conf.set_index(["feature", "target", "minute"])
    keep = one[one.fdr_keep].set_index(["feature", "target", "minute"]).join(conf[["t"]], rsuffix="_confirm")
    keep["confirmed"] = (np.sign(keep.t) == np.sign(keep.t_confirm)) & (keep.t_confirm.abs() >= D.Z95)
    print(f"1. overnight and cross-day measurements: {len(one)} tests, {int(one.fdr_keep.sum())} pass the luck filter, "
          f"{int(keep.confirmed.sum())} confirmed in 2019-2022")
    if len(keep):
        print(keep[["time", "rho", "t", "t_confirm", "confirmed"]].sort_values("t", key=abs, ascending=False)
              .round(3).to_string())

    # 2. regimes
    disc = rows["discovery"]
    def split(name):
        v = feats[name][:, 0]
        med = np.nanmedian(v[disc])
        return {f"{name} high": v > med, f"{name} low": v <= med}
    regimes = {}
    for nm in ("volatility_20d", "last_month_move", "overnight_range"):
        regimes.update(split(nm))
    reg = regime_tests(feats, targets, rows, regimes)
    print(f"\n2. regime-conditional patterns: {len(reg)} tests, {int(reg.fdr_keep.sum())} pass the luck filter, "
          f"{int(reg.confirmed.sum())} confirmed in 2019-2022")
    if reg.fdr_keep.any():
        shown = reg[reg.fdr_keep].copy()
        shown["time"] = shown.minute.map(lambda m: f"{(570 + m) // 60:02d}:{(570 + m) % 60:02d}")
        print(shown[["regime", "feature", "target", "time", "rho", "t", "t_confirm", "confirmed"]]
              .sort_values("t", key=abs, ascending=False).round(3).to_string(index=False))

    # 3. walk-forward boosting
    wf = walk_forward(feats, targets, meta, cost_bps, notional)
    print(f"\n3. walk-forward gradient boosting, out of sample {FIRST_OOS_YEAR}-2026, 1 MNQ at {ref:,.0f}:")
    for _, r in wf.iterrows():
        print(f"   {r.target:5s} {r.rule:20s} trades/day {r.trades_per_day:4.1f}  ${r.avg_per_day:+7.2f}/day  "
              f"t {r.t:+5.2f}  years up {r.years_up}/{r.years}  {'PASS' if r['pass'] else 'fail'}")
        print(f"         by year {r.by_year}")


if __name__ == "__main__":
    main()
