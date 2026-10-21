"""Minute equity of a portfolio of trade lists on the full electronic session, and its intraday maximum drawdown.

    python research/portfolio_dd.py <ratio_study folder> <rth bars pkl> <roll-adjusted pkl> <first year> <last year>
                                    <slippage> <B config name> <FOMC contracts>

The B (+ breakout) trades come from research/ratio_study.py, priced on the rescaled NQ series. The pre-FOMC trades
are mnqbot/fomc.py's rule (MnqFomcDrift.cs), on each announcement's slice of the roll-adjusted series in its
continuous units times the exit day's month factor, so no month-rescaling or roll jump enters a trade that holds
overnight. Each minute, every open position is marked at the minute's worst price (low for a long, high for a short);
the drawdown is measured from the highest equity before that minute.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FEE, TICK, PV = 0.95, 0.25, 2.0


def fomc_trades(adj: pd.DataFrame, slip: int, qty: int, stop_pct: float = 4.0) -> pd.DataFrame:
    """mnqbot/fomc.py's rule (the NinjaScript's) on each announcement's own slice of the roll-adjusted series, priced
    in its continuous units times the exit day's month factor and rounded to the tick."""
    from mnqbot.fomc import trades
    t = adj.index
    day = t.tz_localize(None).normalize()
    fomc = pd.to_datetime(pd.read_csv(ROOT / "research" / "fomc_dates.csv").date)
    rows = []
    for f in fomc:
        on = np.flatnonzero(day == f)
        if not len(on):
            continue
        lo = int(np.searchsorted(t, t[on[0]] - pd.Timedelta(days=5)))
        sl = adj.iloc[lo:on[-1] + 1]
        sc = adj.scale.iloc[on[-1]]
        px = (sl[["open", "high", "low", "close"]].div(sl.scale, axis=0) * sc / TICK).round() * TICK
        for r in trades(px, {f.strftime("%Y-%m-%d")}, qty=qty, slip_ticks=slip, stop_pct=stop_pct):
            path = px.iloc[r["eb"]:r["xb"]]
            rows.append({"t0": px.index[r["eb"]], "t1": px.index[r["xb"]], "d": 1, "q": qty, "en": r["en"],
                         "ex": r["ex"], "pnl": r["pnl"], "why": r["why"], "low_path": path.low.to_numpy(),
                         "high_path": path.high.to_numpy()})
    return pd.DataFrame(rows)


def minute_equity(timeline: pd.DatetimeIndex, legs: list[pd.DataFrame]) -> tuple[np.ndarray, np.ndarray]:
    """(equity at each minute's worst price, closed equity), on the timeline."""
    n = len(timeline)
    closed = np.zeros(n)
    worst = np.zeros(n)
    pos = {t: i for i, t in enumerate(timeline)}
    for leg in legs:
        for r in leg.itertuples():
            i0, i1 = pos[r.t0], pos[r.t1]
            closed[i1:] += r.pnl
            path = r.low_path if r.d > 0 else r.high_path
            m = min(len(path), i1 - i0)
            worst[i0:i0 + m] += r.d * (path[:m] - r.en) * PV * r.q
    return closed + worst, closed


def bw_leg(folder: Path, name: str, slip: int, rth: pd.DataFrame, years) -> pd.DataFrame:
    tr = pd.read_csv(folder / f"trades_nq_{name.replace(' ', '_')}_{slip}t.csv", parse_dates=["day"])
    tr = tr[tr.day.dt.year.isin(years)]
    lo, hi, t = rth.low.to_numpy(float), rth.high.to_numpy(float), rth.index
    rows = []
    for r in tr.itertuples():
        rows.append({"t0": t[r.eb], "t1": t[r.xb], "d": r.d, "q": r.q, "en": r.en, "ex": r.ex, "pnl": r.pnl,
                     "low_path": lo[r.eb:r.xb], "high_path": hi[r.eb:r.xb]})
    return pd.DataFrame(rows)


def main() -> None:
    folder, rth, adj = Path(sys.argv[1]), pd.read_pickle(sys.argv[2]), pd.read_pickle(sys.argv[3])
    y0, y1, slip, name, q = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7], int(sys.argv[8])
    years = range(y0, y1 + 1)
    adj = adj[(adj.index.year >= y0 - 1) & (adj.index.year <= y1)]
    legs = [bw_leg(folder, name, slip, rth, years)]
    if q:
        f = fomc_trades(adj, slip, q)
        legs.append(f[f.t1.dt.year.isin(years)])
    timeline = adj.index.union(rth.index)
    timeline = timeline[(timeline.year >= y0) & (timeline.year <= y1)]
    eq, closed = minute_equity(timeline, legs)
    peak = np.concatenate([[0.0], np.maximum.accumulate(np.maximum(eq, 0.0))[:-1]])
    dd = float(np.max(peak - eq))
    net = sum(leg.pnl.sum() for leg in legs)
    gp = sum(leg.pnl[leg.pnl > 0].sum() for leg in legs)
    print(f"{name} + {q} MNQ pre-FOMC, {y0}-{y1}, {slip} ticks: net {net:.0f}, gross profit {gp:.0f}, "
          f"intraday DD {dd:.0f}, net / DD {net / dd:.2f}, gross / DD {gp / dd:.1f}")
    if q:
        f = legs[1]
        mae = [(min(r.low_path) - r.en) / r.en * 100 for r in f.itertuples()]
        stops = int((f.why == "Stop loss").sum())
        print(f"   FOMC trades {len(f)}, net {f.pnl.sum():.0f}, worst {f.pnl.min():.0f}, stops {stops}, "
              f"largest adverse excursion {min(mae):.2f}% of price")


if __name__ == "__main__":
    main()
