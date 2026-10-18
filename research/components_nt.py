"""Candidates A / B / C (docs/REFERENCE.md, step 4), complete reruns of the NinjaTrader strategy on the stand-in.

    python research/components_nt.py <sim.dll> <bars.pkl> <first> <last> <label> <out.csv> [<trades_dir>]

A: the current combined strategy (defaults). B: the bot (momentum) alone, UseBreakout off. C: the bot and the
breakout's longs, BreakoutShorts off (a day whose short level is reached first has no breakout trade). Everything
else at its default and held fixed: sizing (bot 4 MNQ, breakout $400 / 1-10 MNQ), parameters, warm-up (the bars'
own first 14 full sessions), 09:30-16:00 bars and the 16:00 bar, commission $0.95 a side (provisional: the earlier
exports' rate), slippage 0 / 1 / 2 ticks on every market and stop fill (the stand-in's fill model), sessions with
missing minutes given no new trades (as skip dates, decided from the data before the run: a retrospective
data-quality exclusion, not a rule that could run live). Every run is a complete rerun; no trade is removed after the
fact. Positions = trades here (no partial exits in these configurations).
"""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controlled as K  # noqa: E402

CANDIDATES = {"A combined": {"UseBreakout": True},
              "B momentum only": {"UseBreakout": False},
              "C no breakout shorts": {"UseBreakout": True, "BreakoutShorts": False}}


def extra_metrics(tr, bars):
    tr = tr.sort_values("xb").reset_index(drop=True)
    when = bars.index.tz_convert(K.NY)
    pnl = tr.pnl
    eq = pnl.cumsum()
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    month = pd.Series(pnl.values, index=when[tr.xb.to_numpy()].tz_localize(None).to_period("M")).groupby(level=0).sum()
    roll = month.rolling(3).sum().dropna()
    top5 = pnl.nlargest(5).sum()
    return {"contracts": int(tr.q.sum()), "profit factor": wins.sum() / -losses.sum() if len(losses) else np.inf,
            "avg $/position": pnl.mean(), "avg win": wins.mean(), "avg loss": losses.mean(),
            "closed-trade DD": float((eq.cummax().clip(lower=0) - eq).max()),
            "months +": f"{(month > 0).sum()}/{len(month)}", "worst month": month.min(),
            "worst 3 months": roll.min() if len(roll) else np.nan,
            "top-5 share %": 100 * top5 / pnl.sum() if pnl.sum() > 0 else np.nan}


def main() -> None:
    dll, data, first, last, label, out = sys.argv[1:7]
    trades_dir = Path(sys.argv[7]) if len(sys.argv) > 7 else None
    bars = K.rth(pd.read_pickle(data))
    m = bars.index.tz_convert(K.NY)
    bars = bars[(m >= pd.Timestamp(first, tz=K.NY)) & (m < pd.Timestamp(last, tz=K.NY) + pd.Timedelta(days=1))]
    m = bars.index.tz_convert(K.NY)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(bars, csv)
    skip = K.DEFAULT_SKIP + "," + ",".join(K.incomplete_sessions(bars))
    jobs = [(name, props, slip) for name, props in CANDIDATES.items() for slip in (0, 1, 2)]

    def one(job):
        name, props, slip = job
        p = {**props, "SimSlippageTicks": slip, "SimCommissionPerSide": 0.95, "SkipDates": skip}
        tr = K.run(dll, csv, **p)
        if trades_dir is not None:
            trades_dir.mkdir(parents=True, exist_ok=True)
            stem = f"{label}_{name.split()[0]}_slip{slip}"
            tr.assign(entry_time=m[tr.eb.to_numpy()].strftime("%Y-%m-%d %H:%M"),
                      exit_time=m[tr.xb.to_numpy()].strftime("%Y-%m-%d %H:%M")).to_csv(trades_dir / f"{stem}.csv",
                                                                                     index=False)
            (trades_dir / f"{stem}.config.txt").write_text(
                "\n".join(f"{k}={v}" for k, v in {"dll": dll, "bars": data, "first": first, "last": last, **p}.items()))
        return {"data": label, "candidate": name, "slippage ticks": slip, **K.metrics(tr, bars),
                **extra_metrics(tr, bars)}

    with ThreadPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame(list(pool.map(one, jobs)))
    df.to_csv(out, index=False)
    pd.set_option("display.width", 400)
    pd.set_option("display.max_columns", 40)
    print(f"{label}: {first} to {last}, {len(bars)} bars, {len(K.incomplete_sessions(bars))} incomplete sessions "
          "given no new trades")
    cols = ["candidate", "slippage ticks", "net $", "trades", "contracts", "bot $", "breakout $", "profit factor",
            "avg $/position", "avg win", "avg loss", "closed-trade DD", "intraday DD", "losing streak", "worst day",
            "months +", "worst month", "worst 3 months", "top-5 share %", "eval pass %", "eval fail %"]
    print(df[cols].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
