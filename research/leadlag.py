"""Round sixty-nine: do other markets' recent moves predict the Nasdaq's next half hour? A broad scan, FDR-controlled.

    python research/leadlag.py <scratchpad>

The user asked to search for unknowns. Every earlier discovery round (six, seven) looked at the Nasdaq's own intraday
and overnight measurements, regimes, the calendar, the VIX and volume, and ES confirmation. Not yet scanned: intraday
CROSS-MARKET lead-lag, whether gold, silver, crude, the euro, the yen, the dollar index, the DAX, the Nikkei or the
S&P moving in the last minutes predicts where the Nasdaq goes next.

Data: HistData 1-minute bars (scratchpad/histdata_markets/<SYMBOL>/raw): XAUUSD, XAGUSD, WTIUSD (no files for
2024-01 to 2026-05), EURUSD, USDJPY, UDXUSD (dollar index), GRXEUR (DAX), JPXJPY (Nikkei); the S&P from spx1m.pkl.
ETXEUR (Euro Stoxx) only runs to 2019, so it has no out-of-sample years and is left out. Timestamps are New York
time (research/other_markets.py checked the 08:30 releases and the 10:30 oil report land on the right minute).
Target: the Nasdaq index (nsx1m_scaled.pkl, prices at today's level), then NQ futures (nq1m_scaled.pkl, 2015-2025).

Rules, all fixed before running:
  checks t = 10:00, 10:30, ..., 15:30 New York on Nasdaq sessions. A market's price at t is the close of the 1-minute
  bar ending at t (stale by more than 5 minutes: missing).
  features: the log return of each of the 9 markets over the last 5, 15, 30 and 60 minutes and since 09:30, and the
    Nasdaq-minus-S&P log return over the same 5 windows: 9 x 5 + 5 = 50 features.
  rule: at a check where |feature| is above the 70th percentile of its own |values| over the previous 252 sessions
    (past only), trade the Nasdaq in the direction of sign(feature) ("with"), or against it ("against"); enter at the
    open of the next minute, exit at the close 30 minutes after the check ("30m") or at the 15:59 close ("close").
    50 features x 2 directions x 2 exits = 200 rules.
  P/L per MNQ: direction x (exit - entry) x $2 - $1.24 fees - 2 ticks of slippage ($1.00).
  t-stat: on daily sums of a rule's P/L (trades in one day are not independent), over days with a trade.
Stages:
  1. Discovery 2011-2018: two-sided p-values from t, Benjamini-Hochberg at q = 0.05 across all 200 rules; a survivor
     must also have a positive mean.
  2. One look at 2019 - Sep 2026 (index): positive mean and t >= 2.0.
  3. NQ futures 2015 - Jul 2025: positive mean and t >= 1.5.
A rule passing all three is a real lead-lag edge; its value on one 50K Apex account would then be estimated.
"""
from __future__ import annotations

import glob
import sys
from math import erf, sqrt

import numpy as np
import pandas as pd

NY = "America/New_York"
OTHERS = {"gold": "XAUUSD", "silver": "XAGUSD", "crude": "WTIUSD", "euro": "EURUSD", "yen": "USDJPY",
          "dollar": "UDXUSD", "dax": "GRXEUR", "nikkei": "JPXJPY"}
WINDOWS = (5, 15, 30, 60, "open")
CHECKS = list(range(600, 931, 30))  # minutes after midnight: 10:00 .. 15:30
COST = 1.24 + 2 * 0.25 * 2.0  # $ per MNQ round trip: fees + a tick each way
PV = 2.0


