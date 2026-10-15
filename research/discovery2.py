"""Second and third searches: extremes only, and many weak signals combined. Same periods as discovery.py.

    python research/discovery2.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running (after discovery.py found nothing that held up, and before looking at these):
  B. Extremes. For each feature, half-hour and target: mean forward return when the feature is in its
     top 10% minus when it is in its bottom 10% (cut-offs from 2011-2018). Welch t-test, Benjamini-Hochberg
     5% false discovery rate over all B tests, then the same sign and one-sided p < 5% in 2019-2022.
  C. Combined. For each half-hour and target (30m, close): ridge regression of the forward return (bps,
     clipped at the 2011-2018 1st/99th percentiles) on all features (standardized with 2011-2018 means
     and standard deviations, clipped at +/-3, missing = 0), ridge penalty = number of sessions, fit on
     2011-2018 only. Trading rules, position held 30 minutes and re-decided at every half hour:
       C1 30m model, always in the market, direction = sign of the prediction
       C2 30m model, only when |prediction| is in its top 20% (cut-off from 2011-2018)
       C3 close model, always in the market
       C4 close model, only when |prediction| is in its top 20%
     1 MNQ at today's price, $1.24 fees + 1 tick each way per trade. Pick the rule with the best 2019-2022
     t-stat of daily P&L, and only if that t-stat is at least 2. The pick is run once on 2023 - Sep 2026.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

DUMMIES = {"constant", "monday", "tuesday", "wednesday", "thursday", "friday", "turn_of_month", "opex_day",
           "opex_week", "gap_filled_yet"}


def welch(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 20 or len(b) < 20:
        return math.nan
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def family_b(feats, targets, rows) -> pd.DataFrame:
    out = []
    disc, conf = rows["discovery"], rows["confirm"]
    for fname, F in feats.items():
        if fname in DUMMIES:
            continue
        for tname, Y in targets.items():
            for k, m in enumerate(D.CHECKS):
                if tname != "close" and m + D.HORIZONS[tname] > D.L.MINUTES:
                    continue
                x = F[disc, k]
                good = np.isfinite(x)
                if good.sum() < 200:
                    continue
                lo, hi = np.nanpercentile(x[good], [10, 90])
                res = []
                for r in (disc, conf):
                    xr, yr = F[r, k], Y[r, k]
                    res.append((welch(yr[xr >= hi], yr[xr <= lo]),
                                1e4 * (np.nanmean(yr[xr >= hi]) - np.nanmean(yr[xr <= lo]))))
                out.append((fname, tname, D.CHECKS[k], *res[0], *res[1]))
    cols = ["feature", "target", "minute", "t", "spread_bps", "t_confirm", "spread_bps_confirm"]
    df = pd.DataFrame(out, columns=cols)
    df = df.dropna(subset=["t"])
    df["p"] = D.two_sided_p(df.t.to_numpy())
    df["fdr_keep"] = D.bh(df.p, D.FDR)
    df["confirmed"] = df.fdr_keep & (np.sign(df.t) == np.sign(df.t_confirm)) & (df.t_confirm.abs() >= D.Z95)
    return df


def design(feats, rows_fit, k):
    names = [f for f in feats if f != "constant"]
    X = np.stack([feats[f][:, k] for f in names], axis=1)
    X = np.where(np.isfinite(X), X, np.nan)
    mu, sd = np.nanmean(X[rows_fit], axis=0), np.nanstd(X[rows_fit], axis=0)
    sd[sd == 0] = 1.0

    def z(rows):
        Z = np.clip((X[rows] - mu) / sd, -3, 3)
        return np.nan_to_num(Z, nan=0.0)

    return z


def family_c(feats, targets, rows, cost_bps):
    disc, conf, test = rows["discovery"], rows["confirm"], rows["test"]
    preds = {}
    for tname in ("30m", "close"):
        P = np.full((len(next(iter(feats.values()))), len(D.CHECKS)), np.nan)
        cut = np.zeros(len(D.CHECKS))
        for k in range(len(D.CHECKS)):
            z = design(feats, disc, k)
            y = targets[tname][disc, k] * 1e4
            ok = ~np.isnan(y)
            lo, hi = np.percentile(y[ok], [1, 99])
            Xd, yd = z(disc)[ok], np.clip(y[ok], lo, hi)
            yd = yd - yd.mean()
            lam = len(yd)
            beta = np.linalg.solve(Xd.T @ Xd + lam * np.eye(Xd.shape[1]), Xd.T @ yd)
            for r in (disc, conf, test):
                P[r, k] = z(r) @ beta
            cut[k] = np.percentile(np.abs(P[disc, k]), 80)
        preds[tname] = (P, cut)
    # 30-minute returns at each half hour, for trading every rule the same way
    R30 = targets["30m"]
    rules = {}
    for name, tname, top in (("C1", "30m", False), ("C2", "30m", True), ("C3", "close", False), ("C4", "close", True)):
        P, cut = preds[tname]
        pos = np.sign(P)
        if top:
            pos = np.where(np.abs(P) >= cut[None, :], pos, 0.0)
        pnl_bps = pos * R30 * 1e4 - np.abs(pos) * cost_bps  # one round trip per half hour held
        rules[name] = (pos, pnl_bps)
    return preds, rules


def daily_stats(pnl_bps, rows, notional):
    day = np.nansum(pnl_bps[rows], axis=1) * notional / 1e4
    t = day.mean() / day.std(ddof=1) * math.sqrt(len(day))
    return day, t


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    cost_bps = (2 * 0.25 + 1.24 / 2.0) / ref * 1e4
    feats, targets, meta = D.build(raw)
    rows = {n: np.flatnonzero(meta.ok & (meta.year >= a) & (meta.year < b)) for n, (a, b) in D.PERIODS.items()}

    b = family_b(feats, targets, rows)
    pd.set_option("display.width", 220)
    print(f"B. extremes: {len(b)} tests, {int(b.fdr_keep.sum())} pass the 5% false discovery rate, "
          f"{int(b.confirmed.sum())} confirmed in 2019-2022")
    shown = b[b.fdr_keep].copy()
    shown["time"] = shown.minute.map(lambda m: f"{(570 + m) // 60:02d}:{(570 + m) % 60:02d}")
    print(shown[["feature", "target", "time", "t", "spread_bps", "t_confirm", "spread_bps_confirm", "confirmed"]]
          .sort_values("t", key=abs, ascending=False).round(2).to_string(index=False))

    preds, rules = family_c(feats, targets, rows, cost_bps)
    print(f"\nC. combined model, 1 MNQ at {ref:,.0f}, cost {cost_bps:.2f} bps per round trip")
    best, best_t = None, -math.inf
    for name, (pos, pnl) in rules.items():
        _, t_disc = daily_stats(pnl, rows["discovery"], notional)
        day_c, t_conf = daily_stats(pnl, rows["confirm"], notional)
        trades = np.abs(pos[rows["confirm"]]).sum(axis=1).mean()
        print(f"  {name}: trades/day {trades:.1f}, 2011-18 t {t_disc:+.2f} (in-sample), "
              f"2019-22 ${day_c.mean():+.2f}/day t {t_conf:+.2f}")
        if t_conf > best_t:
            best, best_t = name, t_conf
    if best_t >= 2:
        pos, pnl = rules[best]
        day_t, t_test = daily_stats(pnl, rows["test"], notional)
        years = pd.Series(day_t, index=meta.year.to_numpy()[rows["test"]]).groupby(level=0).sum().round(0)
        print(f"\nPicked {best} (2019-22 t {best_t:.2f}). FINAL TEST 2023 - Sep 2026: ${day_t.mean():+.2f}/day, "
              f"t {t_test:+.2f}, by year {years.astype(int).to_dict()}")
    else:
        print(f"\nNo rule reaches t >= 2 in 2019-2022 (best {best} at {best_t:.2f}): nothing goes to the final test.")


if __name__ == "__main__":
    main()
