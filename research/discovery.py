"""Search the data itself for intraday patterns in the Nasdaq-100, with guards against fooling ourselves.

    python research/discovery.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running:
  * Decision times: every half hour from 10:00 to 15:30 New York time (12 a day).
  * Targets: the return from the decision time over the next 30 minutes, the next 60 minutes, and to the
    16:00 close, entering at the next minute's open.
  * Candidate patterns: the FEATURES listed below, all computed from data up to the decision time.
  * Periods: discovery 2011-2018, confirmation 2019-2022, final test 2023 - Sep 2026 (not touched here).
  * Discovery: Spearman rank correlation of each (feature, time, target) across days. Keep the ones that
    pass a Benjamini-Hochberg false discovery rate of 5% over all tests run.
  * Confirmation: a discovery survives if, in 2019-2022, its correlation has the same sign with a one-sided
    p-value below 5%.
  * The constant feature tests whether the average return itself is non-zero (a time-of-day drift).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

CHECKS = list(range(30, 361, 30))  # minutes after 09:30: 10:00 .. 15:30
HORIZONS = {"30m": 30, "60m": 60, "close": None}
PERIODS = {"discovery": (2011, 2019), "confirm": (2019, 2023), "test": (2023, 2100)}
FDR = 0.05
LOOKBACK = 20  # sessions for "normal" levels


def session_table(raw: pd.DataFrame, days: L.Days) -> pd.DataFrame:
    """Per-session values that don't depend on the decision time."""
    idx = raw.index
    trade_date = (idx + pd.Timedelta(hours=6)).date  # CME day: 18:00 starts the next date
    hhmm = idx.hour * 100 + idx.minute
    on = raw[(hhmm >= 1800) | (hhmm < 930)]
    on_g = on.groupby(trade_date[(hhmm >= 1800) | (hhmm < 930)])
    on_hi, on_lo = on_g.high.max(), on_g.low.min()
    n = len(days.dates)
    rth_hi = np.nanmax(days.h, axis=1)
    rth_lo = np.nanmin(days.l, axis=1)
    last_close = days.cf[:, -1]
    t = pd.DataFrame(index=pd.Index(days.dates, name="day"))
    t["open"] = days.o[:, 0]
    t["prev_close"] = days.prev_close
    prev = np.r_[np.nan, np.arange(n - 1)]  # previous session row (half days count)
    valid_prev = ~np.isnan(days.prev_close)
    pi = np.where(valid_prev, prev, np.nan)

    def lag(a, k=1):
        out = np.full(n, np.nan)
        out[k:] = a[:-k]
        return np.where(valid_prev, out, np.nan)

    t["prev_open"], t["prev_high"], t["prev_low"] = lag(days.o[:, 0]), lag(rth_hi), lag(rth_lo)
    t["close_5"], t["close_20"] = lag(last_close, 5), lag(last_close, 20)
    t["on_high"] = pd.Series(on_hi).reindex(t.index).to_numpy()
    t["on_low"] = pd.Series(on_lo).reindex(t.index).to_numpy()
    daily_ret = pd.Series(last_close / lag(last_close) - 1, index=t.index)
    t["vol20"] = daily_ret.rolling(LOOKBACK, min_periods=LOOKBACK).std().shift(1).to_numpy()
    d = pd.to_datetime(pd.Series(t.index))
    t["dow"] = d.dt.dayofweek.to_numpy()
    month = d.dt.to_period("M")
    rank_in_month = d.groupby(month).cumcount().to_numpy()
    left_in_month = (d.groupby(month).cumcount(ascending=False)).to_numpy()
    t["turn_of_month"] = ((rank_in_month <= 2) | (left_in_month == 0)).astype(float)
    third_friday = (d.dt.dayofweek == 4) & (d.dt.day >= 15) & (d.dt.day <= 21)
    t["opex_day"] = third_friday.astype(float).to_numpy()
    week = d.dt.to_period("W")
    t["opex_week"] = third_friday.groupby(week).transform("max").astype(float).to_numpy()
    del pi
    return t


