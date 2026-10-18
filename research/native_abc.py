"""The nine native NinjaTrader runs A / B / C x slippage 0 / 1 / 2 (docs/NATIVE_RUNS.md), compared.

    python research/native_abc.py <folder> [<out.csv>] [<flag days, yyyy-mm-dd,...>]

The folder holds, per run (A_S0 ... C_S2): <run>_output.txt (its own NinjaScript Output), <run>_trades.csv (the
Strategy Analyzer's Trades export) and <run>_summary.csv. Checked first, per run: the code's settings lines are the
frozen ones (only UseBreakout / shorts differ by configuration), commission is charged, the funnel has no rejection
or runtime error, and where warm-up ended (the engine's first ready bar). The eligible period starts at the first
session after the LATEST ready time of the nine; every run is measured over it, and any trade before it is reported
(none is expected: nothing trades before the engine is ready). Then, per run: net after costs, gross, commission,
positions and contracts, profit factor, $ a position, average win / loss, closed-trade drawdown (on net, exit order),
an intraday estimate (closed equity before each trade less its MAE: the trade's worst point, from NinjaTrader's own
MAE), losing streak, worst day, components (entry name), months, the largest winners' share; and between runs: the
cost of each tick of slippage, and which entries differ between configurations (expected: B = A's momentum trades,
C = A without its "W Short" trades; any other difference is listed). Flag days (e.g. the first session after a data
hole, whose "yesterday" is weeks old): every run is also measured without the trades entered on them, a retrospective
data-quality view reported beside the full one, never instead of it. Months: net after costs by exit month.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

RUNS = [f"{c}_S{s}" for c in "ABC" for s in (0, 1, 2)]
COMPONENT = {"Long": "momentum long", "Short": "momentum short", "W Long": "breakout long", "W Short": "breakout short"}
READY = re.compile(r"2 engine ready: \d+ bars \(from (\d{4}-\d\d-\d\d \d\d:\d\d)\)")


def money(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(r"[$,)]", "", regex=True).str.replace("(", "-", regex=False).astype(float)


def load_trades(path: Path) -> pd.DataFrame:
    t = pd.read_csv(path)
    t["entry_time"] = pd.to_datetime(t["Entry time"])
    t["exit_time"] = pd.to_datetime(t["Exit time"])
    t["net"] = money(t["Profit"])
    t["commission"] = money(t["Commission"])
    t["gross"] = t.net + t.commission
    t["mae"] = money(t["MAE"]) if "MAE" in t else 0.0
    t["component"] = t["Entry name"].map(COMPONENT)
    return t.sort_values(["exit_time", "entry_time"]).reset_index(drop=True)


def load_output(path: Path) -> dict:
    lines = path.read_text().splitlines()
    sets = [x for x in lines if x.startswith("MNQ settings:")]
    funnel = "\n".join(x for x in lines if x.startswith("  "))
    m = READY.search(funnel)
    n = lambda pat: int(re.search(pat, funnel).group(1)) if re.search(pat, funnel) else -1  # noqa: E731
    return {"settings": sets, "ready": pd.Timestamp(m.group(1)) if m else pd.NaT,
            "runs in file": sum(x.startswith("MNQ funnel, end of run") for x in lines),
            "rejected": n(r"rejected (\d+)"), "runtime errors": n(r"runtime errors (\d+)")}


def frozen(settings: list[str]) -> list[str]:
    """The settings lines without what the configuration changes (UseBreakout, shorts) and the bar count."""
    out = []
    for s in settings:
        s = re.sub(r"\(\d+ loaded", "(n loaded", s)
        s = re.sub(r"UseBreakout \w+ \(risk \$\d+, shorts \w+\)", "UseBreakout <cfg>", s)
        out.append(s)
    return out


def metrics(t: pd.DataFrame) -> dict:
    eq = t.net.cumsum()
    before = eq.shift(fill_value=0.0)
    low = before - t.mae
    peak = eq.cummax().clip(lower=0).shift(fill_value=0.0)
    wins, losses = t.net[t.net > 0], t.net[t.net < 0]
    run = best = 0
    for p in t.net:
        run = run + 1 if p < 0 else 0
        best = max(best, run)
    day = t.groupby(t.exit_time.dt.normalize()).net.sum()
    comp = t.groupby("component").net.sum()
    return {"positions": len(t), "contracts": int(t.Qty.sum()), "gross $": t.gross.sum(),
            "commission $": t.commission.sum(), "net $": t.net.sum(),
            "profit factor": wins.sum() / -losses.sum() if len(losses) else float("inf"),
            "net $/position": t.net.mean(), "avg win": wins.mean(), "avg loss": losses.mean(),
            "closed DD": float((eq.cummax().clip(lower=0) - eq).max()) if len(t) else 0.0,
            "intraday DD (MAE est.)": float((peak - low).max()) if len(t) else 0.0,
            "losing streak": best, "worst day": day.min(), "losing days": int((day < 0).sum()), "days": len(day),
            "top-5 share %": 100 * t.net.nlargest(5).sum() / t.net.sum() if t.net.sum() > 0 else float("nan"),
            **{f"{k} $": comp.get(k, 0.0) for k in COMPONENT.values()}}


def keys(t: pd.DataFrame) -> set:
    return set(zip(t.entry_time, t["Entry name"], t.Qty, strict=True))


def main() -> None:
    folder = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    flag = pd.to_datetime(sys.argv[3].split(",")) if len(sys.argv) > 3 else pd.DatetimeIndex([])
    have = [r for r in RUNS if (folder / f"{r}_trades.csv").exists()]
    missing = [r for r in RUNS if r not in have]
    if missing:
        print(f"missing runs (no trades export): {missing}")
    trades = {r: load_trades(folder / f"{r}_trades.csv") for r in have}
    outs = {r: load_output(folder / f"{r}_output.txt") for r in have if (folder / f"{r}_output.txt").exists()}
    print("== Checks per run")
    ref = frozen(outs[have[0]]["settings"]) if have and have[0] in outs else None
    for r in have:
        o = outs.get(r)
        t = trades[r]
        cfg_ok = o is not None and frozen(o["settings"]) == ref
        def g(k, o=o):
            return o[k] if o else "-"
        print(f"{r}: Output {'present' if o else 'MISSING'}; runs in Output {g('runs in file')}; "
              f"settings frozen: {cfg_ok}; ready from {g('ready')}; rejected {g('rejected')}; "
              f"runtime errors {g('runtime errors')}; commission charged on {(t.commission > 0).sum()}/{len(t)} "
              f"trades; $ per contract {(t.commission / t.Qty).round(2).unique()}")
    ready = max((o["ready"] for o in outs.values() if pd.notna(o["ready"])), default=pd.NaT)
    start = (ready + pd.Timedelta(hours=12)).normalize() if pd.notna(ready) else pd.NaT
    first = start.date() if pd.notna(start) else "?"
    print(f"\nwarm-up ends (latest of the runs): {ready}; eligible period from {first}")
    rows = []
    for r in have:
        t = trades[r]
        early = t[t.entry_time < start] if pd.notna(start) else t.iloc[:0]
        if len(early):
            print(f"{r}: {len(early)} trades before the eligible period (not counted): {early.entry_time.min()}")
        rows.append({"run": r, **metrics(t[~t.index.isin(early.index)])})
    df = pd.DataFrame(rows).set_index("run")
    eligible = {r: trades[r][trades[r].entry_time >= start] if pd.notna(start) else trades[r] for r in have}
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 40)
    print("\n== Per run, eligible period, after commission")
    print(df.round(1).T.to_string())
    if len(flag):
        print(f"\n== Without trades entered on the flag days {[d.date() for d in flag]} (retrospective view)")
        print(pd.DataFrame({r: metrics(t[~t.entry_time.dt.normalize().isin(flag)]) for r, t in eligible.items()})
              .round(1).loc[["positions", "net $", "closed DD", "intraday DD (MAE est.)", "losing streak",
                             "worst day"]].to_string())
    print("\n== Net $ after costs by exit month")
    print(pd.DataFrame({r: t.groupby(t.exit_time.dt.to_period("M")).net.sum() for r, t in eligible.items()})
          .fillna(0).round(1).to_string())
    print("\n== Slippage: net $ change per configuration")
    for c in "ABC":
        if all(f"{c}_S{s}" in df.index for s in (0, 1, 2)):
            n0, n1, n2 = (df.loc[f"{c}_S{s}", "net $"] for s in (0, 1, 2))
            print(f"{c}: S1 - S0 {n1 - n0:+.2f}, S2 - S0 {n2 - n0:+.2f}")
    print("\n== Entries between configurations (same slippage)")
    for s in (0, 1, 2):
        a, b, c = (trades.get(f"{x}_S{s}") for x in "ABC")
        if a is None:
            continue
        mom = a[a["Entry name"].isin(["Long", "Short"])]
        if b is not None:
            print(f"S{s}: B vs A's momentum trades: only in B {len(keys(b) - keys(mom))}, only in A "
                  f"{len(keys(mom) - keys(b))}")
        if c is not None:
            noshort = a[a["Entry name"] != "W Short"]
            print(f"S{s}: C vs A without W Short: only in C {len(keys(c) - keys(noshort))}, only in A "
                  f"{len(keys(noshort) - keys(c))}")
    if out is not None:
        df.to_csv(out)


if __name__ == "__main__":
    main()
