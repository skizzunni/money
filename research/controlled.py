"""A controlled comparison of the original and revised NinjaTrader code (the audit, step 3-6 of the user's brief).

python research/controlled.py <sim_original.dll> <sim_revised.dll> <bars.pkl> <first> <last> <out.csv>

Both versions of the C# strategy (original: commit d4cb597, the source of the user's first export; revised: the
current files) compiled against the same NinjaTrader stand-in, run as complete backtests on identical 1-minute bars
(09:30-16:00 New York, and the 16:00 bar), identical warm-up (the first 14 full sessions), commission $0.95 a side
(the user's export), the strategy's default evaluation settings and sizing (4 MNQ bot, breakout $400 / 1-10 MNQ),
RoundPrices on. Varied, one at a time: the code, the breakout on/off, and slippage 0 / 1 / 2 ticks on every market
fill (the stand-in's fill model: market orders fill at the next bar's open +/- slippage; stops at the stop or the open
past it +/- slippage; take-profits at their price). Each run is a full rerun, never trades edited after the fact.

Per run: net $, trades, $ by component (bot / breakout), winners %, longest losing streak (trades in time order), max
drawdown of minute equity (closed P/L + open P/L at each minute's worst price, against the peak (each minute's best)
before that minute), worst day, days below -$1,000, and the Apex 50K intraday-trail evaluation replayed from every
session (pass at +$3,000 + $25 of equity, fail at $2,000 below the equity peak, 30 calendar days; worst point of a
minute before its best): passed / failed / ran out of time.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
DOTNET = "/opt/dotnet/dotnet" if Path("/opt/dotnet/dotnet").exists() else "dotnet"
ENV = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}


def rth(bars):
    """09:30-16:00 and the 16:00 bar: the strategy's 16:00 exit is a market order that fills at the next bar's open,
    which must be 16:00 (as in NinjaTrader), not the next morning's."""
    m = bars.index.tz_convert(NY)
    t = m.hour * 60 + m.minute
    return bars[(t >= 570) & (t <= 960)]


def write_bars(bars, path):
    idx = bars.index.tz_convert(NY).strftime("%Y-%m-%d %H:%M")
    df = pd.DataFrame({"t": idx, "o": bars.open.values, "h": bars.high.values, "l": bars.low.values,
                       "c": bars.close.values})
    df.to_csv(path, header=False, index=False, float_format="%.2f")


def run(dll, bars_csv, **props):
    args = [f"{k}={v}" for k, v in props.items()]
    r = subprocess.run([DOTNET, str(dll), str(bars_csv), "1", *args], capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    rows = [{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]), "why": a[5],
             "pnl": float(a[6]), "name": b[0], "q": int(b[1])} for a, b in zip(t, n, strict=True)]
    return pd.DataFrame(rows)


def metrics(tr, bars):
    tr = tr.sort_values("eb").reset_index(drop=True)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    day = bars.index.tz_convert(NY).normalize()
    # minute equity: closed P/L + the open position at each minute's best and worst
    n = len(bars)
    closed = np.zeros(n)
    best = np.zeros(n)
    worst = np.zeros(n)
    for r in tr.itertuples():
        closed[r.xb:] += r.pnl
        if r.xb > r.eb:
            seg = slice(r.eb, r.xb)
            fav = (h[seg] - r.en) if r.d > 0 else (r.en - lo[seg])
            adv = (lo[seg] - r.en) if r.d > 0 else (r.en - h[seg])
            best[seg] += fav * 2.0 * r.q
            worst[seg] += adv * 2.0 * r.q
    hi_eq, lo_eq = closed + best, closed + worst
    # closed P/L is booked at the exit bar; before it, the open P/L stands for the trade
    # the peak before each minute (a minute's low is not compared with its own high: worst case for a trail)
    peak = np.concatenate([[0.0], np.maximum.accumulate(np.maximum(hi_eq, 0.0))[:-1]])
    intra_dd = float(np.max(peak - lo_eq)) if n else 0.0
    losing = run_ = 0
    for p in tr.pnl:
        run_ = run_ + 1 if p < 0 else 0
        losing = max(losing, run_)
    daily = tr.groupby(day[tr.eb.to_numpy()]).pnl.sum()
    is_w = tr.name.str.startswith("W")
    # the evaluation from every session's first minute
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    res = {"passed": 0, "failed": 0, "timeout": 0}
    for s in starts:
        base = closed[s - 1] if s > 0 else 0.0
        end_t = day[s] + pd.Timedelta(days=30)
        e = int(np.searchsorted(day, end_t))
        if e >= n:
            break
        hi = hi_eq[s:e] - base
        lw = lo_eq[s:e] - base
        pk = np.concatenate([[0.0], np.maximum.accumulate(np.maximum(hi, 0.0))[:-1]])
        bust = np.flatnonzero(lw <= pk - 2000.0)
        hit = np.flatnonzero(hi >= 3025.0)
        if hit.size and (not bust.size or hit[0] < bust[0]):
            res["passed"] += 1
        elif bust.size:
            res["failed"] += 1
        else:
            res["timeout"] += 1
    total = sum(res.values())
    return {"net $": tr.pnl.sum(), "trades": len(tr), "bot $": tr.pnl[~is_w].sum(), "breakout $": tr.pnl[is_w].sum(),
            "breakout shorts $": tr.pnl[is_w & (tr.d < 0)].sum(), "winners %": 100 * (tr.pnl > 0).mean(),
            "losing streak": losing, "intraday DD": intra_dd, "worst day": daily.min(),
            "days < -$1,000": int((daily < -1000).sum()),
            "eval pass %": 100 * res["passed"] / total, "eval fail %": 100 * res["failed"] / total,
            "eval timeout %": 100 * res["timeout"] / total}