def build(raw: pd.DataFrame) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], pd.DataFrame]:
    days = L.Days(raw)
    st = session_table(raw, days)
    o, h, l, cf = days.o, days.h, days.l, days.cf
    n, T = len(days.dates), len(CHECKS)
    O = o[:, 0][:, None]
    logc = np.log(cf)
    r1 = np.diff(logc, axis=1, prepend=np.log(o[:, :1]))  # 1-minute log returns
    rv_cum = np.nancumsum(r1**2, axis=1)
    hi_cum = np.fmax.accumulate(np.where(np.isnan(h), -np.inf, h), axis=1)
    lo_cum = np.fmin.accumulate(np.where(np.isnan(l), np.inf, l), axis=1)
    typical = (h + l + cf) / 3
    twap = np.nancumsum(typical, axis=1) / np.cumsum(~np.isnan(typical), axis=1)
    up = (r1 > 0).astype(float)

    full = np.flatnonzero(days.full)
    ms = np.array(CHECKS)
    P = cf[:, ms - 1]
    feats: dict[str, np.ndarray] = {}
    feats["constant"] = np.ones((n, T))
    feats["move_from_open"] = P / O - 1
    feats["gap"] = np.repeat((st.open / st.prev_close - 1).to_numpy()[:, None], T, axis=1)
    feats["prev_day_move"] = np.repeat(((st.prev_close / st.prev_open) - 1).to_numpy()[:, None], T, axis=1)
    ref30 = np.where(ms - 31 >= 0, cf[:, np.maximum(ms - 31, 0)], O)
    feats["last_30m_move"] = P / ref30 - 1
    feats["last_5m_move"] = P / cf[:, ms - 6] - 1
    hi_t, lo_t = hi_cum[:, ms - 1], lo_cum[:, ms - 1]
    feats["position_in_day_range"] = (P - lo_t) / (hi_t - lo_t)
    feats["distance_from_twap"] = P / twap[:, ms - 1] - 1
    feats["first_30m_move"] = np.repeat((cf[:, 29] / o[:, 0] - 1)[:, None], T, axis=1)
    feats["up_minutes_last_30"] = np.stack([np.nanmean(up[:, max(m - 30, 0) : m], axis=1) for m in ms], axis=1)
    # "normal" levels at the same time of day over the previous LOOKBACK full sessions
    rv_t, rng_t = rv_cum[:, ms - 1], (hi_t - lo_t) / O[:, 0][:, None]
    mv_t = np.abs(P / O - 1)
    avg_rv, avg_rng, avg_mv = (np.full((n, T), np.nan) for _ in range(3))
    for j in range(LOOKBACK, len(full)):
        prev = full[j - LOOKBACK : j]
        avg_rv[full[j]] = np.nanmean(rv_t[prev], axis=0)
        avg_rng[full[j]] = np.nanmean(rng_t[prev], axis=0)
        avg_mv[full[j]] = np.nanmean(mv_t[prev], axis=0)
    feats["volatility_vs_normal"] = rv_t / avg_rv
    feats["range_vs_normal"] = rng_t / avg_rng
    feats["move_in_noise_units"] = (P / O - 1) / avg_mv
    on_rng = (st.on_high - st.on_low).to_numpy()
    feats["overnight_range"] = np.repeat((on_rng / st.prev_close.to_numpy())[:, None], T, axis=1)
    feats["open_in_overnight_range"] = np.repeat(((st.open - st.on_low).to_numpy() / on_rng)[:, None], T, axis=1)
    feats["last_week_move"] = np.repeat((st.prev_close / st.close_5 - 1).to_numpy()[:, None], T, axis=1)
    feats["last_month_move"] = np.repeat((st.prev_close / st.close_20 - 1).to_numpy()[:, None], T, axis=1)
    feats["vs_prev_high"] = P / st.prev_high.to_numpy()[:, None] - 1
    feats["vs_prev_low"] = P / st.prev_low.to_numpy()[:, None] - 1
    prev_rng = (st.prev_high - st.prev_low).to_numpy()
    feats["prev_day_range"] = np.repeat((prev_rng / st.prev_close.to_numpy())[:, None], T, axis=1)
    prev_close_pos = (st.prev_close - st.prev_low).to_numpy() / prev_rng
    feats["prev_close_in_prev_range"] = np.repeat(prev_close_pos[:, None], T, axis=1)
    pc = st.prev_close.to_numpy()[:, None]
    feats["gap_filled_yet"] = ((lo_t <= pc) & (hi_t >= pc)).astype(float)
    feats["volatility_20d"] = np.repeat(st.vol20.to_numpy()[:, None], T, axis=1)
    for k, name in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday"]):
        feats[name] = np.repeat((st.dow.to_numpy() == k).astype(float)[:, None], T, axis=1)
    for name in ("turn_of_month", "opex_day", "opex_week"):
        feats[name] = np.repeat(st[name].to_numpy()[:, None], T, axis=1)

    entry = np.where(np.isnan(o[:, ms]), cf[:, ms - 1], o[:, ms])
    targets = {}
    close = cf[:, -1][:, None]
    for name, hz in HORIZONS.items():
        if hz is None:
            ex = np.repeat(close, T, axis=1)
        else:
            mm = np.minimum(ms + hz, L.MINUTES - 1)
            at = np.where(np.isnan(o[:, mm]), cf[:, mm - 1], o[:, mm])  # open of the exit minute
            ex = np.where((ms + hz)[None, :] >= L.MINUTES, close, at)
        targets[name] = ex / entry - 1

    # usable sessions: full sessions with few missing minutes and the look-back levels available
    missing = days.missing.sum(axis=1)
    ok = days.full & (missing <= 5) & ~np.isnan(avg_rv[:, 0]) & ~np.isnan(days.prev_close)
    meta = pd.DataFrame({"day": days.dates, "year": [d.year for d in days.dates], "ok": ok})
    return feats, targets, meta