def load_histdata(sp: str, symbol: str) -> pd.Series:
    frames = []
    for f in sorted(glob.glob(f"{sp}/histdata_markets/{symbol}/raw/DAT_ASCII_{symbol}_M1_*.csv")):
        df = pd.read_csv(f, sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
        frames.append(df)
    df = pd.concat(frames).drop_duplicates("ts").sort_values("ts").set_index("ts")
    df.index = df.index.tz_localize(NY, ambiguous="NaT", nonexistent="shift_forward")
    return df[~df.index.isna()]["close"].astype(float)


def sessions(target: pd.DataFrame) -> list:
    m = target.index
    return sorted(set(m[(m.hour == 9) & (m.minute == 30)].tz_localize(None).normalize()))


def grid_prices(close: pd.Series, days: list) -> np.ndarray:
    """Close of the bar ending at each minute 08:25..16:00 (bar start 08:24..15:59), ffill up to 5 minutes:
    array [day, minute offset], minute offset k means the price at 08:25 + k."""
    c = close.copy()
    c.index = c.index.tz_localize(None)
    c = c[~c.index.duplicated()]
    out = np.full((len(days), 456), np.nan)
    starts = pd.DatetimeIndex(days) + pd.Timedelta(minutes=8 * 60 + 24)
    for i, s in enumerate(starts):
        seg = c.loc[s - pd.Timedelta(minutes=5): s + pd.Timedelta(minutes=455)]
        if seg.empty:
            continue
        idx = pd.date_range(s - pd.Timedelta(minutes=5), s + pd.Timedelta(minutes=455), freq="1min")
        v = seg.reindex(idx).ffill(limit=5).to_numpy()[5:]
        out[i] = v
    return out


def at(minute_of_day: int) -> int:
    """Offset into grid_prices for the price at that time (the close of the bar ending then)."""
    return minute_of_day - (8 * 60 + 25)


def target_arrays(bars: pd.DataFrame, days: list):
    """Per day and check: entry (open of the bar starting at t), exit 30m (close of the bar ending t+30) and exit at
    the 15:59 close; and the Nasdaq's own price grid for the relative feature."""
    b = bars.copy()
    b.index = b.index.tz_localize(None)
    b = b[~b.index.duplicated()]
    o, c = b["open"], b["close"]
    entry = np.full((len(days), len(CHECKS)), np.nan)
    ex30 = entry.copy()
    exc = np.full(len(days), np.nan)
    for i, d in enumerate(days):
        for j, t in enumerate(CHECKS):
            te = d + pd.Timedelta(minutes=t)
            entry[i, j] = o.get(te, np.nan)
            ex30[i, j] = c.get(te + pd.Timedelta(minutes=29), np.nan)
        exc[i] = c.get(d + pd.Timedelta(minutes=959), np.nan)
    return entry, ex30, exc


def features(grids: dict, days: list) -> dict:
    """name -> array [day, check] of log returns."""
    out = {}
    for name, g in grids.items():
        lg = np.log(g)
        for w in WINDOWS:
            f = np.full((len(days), len(CHECKS)), np.nan)
            for j, t in enumerate(CHECKS):
                start = at(570) if w == "open" else at(t - w)
                f[:, j] = lg[:, at(t)] - lg[:, start]
            out[f"{name} {w}"] = f
    for w in WINDOWS:  # the Nasdaq's own move enters only relative to the S&P's
        out[f"nasdaq-sp {w}"] = out.pop(f"nasdaq {w}") - out[f"sp {w}"]
    return out


def thresholds(f: np.ndarray) -> np.ndarray:
    """70th percentile of |f| over the previous 252 sessions' checks (past only, including earlier checks today)."""
    flat = pd.Series(np.abs(f).ravel())
    q = flat.rolling(252 * len(CHECKS), min_periods=60 * len(CHECKS)).quantile(0.7).shift(1)
    return q.to_numpy().reshape(f.shape)


def tstat(daily: np.ndarray) -> float:
    if len(daily) < 30 or daily.std(ddof=1) == 0:
        return float("nan")
    return float(daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily)))


def pval(t: float) -> float:
    return float("nan") if np.isnan(t) else 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))


def rule_pnl(f, thr, entry, ex30, exc, direction, exit_kind):
    """P/L [day, check] and which checks traded (a signal, and both prices present)."""
    with np.errstate(invalid="ignore"):
        sig = np.nan_to_num(np.where(np.abs(f) > thr, np.sign(f), 0.0)) * direction
    exit_ = ex30 if exit_kind == "30m" else np.repeat(exc[:, None], len(CHECKS), axis=1)
    raw = sig * (exit_ - entry) * PV - np.abs(sig) * COST
    traded = (sig != 0) & ~np.isnan(raw)
    return np.where(traded, raw, 0.0), traded