def incomplete_sessions(bars):
    """Sessions whose 09:30-16:00 data ends before 15:59 or misses minutes (half days, holidays, data holes)."""
    m = bars.index.tz_convert(NY)
    t = (m.hour * 60 + m.minute).to_numpy()
    day = m.normalize()
    inside = (t >= 570) & (t < 960)
    n = pd.Series(inside, index=day).groupby(level=0).sum()
    return sorted(d.strftime("%Y-%m-%d") for d in n[n < 390].index)


DEFAULT_SKIP = ("2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07,"
                "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26,"
                "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24")


def main() -> None:
    """argv: dll_original dll_revised bars.pkl first last out.csv [treatment: none | complete] [trades_dir]"""
    dll_o, dll_r, data, first, last, out = sys.argv[1:7]
    treatment = sys.argv[7] if len(sys.argv) > 7 else "none"
    trades_dir = Path(sys.argv[8]) if len(sys.argv) > 8 else None
    bars = rth(pd.read_pickle(data))
    m = bars.index.tz_convert(NY)
    bars = bars[(m >= pd.Timestamp(first, tz=NY)) & (m < pd.Timestamp(last, tz=NY) + pd.Timedelta(days=1))]
    tmp = Path(tempfile.mkdtemp())
    csv = tmp / "bars.csv"
    write_bars(bars, csv)
    skip = incomplete_sessions(bars)
    extra = {"SkipDates": DEFAULT_SKIP + "," + ",".join(skip)} if treatment == "complete" else {}
    print(f"treatment: {treatment}; incomplete sessions: {len(skip)}" +
          (" (no new trades on them)" if treatment == "complete" else " (traded as they are)"))
    jobs = [(code, dll, brk, slip) for code, dll in (("original", dll_o), ("revised", dll_r))
            for brk in (True, False) for slip in (0, 1, 2)]

    def one(job):
        code, dll, brk, slip = job
        props = {"UseBreakout": brk, "SimSlippageTicks": slip, "SimCommissionPerSide": 0.95, **extra}
        tr = run(dll, csv, **props)
        if trades_dir is not None:
            trades_dir.mkdir(parents=True, exist_ok=True)
            name = f"{code}_breakout-{'on' if brk else 'off'}_slip{slip}"
            when = bars.index.tz_convert(NY)
            tr.assign(entry_time=when[tr.eb.to_numpy()].strftime("%Y-%m-%d %H:%M"),
                      exit_time=when[tr.xb.to_numpy()].strftime("%Y-%m-%d %H:%M")).to_csv(
                trades_dir / f"{name}.csv", index=False)
            (trades_dir / f"{name}.config.txt").write_text(
                "\n".join(f"{k}={v}" for k, v in {"dll": dll, "bars": data, "first": first, "last": last,
                                                   "treatment": treatment, **props}.items()) + "\n")
        return {"code": code, "breakout": "on" if brk else "off", "slippage ticks": slip, **metrics(tr, bars)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame(list(pool.map(one, jobs)))
    df.to_csv(out, index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    print(f"{first} to {last}, {len(bars)} bars")
    print(df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