Z95 = 1.6448536269514722  # one-sided 5% normal quantile


def two_sided_p(t: np.ndarray) -> np.ndarray:
    return np.array([math.erfc(abs(v) / math.sqrt(2)) for v in t])


def spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, int]:
    """Rank correlation (average ranks for ties)."""
    m = ~np.isnan(x) & ~np.isnan(y) & np.isfinite(x)
    if m.sum() < 50 or np.nanstd(x[m]) == 0:
        return math.nan, int(m.sum())
    rx = pd.Series(x[m]).rank().to_numpy()
    ry = pd.Series(y[m]).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1]), int(m.sum())


def test_all(feats, targets, rows) -> pd.DataFrame:
    out = []
    for fname, F in feats.items():
        for tname, Y in targets.items():
            for k, m in enumerate(CHECKS):
                if tname != "close" and m + HORIZONS[tname] > L.MINUTES:
                    continue
                y = Y[rows, k]
                if fname == "constant":
                    yy = y[~np.isnan(y)]
                    tstat = yy.mean() / yy.std(ddof=1) * math.sqrt(len(yy))
                    out.append((fname, tname, m, math.nan, tstat, len(yy), yy.mean() * 1e4))
                    continue
                rho, n = spearman(F[rows, k], y)
                tstat = rho * math.sqrt((n - 2) / max(1 - rho * rho, 1e-12)) if not math.isnan(rho) else math.nan
                out.append((fname, tname, m, rho, tstat, n, math.nan))
    df = pd.DataFrame(out, columns=["feature", "target", "minute", "rho", "t", "n", "mean_bps"])
    df["time"] = df.minute.map(lambda m: f"{(570 + m) // 60:02d}:{(570 + m) % 60:02d}")
    df["p"] = two_sided_p(df.t.to_numpy())
    return df


def bh(p: pd.Series, q: float) -> pd.Series:
    order = p.sort_values()
    k = np.arange(1, len(order) + 1)
    passed = order.to_numpy() <= q * k / len(order)
    cutoff = k[passed].max() if passed.any() else 0
    keep = pd.Series(False, index=p.index)
    keep[order.index[:cutoff]] = True
    return keep


def main() -> None:
    raw = load_histdata(sys.argv[1])
    feats, targets, meta = build(raw)
    rows = {name: np.flatnonzero(meta.ok & (meta.year >= a) & (meta.year < b)) for name, (a, b) in PERIODS.items()}
    print({k: len(v) for k, v in rows.items()}, "sessions per period")
    disc = test_all(feats, targets, rows["discovery"]).dropna(subset=["t"])
    disc["fdr_keep"] = bh(disc.p, FDR)
    print(f"{len(disc)} tests in discovery; {disc.fdr_keep.sum()} pass the 5% false discovery rate")
    conf = test_all(feats, targets, rows["confirm"]).set_index(["feature", "target", "minute"])
    keep = disc[disc.fdr_keep].set_index(["feature", "target", "minute"])
    keep = keep.join(conf[["t", "rho", "mean_bps"]], rsuffix="_confirm")
    keep["confirmed"] = (np.sign(keep.t) == np.sign(keep.t_confirm)) & (keep.t_confirm.abs() >= Z95)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 400)
    cols = ["time", "rho", "t", "mean_bps", "rho_confirm", "t_confirm", "mean_bps_confirm", "confirmed"]
    print(keep[cols].sort_values("t", key=abs, ascending=False).round(3).to_string())
    print(f"\nConfirmed in 2019-2022: {int(keep.confirmed.sum())} of {len(keep)}")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if out:
        keep.reset_index().to_csv(out, index=False)


if __name__ == "__main__":
    main()