def evaluate(feat, entry, ex30, exc, days, y0, y1, thr_cache):
    yrs = np.array([d.year for d in days])
    keep = (yrs >= y0) & (yrs <= y1)
    rows = []
    for name, f in feat.items():
        if name not in thr_cache:
            thr_cache[name] = thresholds(f)
        thr = thr_cache[name]
        for direction, dname in ((1.0, "with"), (-1.0, "against")):
            for exit_kind in ("30m", "close"):
                pnl, traded = rule_pnl(f, thr, entry, ex30, exc, direction, exit_kind)
                pnl, traded = pnl[keep], traded[keep]
                n_trades = int(traded.sum())
                daily = pnl.sum(axis=1)[traded.any(axis=1)]
                t = tstat(daily)
                rows.append({"rule": f"{name} {dname} {exit_kind}", "trades": n_trades,
                             "$/trade": pnl.sum() / max(n_trades, 1), "$/day traded": daily.mean() if len(daily) else 0,
                             "t": t, "p": pval(t)})
    return pd.DataFrame(rows)


def bh(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    n = len(p)
    order = np.argsort(p)
    passed = np.zeros(n, bool)
    ranked = p[order]
    ok = ranked <= q * np.arange(1, n + 1) / n
    if ok.any():
        k = np.max(np.nonzero(ok)[0])
        passed[order[: k + 1]] = True
    return passed


def build(sp: str, target_file: str, others: dict):
    target = pd.read_pickle(f"{sp}/{target_file}")
    days = sessions(target)
    entry, ex30, exc = target_arrays(target, days)
    grids = {name: grid_prices(s, days) for name, s in others.items()}
    grids["nasdaq"] = grid_prices(target["close"], days)
    return days, entry, ex30, exc, features(grids, days)


def main() -> None:
    sp = sys.argv[1]
    pd.set_option("display.width", 200)
    others = {name: load_histdata(sp, sym) for name, sym in OTHERS.items()}
    others["sp"] = pd.read_pickle(f"{sp}/spx1m.pkl")["close"]
    print("data:", {k: (str(v.index[0].date()), str(v.index[-1].date()), len(v)) for k, v in others.items()})

    days, entry, ex30, exc, feat = build(sp, "nsx1m_scaled.pkl", others)
    cache, cache_f = {}, {}
    disc = evaluate(feat, entry, ex30, exc, days, 2011, 2018, cache)
    disc["fdr"] = bh(disc.p.fillna(1.0).to_numpy()) & (disc["$/trade"] > 0)
    print(f"\nStage 1, 2011-2018: {len(disc)} rules; Benjamini-Hochberg q=0.05 survivors with a positive mean: "
          f"{int(disc.fdr.sum())}")
    print(disc.sort_values("t", ascending=False).head(15).round(3).to_string(index=False))
    surv = list(disc[disc.fdr].rule)
    if not surv:
        print("\nNo survivors: none.")
        return
    hold = evaluate(feat, entry, ex30, exc, days, 2019, 2026, cache).set_index("rule").loc[surv]
    hold["pass"] = (hold["$/trade"] > 0) & (hold.t >= 2.0)
    print("\nStage 2, 2019 - Sep 2026 (one look):")
    print(hold.round(3).to_string())
    surv2 = list(hold[hold["pass"]].index)
    if not surv2:
        print("\nNo rule survives 2019-2026: none.")
        return
    days_f, entry_f, ex30_f, exc_f, feat_f = build(sp, "nq1m_scaled.pkl", others)
    fut = evaluate(feat_f, entry_f, ex30_f, exc_f, days_f, 2015, 2025, cache_f).set_index("rule").loc[surv2]
    fut["pass"] = (fut["$/trade"] > 0) & (fut.t >= 1.5)
    print("\nStage 3, NQ futures 2015-2025:")
    print(fut.round(3).to_string())
    print("\nSurvivors of all three stages:", list(fut[fut["pass"]].index) or "none")


if __name__ == "__main__":
    main()
