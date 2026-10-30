"""Score any trade log honestly against the user's targets: an ONYX "paper model trade book", a TradingView "List of
trades" export or a NinjaTrader trade export, saved as CSV.

Columns are found by name, case-insensitively:
- a P/L in dollars ("profit", "p/l", "pnl", "net profit"); or
- points ("points"), turned into MNQ dollars at $2 a point.

When only points are given, $1.24 of fees and a tick of slippage a side ($1.00) are taken off each trade, since model
points carry no costs. A time column ("time", "date", "entry time", "exit time") orders the trades and splits them
into halves: a filter or change is worth trusting only if it holds in both.

    python research/score_trades.py <trades.csv> [contracts, default 1]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

TARGETS = {"net $": 75000.0, "net win %": 80.0, "profit factor": 2.0, "max drawdown $ (under)": 4000.0}
COST_PER_MNQ = 1.24 + 1.00


def find(cols: list[str], *names: str) -> str | None:
    low = {c.lower().strip(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    for n in names:
        for k, c in low.items():
            if n in k:
                return c
    return None


def stats(p: np.ndarray) -> dict:
    if len(p) == 0:
        return {"trades": 0}
    e = np.r_[0.0, np.cumsum(p)]
    w, l_ = p[p > 0].sum(), -p[p <= 0].sum()
    sd = p.std(ddof=1) if len(p) > 1 else 0.0
    return {"trades": len(p), "net $": round(float(p.sum()), 2), "net $/trade": round(float(p.mean()), 2),
            "t": round(float(p.mean() / (sd / np.sqrt(len(p)))), 2) if sd else 0.0,
            "net win %": round(100 * float((p > 0).mean()), 1),
            "profit factor": round(float(w / l_), 3) if l_ > 0 else float("inf"),
            "max drawdown $": round(float((np.maximum.accumulate(e) - e).max()), 2)}


def main() -> None:
    df = pd.read_csv(sys.argv[1])
    qty = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    cols = list(df.columns)
    tcol = find(cols, "exit time", "entry time", "date/time", "time", "date")
    if tcol:
        df = df.assign(_t=pd.to_datetime(df[tcol], errors="coerce", format="mixed")).sort_values("_t")
    usd = find(cols, "net profit", "profit", "p/l", "pnl")
    pts = find(cols, "points", "pts")
    if usd is not None:
        p = pd.to_numeric(df[usd].astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce").dropna()
        p = p.to_numpy() * qty
        how = f"dollars from '{usd}' x {qty:g}"
    elif pts is not None:
        x = pd.to_numeric(df[pts].astype(str).str.replace(r"[,\s+]", "", regex=True), errors="coerce").dropna()
        p = (x.to_numpy() * 2.0 - COST_PER_MNQ) * qty
        how = f"points from '{pts}' at $2 a point, less ${COST_PER_MNQ:.2f} costs, x {qty:g} MNQ"
    else:
        raise SystemExit(f"no P/L or points column in {cols}")
    s = stats(p)
    print(f"{sys.argv[1]}: {how}")
    for k, v in s.items():
        print(f"  {k:16} {v}")
    print("  targets:")
    for k, v in TARGETS.items():
        key = k.replace(" (under)", "")
        got = s.get(key)
        ok = got is not None and (got < v if "under" in k else got >= v)
        print(f"    {k:26} {v:>10}  {'PASS' if ok else 'fail'}")
    if len(p) >= 20:
        h = len(p) // 2
        a, b = stats(p[:h]), stats(p[h:])
        print(f"  first half : {a['trades']} trades, net ${a['net $']}, PF {a['profit factor']}, win {a['net win %']}%")
        print(f"  second half: {b['trades']} trades, net ${b['net $']}, PF {b['profit factor']}, win {b['net win %']}%")
    lo = 1.96 * np.sqrt(max(1e-9, (p > 0).mean() * (1 - (p > 0).mean())) / max(1, len(p)))
    print(f"  95% range of the true win rate: {100 * max(0, (p > 0).mean() - lo):.0f}-"
          f"{100 * min(1, (p > 0).mean() + lo):.0f}%")


if __name__ == "__main__":
    main()
