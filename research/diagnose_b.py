"""Diagnose frozen B (momentum only) on DEVELOPMENT data only (docs/DEVELOPMENT.md step 2).

    python research/diagnose_b.py <sim.dll> <nq1m_scaled.pkl>

B on the stand-in, NQ 2015-03 to 2020-12 (rescaled), $0.95 a side, 1 tick. Per trade: its check time, its number in
the day, exit reason, gross and net, the best (MFE) and worst (MAE) points while open (from the bars), whether the
lock armed (MFE >= 25 points). Questions: are losses concentrated in sideways days or repeated entries (entry
quality); do losers recover after the stop (stop placement); how much open profit is given back (exits); how much of
the gross edge do costs take.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402

dll, data = sys.argv[1], sys.argv[2]
bars = K.rth(pd.read_pickle(data))
m = bars.index.tz_convert(K.NY)
bars = bars[(m >= pd.Timestamp("2015-03-01", tz=K.NY)) & (m < pd.Timestamp("2021-01-01", tz=K.NY))]
m = bars.index.tz_convert(K.NY)
csv = Path(tempfile.mkdtemp()) / "b.csv"
K.write_bars(bars, csv)
skip = K.DEFAULT_SKIP + "," + ",".join(K.incomplete_sessions(bars))
tr = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=1, SimCommissionPerSide=0.95, SkipDates=skip)
h, lo, c = (bars[x].to_numpy(float) for x in ("high", "low", "close"))
day = m.normalize()
rows = []
for r in tr.itertuples():
    seg = slice(r.eb, r.xb + 1)
    mfe = (h[seg].max() - r.en) if r.d > 0 else (r.en - lo[seg].min())
    mae = (r.en - lo[seg].min()) if r.d > 0 else (h[seg].max() - r.en)
    # after the exit, to the 16:00 close: did price go on to the take-profit side (would a wider stop have paid)?
    end = np.flatnonzero(day == day[r.xb])[-1]
    after = slice(r.xb, end + 1)
    later_best = ((h[after].max() - r.en) if r.d > 0 else (r.en - lo[after].min())) if r.xb < end else np.nan
    close_move = r.d * (c[end] - r.en)
    rows.append({"day": day[r.eb], "t": m[r.eb - 1].strftime("%H:%M") if r.eb > 0 else "", "d": r.d,
                 "why": r.why, "net": r.pnl, "gross": r.pnl + 2 * 0.95 * r.q, "mfe": mfe, "mae": mae,
                 "later_best": later_best, "close_move": close_move})
t = pd.DataFrame(rows)
t["n_in_day"] = t.groupby("day").cumcount() + 1
cost = 2 * 0.95 * 4 + 2 * 0.25 * 2 * 4  # commission + a tick each side, 4 MNQ
print(f"trades {len(t)}, net ${t.net.sum():,.0f}, gross (after slippage, before commission) ${t.gross.sum():,.0f}, "
      f"net ${t.net.mean():.1f}/trade; costs about ${cost:.1f}/trade (commission ${2*0.95*4:.1f} + 1 tick a side "
      f"${2*0.25*2*4:.1f}) = {100*cost*len(t)/(t.net.sum()+cost*len(t)):.0f}% of the edge before costs")
print("\n== By exit reason (net)")
print(t.groupby("why").agg(n=("net", "size"), net=("net", "sum"), avg=("net", "mean"), mfe=("mfe", "mean")).round(1))
print("\n== By trade number in the day")
print(t.groupby(t.n_in_day.clip(upper=3)).agg(n=("net", "size"), net=("net", "sum"), avg=("net", "mean"),
                                            win=("net", lambda s: 100 * (s > 0).mean())).round(1))
print("\n== By check time (entry signal)")
print(t.groupby("t").agg(n=("net", "size"), net=("net", "sum"), avg=("net", "mean")).round(1).T.to_string())
print("\n== Giveback: trades whose open profit reached 25+ points (the lock armed)")
lk = t[t.mfe >= 25]
print(f"{len(lk)} trades; net ${lk.net.sum():,.0f}; average best {lk.mfe.mean():.1f} pts, average kept "
      f"{(lk.gross / 8).mean():.1f} pts; exits {lk.why.value_counts().to_dict()}")
for lo_, hi_ in ((25, 40), (40, 60), (60, 1e9)):
    s = lk[(lk.mfe >= lo_) & (lk.mfe < hi_)]
    print(f"  best {lo_}-{hi_} pts: {len(s)} trades, avg kept {(s.gross / 8).mean():.1f} pts "
          f"of avg best {s.mfe.mean():.1f}")
print("\n== Stops: losers")
ls = t[t.net < 0]
print(f"{len(ls)} losers, net ${ls.net.sum():,.0f}; average MAE {ls.mae.mean():.1f} pts; later in the day price went "
      f"25+ pts their way after the stop: {(ls.later_best >= 25).sum()} ({100*(ls.later_best >= 25).mean():.0f}%); "
      f"the 16:00 close was on their side of the entry: {(ls.close_move > 0).sum()} "
      f"({100*(ls.close_move > 0).mean():.0f}%)")
print("\n== Sideways days: B's day result against the day's directional efficiency (|close-open| / range, 09:30-16:00)")
o = bars.open.groupby(day).first()
cl = bars.close.groupby(day).last()
rng = bars.high.groupby(day).max() - bars.low.groupby(day).min()
eff = ((cl - o).abs() / rng).rename("eff")
dd = t.groupby("day").agg(net=("net", "sum"), n=("net", "size")).join(eff)
dd["eff_q"] = pd.qcut(dd.eff, 4, labels=["most sideways", "q2", "q3", "most directional"])
print(dd.groupby("eff_q", observed=True).agg(days=("net", "size"), trades=("n", "sum"), net=("net", "sum"),
                                              avg_day=("net", "mean")).round(1))
print("(the day's efficiency is known only at the close: a description of where losses fall, not a usable filter)")
yrange = rng.shift(1)
dd = dd.join((rng / rng.rolling(20).mean().shift(1)).rename("range_vs_20d"))
