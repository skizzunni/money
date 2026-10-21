"""Net and gross profit against the maximum drawdown: frozen B and variants of its own settings, on the stand-in.

    python research/ratio_study.py <out folder> <B sim.dll> nq=<pkl> [raw=<folder>] [first=<date>] [last=<date>]
                                   [adj=<pkl>] [mnq=<sep>,<dec>] [variants=a,b]

For each variant (B's NinjaScript, MnqNoiseMomentum.cs, with property overrides), each data set and 2 / 3 ticks: net,
gross profit and loss, the closed-trade and the intraday maximum drawdown (open P/L at each minute's worst, as
research/controlled.py), their ratios, and the same within each half of NQ (2015-2019, 2020-2025) and within each
year. Same skip dates (holidays, half days, sessions missing 09:30-16:00 minutes) and FOMC dates as every B result,
$0.95 a side.
"""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_d as ED  # noqa: E402

NY = "America/New_York"
VARIANTS = {
    "B": {"UseBreakout": False},
    "B + Williams in the gaps": {"UseBreakout": True},
    # the breakout's risk a trade (the evaluation setting EvalBreakoutRisk; default 400): its weight against the bot
    "B + W risk 200": {"UseBreakout": True, "EvalBreakoutRisk": 200},
    "B + W risk 600": {"UseBreakout": True, "EvalBreakoutRisk": 600},
    "B + W risk 800": {"UseBreakout": True, "EvalBreakoutRisk": 800},
    # B's own daily gate across both setups (DailyLossLimit: no entry whose planned risk could take the day's realized
    # loss past it), on B + breakout $200
    "B + W risk 200 day limit 400": {"UseBreakout": True, "EvalBreakoutRisk": 200, "DailyLossLimit": 400},
    "B + W risk 200 day limit 600": {"UseBreakout": True, "EvalBreakoutRisk": 200, "DailyLossLimit": 600},
    "B + W risk 200 day limit 1000": {"UseBreakout": True, "EvalBreakoutRisk": 200, "DailyLossLimit": 1000},
    # the breakout long only (BreakoutShorts off)
    "B + W risk 200 long only": {"UseBreakout": True, "EvalBreakoutRisk": 200, "BreakoutShorts": False},
    "B + W risk 600 long only": {"UseBreakout": True, "EvalBreakoutRisk": 600, "BreakoutShorts": False},
    # sensitivity of the breakout's levels (BreakoutK, default 0.5) and stop (BreakoutStop, default 0.25), at $200
    "B + W200 k 0.4": {"UseBreakout": True, "EvalBreakoutRisk": 200, "BreakoutK": 0.4},
    "B + W200 k 0.6": {"UseBreakout": True, "EvalBreakoutRisk": 200, "BreakoutK": 0.6},
    "B + W200 stop 0.20": {"UseBreakout": True, "EvalBreakoutRisk": 200, "BreakoutStop": 0.2},
    "B + W200 stop 0.30": {"UseBreakout": True, "EvalBreakoutRisk": 200, "BreakoutStop": 0.3},
}
FIRST = {"nq": "2015-03-01", "adj": "2015-03-01", "mnq": "2026-07-20"}
HALVES = {"nq": (("2015-2019", "2015-03-01", "2020-01-01"), ("2020-2025", "2020-01-01", "2026-01-01")),
          "adj": (("2015-2019", "2015-03-01", "2020-01-01"), ("2020-2025", "2020-01-01", "2026-01-01")),
          "mnq": ()}


def drawdowns(tr: pd.DataFrame, bars: pd.DataFrame) -> tuple[float, float]:
    """(closed-trade maximum drawdown, intraday maximum drawdown with open P/L) of a trade list."""
    if tr.empty:
        return 0.0, 0.0
    eq = tr.sort_values("xb").pnl.cumsum().to_numpy()
    closed = float(np.max(np.maximum.accumulate(np.maximum(eq, 0.0)) - eq))
    return closed, float(K.metrics(tr, bars)["intraday DD"])


