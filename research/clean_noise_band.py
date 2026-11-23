# ruff: noqa: E501, B023
"""The user's "Clean Noise-Band Momentum (Prop Version)" spec (2026-11-23), coded as written, against Funded growth.

5-minute regular-hours bars (09:30-16:00 New York, the bar's start), 1 contract:
  * sigma at each half-hour check t (10:00 ... 15:00): the mean over the last 14 complete sessions of |close at t / the
    09:30 open - 1|; upper = max(today's open, the prior close) x (1 + sigma), lower = min(...) x (1 - sigma);
  * at a check's close, flat: long if the close > upper and > the session VWAP (and, with `trend`, > the 20-session
    average of closes); short mirrored; filled at the next bar's open + 1 tick; one position at a time, more than one a
    day allowed, no new entries after the 15:00 check;
  * the trailing stop: the band on the trade's side (long: upper; short: lower), or with `vwap_stop` the tighter of the
    band and VWAP, set at each check (from the entry check on), resting between checks; a stop fill has `stop_slip`
    ticks of slippage (at the open when it gaps through);
  * a hard stop `hard` $ a contract from the fill (same slippage); out at the 15:55 bar's close (1 tick);
  * $0.62 a side.
The account test: research/orb_every_day.py's (fresh 50K starts every quarter, 12 months, the $2,000 trailing floor).

    python research/clean_noise_band.py <nq1m_scaled.pkl> <es_continuous_1m.parquet> <MNQ 12-26 NinjaTrader export> <out.csv>
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd
from orb_every_day import FEE, NY, SPEC, account_test

CHECKS = list(range(600, 901, 30))  # 10:00 ... 15:00 (minute of the check bar's close)


def five_min(df: pd.DataFrame) -> pd.DataFrame:
    t = df.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    df = df[(m >= 570) & (m < 960)]
    return df.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def days_of(b: pd.DataFrame) -> list:
    t = b.index.tz_convert(NY)
    out = []
    for d, g in b.groupby(t.date):
        if len(g) < 76:
            continue
        mm = (g.index.tz_convert(NY).hour * 60 + g.index.tz_convert(NY).minute).to_numpy()
        out.append((d, mm, *(g[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))))
    return out


def simulate(days: list, sym: str, vwap_entry: bool, trend: bool, vwap_stop: bool, hard: float, stop_slip: int):
    tick, pv = SPEC[sym]
    hist: list[dict] = []  # per past session: {check minute: |close/open - 1|}
    closes: list[float] = []
    trades = []
    for d, mm, o, h, lo, c, v in days:
        moves = {}
        if len(hist) >= 14 and closes:
            sig = {t: np.mean([x[t] for x in hist[-14:] if t in x]) for t in CHECKS}
            prev = closes[-1]
            sma = np.mean(closes[-20:]) if len(closes) >= 20 else np.nan
            typ = (h + lo + c) / 3
            cum_v = np.cumsum(v)
            vwap = np.where(cum_v > 0, np.cumsum(typ * v) / np.maximum(cum_v, 1e-9), np.nan)
            pos, entry, stop, hard_px = 0, 0.0, np.nan, np.nan
            pending = 0
            for i in range(len(o)):
                end = mm[i] + 5  # this bar closes at `end`
                if pending and pos == 0:  # the entry at this bar's open
                    pos, entry = pending, o[i] + pending * tick
                    hard_px = entry - pos * hard / pv
                    stop = stop_next
                    pending = 0
                if pos != 0:  # the resting stops
                    lvl = max(stop, hard_px) if pos > 0 else min(stop, hard_px)
                    if (pos > 0 and lo[i] <= lvl) or (pos < 0 and h[i] >= lvl):
                        px = (min(o[i], lvl) if pos > 0 else max(o[i], lvl)) - pos * stop_slip * tick
                        trades.append((d, pos, (px - entry) * pos * pv - 2 * FEE, "stop" if lvl == stop else "hard"))
                        pos = 0
                if end in sig and not np.isnan(sig[end]):
                    s = sig[end]
                    up = max(o[0], prev) * (1 + s)
                    dn = min(o[0], prev) * (1 - s)
                    band_l, band_s = up, dn
                    if vwap_stop and not np.isnan(vwap[i]):
                        band_l, band_s = max(up, vwap[i]), min(dn, vwap[i])
                    if pos > 0:
                        stop = band_l
                    elif pos < 0:
                        stop = band_s
                    elif end <= 900:
                        want = 1 if c[i] > up else -1 if c[i] < dn else 0
                        if want and vwap_entry and not np.isnan(vwap[i]) and want * (c[i] - vwap[i]) <= 0:
                            want = 0
                        if want and trend and not np.isnan(sma) and want * (c[i] - sma) <= 0:
                            want = 0
                        if want:
                            pending = want
                            stop_next = band_l if want > 0 else band_s
                if mm[i] >= 955 and pos != 0:  # out at the 15:55 bar's close
                    px = c[i] - pos * tick
                    trades.append((d, pos, (px - entry) * pos * pv - 2 * FEE, "15:55"))
                    pos = 0
        for i in range(len(o)):
            end = mm[i] + 5
            if end in CHECKS:
                moves[end] = abs(c[i] / o[0] - 1)
        hist.append(moves)
        closes.append(c[-1])
    return trades


def report(name: str, days: list, sym: str, rule: tuple) -> dict:
    t = pd.DataFrame(simulate(days, sym, *rule), columns=["d", "side", "usd", "why"])
    daily = t.groupby("d").usd.sum().reindex([x[0] for x in days], fill_value=0.0)
    eq = daily.cumsum()
    yr = t.groupby(pd.to_datetime(t.d).dt.year).usd.sum()
    return {"set": name, "vwap_entry": rule[0], "trend20": rule[1], "vwap_stop": rule[2], "hard": rule[3],
            "stop_slip": rule[4], "trades": len(t), "win": round(float((t.usd > 0).mean()), 3),
            "net": round(float(t.usd.sum())), "per_trade": round(float(t.usd.mean()), 2),
            "pf": round(float(t.usd[t.usd > 0].sum() / max(1e-9, -t.usd[t.usd < 0].sum())), 2),
            "dd": round(float((eq.cummax().clip(lower=0) - eq).max())), "worst_day": round(float(daily.min())),
            "yrs_up": f"{(yr > 0).sum()}/{len(yr)}", **(account_test(daily) if name.startswith("NQ") else {})}


def main() -> None:
    import mnq_bars as M
    nq = pd.read_pickle(sys.argv[1])
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)]
    es = pd.read_parquet(sys.argv[2])[["open", "high", "low", "close", "volume"]]
    es.index = es.index.tz_convert(NY)
    mnq = M.load(sys.argv[3])
    sets = {"NQ 2015-25 (MNQ)": (days_of(five_min(nq)), "MNQ"), "ES 2020-24 (MES)": (days_of(five_min(es)), "MES"),
            "MNQ Sep-Nov 2026 (NinjaTrader export)": (days_of(five_min(mnq)), "MNQ")}
    rows = []
    for (vwe, tr, vws, hard, sl) in itertools.product((True, False), (False, True), (False, True), (150.0, 250.0), (2,)):
        for name, (days, sym) in sets.items():
            rows.append(report(name, days, sym, (vwe, tr, vws, hard, sl)))
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[4], index=False)


if __name__ == "__main__":
    main()
