"""Two more families (docs/RESULTS.md, after v3.6), on raw NQ futures 1-minute bars 2015-2025 with the overnight
session (roll weeks skipped), 5-minute bars, 1 MNQ, $0.62 a side, a tick of slippage on market and stop fills:

- "onbreak": the overnight range (18:00-09:30). After 09:30, the first 5-minute close above the overnight high buys at
  the next bar's open (below the low sells, when "both"); the stop at the overnight range's middle or k x the range
  from the entry, whichever is closer; a target r x the risk; out at the time exit. Entries until 12:00, one a day.
- "tom": the turn of the month. Long from the 09:30 open to the 16:00 close on the last trading day of a month and
  the first three of the next, with a stop k x the 14-day average range.

The index has no overnight session, so the overnight family is NQ only; the turn of the month runs on the index too.

    python research/v39_overnight.py <data dir> <out.csv>
"""
from __future__ import annotations

import glob
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v38_gap as G  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

NY = "America/New_York"
TICK, PV, FEE = 0.25, 2.0, 0.62


def overnight_days(nq: pd.DataFrame) -> list[tuple]:
    """(day, overnight high, low, the day's RTH 5-minute bars) for complete sessions outside roll weeks."""
    t = nq.index.tz_convert(NY)
    m = np.asarray(t.hour * 60 + t.minute)
    # the session a bar belongs to: bars from 18:00 count toward the next day
    sess = (t + pd.to_timedelta(np.where(m >= 18 * 60, 1, 0), unit="D")).normalize()
    df = nq.assign(sess=np.asarray(sess.strftime("%Y-%m-%d")), m=m)
    out = []
    for day, g in df.groupby("sess", sort=True):
        on = g[(g.m >= 18 * 60) | (g.m < 570)]
        rth = g[(g.m >= 570) & (g.m < 960)]
        d = pd.Timestamp(day)
        if d.month in (3, 6, 9, 12) and 7 <= d.day <= 21:
            continue
        if len(on) < 300 or len(rth) < 380:
            continue
        b = G.rth5(rth.drop(columns=["sess", "m"]))
        bt = b.index.tz_convert(NY)
        bm = np.asarray(bt.hour * 60 + bt.minute)
        if bm[0] != 570 or bm[-1] != 955:
            continue
        out.append((day, on.high.max(), on.low.min(), bm, *(b[x].to_numpy(float) for x in ("open", "high", "low",
                                                                                           "close"))))
    return out


def run_onbreak(days: list[tuple], k: float, r_tgt: float, t_exit: int, side: str) -> pd.DataFrame:
    rows = []
    for day, onh, onl, mi, o, h, lo, c in days:
        mid, rng = (onh + onl) / 2, onh - onl
        for j in range(len(mi) - 1):
            if mi[j] + 5 > 720:
                break
            d = 1 if c[j] > onh else -1 if (side == "both" and c[j] < onl) else 0
            if not d:
                continue
            entry = o[j + 1] + d * TICK
            stop = max(mid, entry - k * rng) if d > 0 else min(mid, entry + k * rng)
            risk_pts = abs(entry - stop)
            if risk_pts <= 2 * TICK:
                break
            tgt = entry + d * r_tgt * risk_pts
            out = None
            for i in range(j + 1, len(mi)):
                if (d > 0 and lo[i] <= stop) or (d < 0 and h[i] >= stop):
                    out = (min(o[i], stop) if d > 0 else max(o[i], stop)) - d * TICK
                elif (d > 0 and h[i] >= tgt) or (d < 0 and lo[i] <= tgt):
                    out = tgt
                elif mi[i] + 5 >= t_exit or i == len(mi) - 1:
                    out = c[i] - d * TICK
                if out is not None:
                    break
            pnl = (out - entry) * d * PV - 2 * FEE
            rows.append({"day": day, "pnl": pnl, "r": pnl / (risk_pts * PV + 2 * FEE)})
            break
    return pd.DataFrame(rows)


def run_tom(sess: list[tuple], k: float) -> pd.DataFrame:
    days = [s[0] for s in sess]
    month = [d[:7] for d in days]
    tom = set()
    for i in range(len(days)):
        if i + 1 < len(days) and month[i + 1] != month[i]:
            tom.add(days[i])
        first = i == 0 or month[i - 1] != month[i]
        if first:
            tom.update(days[i:i + 3])
    rng = [s[4].max() - s[5].min() for s in sess]
    avg = pd.Series(rng).rolling(14).mean().shift(1).to_numpy()
    rows = []
    for idx, (day, _pc, _mi, o, _h, lo, c) in enumerate(sess):
        if day not in tom or not np.isfinite(avg[idx]):
            continue
        entry = o[0] + TICK
        stop = entry - k * avg[idx]
        hit = np.flatnonzero(lo <= stop)
        out = (min(o[hit[0]], stop) - TICK) if len(hit) else c[-1] - TICK
        pnl = (out - entry) * PV - 2 * FEE
        rows.append({"day": day, "pnl": pnl, "r": pnl / ((entry - stop) * PV + 2 * FEE)})
    return pd.DataFrame(rows)


def main() -> None:
    data, out = Path(sys.argv[1]), sys.argv[2]
    nq = pd.read_pickle(data / "nq1m_all.pkl")
    days = overnight_days(nq)
    print("overnight days", len(days), days[0][0], days[-1][0], flush=True)
    files = sorted(glob.glob(str(data / "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv")))
    ix = pd.concat([load_histdata(f) for f in files]).sort_index()
    ix = ix[~ix.index.duplicated()]
    sess = {"nq": G.sessions(G.rth5(nq), True), "index": G.sessions(G.rth5(ix), False)}
    rows = []

    def split(r: dict, f: pd.DataFrame, cut: str, a: str, b: str) -> None:
        for tag, part in ((a, f[f.day < cut] if len(f) else f), (b, f[f.day >= cut] if len(f) else f)):
            r.update({f"{tag} {k}": v for k, v in G.stats(part).items()})

    for k, r_tgt, t_exit, side in itertools.product((0.25, 0.5, 1.0), (1.0, 2.0, 3.0), (720, 960), ("buy", "both")):
        r = {"family": "onbreak", "k": k, "r_tgt": r_tgt, "t_exit": t_exit, "side": side}
        split(r, run_onbreak(days, k, r_tgt, t_exit, side), "2020", "nq15-19", "nq20-25")
        rows.append(r)
        print(r["family"], k, r_tgt, t_exit, side, r["nq15-19 pf"], r["nq20-25 pf"], r["nq15-19 win"], flush=True)
    for k in (0.5, 1.0, 2.0):
        r = {"family": "tom", "k": k}
        split(r, run_tom(sess["nq"], k), "2020", "nq15-19", "nq20-25")
        split(r, run_tom(sess["index"], k), "2018", "ix11-17", "ix18-26")
        rows.append(r)
        print(r, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