def summary(tr: pd.DataFrame, bars: pd.DataFrame) -> dict:
    pnl = tr.pnl.to_numpy() if len(tr) else np.zeros(0)
    cdd, idd = drawdowns(tr, bars)
    gp, gl = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    net = pnl.sum()
    return {"trades": len(tr), "net $": net, "gross profit $": gp, "gross loss $": gl,
            "profit factor": gp / gl if gl else np.inf, "closed DD $": cdd, "intraday DD $": idd,
            "net / intraday DD": net / idd if idd else np.inf,
            "gross profit / intraday DD": gp / idd if idd else np.inf,
            "net / closed DD": net / cdd if cdd else np.inf}


def one(args):
    name, props, kind, slip, csv, skip, dll = args
    tr = K.run(dll, csv, SimSlippageTicks=slip, SimCommissionPerSide=ED.FEE, SkipDates=",".join(sorted(skip)),
               FedDates=",".join(sorted(ED.FOMC)), **props)
    return name, kind, slip, tr


def main() -> None:
    out, dll = Path(sys.argv[1]), sys.argv[2]
    opts = dict(a.split("=", 1) for a in sys.argv[3:])
    names = opts["variants"].split(",") if "variants" in opts else list(VARIANTS)
    out.mkdir(parents=True, exist_ok=True)
    data = {}
    if "nq" in opts:
        data["nq"] = ED.nq_bars(opts["nq"], opts.get("raw", ""), opts.get("first", "2015-03-01"),
                                opts.get("last", "2025-06-30"))
    if "adj" in opts:
        data["adj"] = ED.nq_bars(opts["adj"], "")
    if "mnq" in opts:
        sep, dec = opts["mnq"].split(",")
        data["mnq"] = ED.mnq_series(sep, dec)
    jobs, rth_of = [], {}
    for kind, bars in data.items():
        skip = ED.skip_set(bars)
        rth = K.rth(bars[["open", "high", "low", "close"]])
        csv = Path(tempfile.mkdtemp()) / f"{kind}.csv"
        K.write_bars(rth, csv)
        rth_of[kind] = rth
        jobs += [(n, VARIANTS[n], kind, slip, str(csv), skip, dll) for n in names for slip in (2, 3)]
    with ProcessPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, jobs))
    rows, years = [], []
    for name, kind, slip, tr in results:
        rth = rth_of[kind]
        day = rth.index.tz_localize(None).normalize()
        tr = tr.assign(day=day[tr.eb.to_numpy()])
        tr = tr[tr.day >= pd.Timestamp(opts.get("first", FIRST[kind]) if kind == "nq" else FIRST[kind])]
        tr.to_csv(out / f"trades_{kind}_{name.replace(' ', '_')}_{slip}t.csv", index=False)
        rows.append({"variant": name, "data": kind, "slippage": slip, "period": "all", **summary(tr, rth)})
        for label, a, b in HALVES[kind]:
            part = tr[(tr.day >= pd.Timestamp(a)) & (tr.day < pd.Timestamp(b))]
            rows.append({"variant": name, "data": kind, "slippage": slip, "period": label, **summary(part, rth)})
        for y, part in tr.groupby(tr.day.dt.year):
            s = summary(part, rth)
            years.append({"variant": name, "data": kind, "slippage": slip, "year": y, "net $": s["net $"],
                          "intraday DD $": s["intraday DD $"], "net / intraday DD": s["net / intraday DD"]})
    res = pd.DataFrame(rows)
    yr = pd.DataFrame(years)
    res.to_csv(out / "ratios.csv", index=False)
    yr.to_csv(out / "years.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(res.round(2).to_string(index=False))
    print(yr.pivot_table(index=["data", "slippage", "year"], columns="variant", values="net / intraday DD").round(2)
          .to_string())


if __name__ == "__main__":
    main()
