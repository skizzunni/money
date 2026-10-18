"""The 172-trade NinjaTrader reference run, rebuilt from its NinjaScript Output (docs/REFERENCE.md).

    python research/nt_reference.py <NinjaScript_Output.txt> <summary.csv> [<previous_trades.csv>] [<out_dir>]

Every trade is rebuilt from the run's own execution lines ("MNQ execution: <order> <qty> @ <price> <side> <time>",
printed with Diagnostics on), entries paired with the exits that closed them. Checked against the run's summary
export, then measured: per component, per month, per day, closed-trade drawdown, losing streak, contract volume, the
largest winners, the trades shared with the previous (83-trade) export, the sessions present, and commission
scenarios applied to these same trades (arithmetic on fixed trades, not a rerun).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PV = 2.0  # MNQ, $ a point
ENTRIES = ("Long", "Short", "W Long", "W Short")
EXEC = re.compile(r"MNQ execution: (.+?) (\d+) @ ([\d.]+) (Long|Short) (.+)$")
DAILY = re.compile(r"(\d{4}-\d\d-\d\d) MNQ Noise Momentum \(")
HOLIDAYS = ("2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
            "2026-09-07")


def trades_from_output(lines):
    open_, out = [], []
    for line in lines:
        m = EXEC.match(line)
        if not m:
            continue
        name, qty, px, side, when = m.group(1), int(m.group(2)), float(m.group(3)), m.group(4), m.group(5)
        t = pd.Timestamp(when)
        if name in ENTRIES:
            open_.append({"name": name, "dir": 1 if side == "Long" else -1, "qty": qty, "entry": px, "entry_time": t})
            continue
        d = -1 if side == "Long" else 1  # an exit's side is the opposite of the position's
        cands = [p for p in open_ if p["dir"] == d]
        if name == "Breakout: bot first":
            cands = [p for p in cands if p["name"].startswith("W")]
        p = cands[0]
        if qty != p["qty"]:
            raise ValueError(f"partial exit not expected in this run: {line}")
        open_.remove(p)
        out.append({**p, "exit": px, "exit_time": t, "exit_name": name,
                    "pnl": d * (px - p["entry"]) * qty * PV})
    if open_:
        raise ValueError(f"positions left open: {open_}")
    df = pd.DataFrame(out).sort_values(["exit_time", "entry_time"]).reset_index(drop=True)
    df["component"] = df.name.map({"Long": "momentum long", "Short": "momentum short", "W Long": "breakout long",
                                   "W Short": "breakout short"})
    return df


def closed_drawdown(pnl):
    eq = pnl.cumsum()
    return float((eq.cummax().clip(lower=0) - eq).max())


def streak(pnl):
    best = run = 0
    for p in pnl:
        run = run + 1 if p < 0 else 0
        best = max(best, run)
    return best


def summary_value(summary, key):
    row = summary[summary.iloc[:, 0] == key]
    return str(row.iloc[0, 1]) if len(row) else ""


def main() -> None:
    output, summ = Path(sys.argv[1]), Path(sys.argv[2])
    prev = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    lines = output.read_text().splitlines()
    tr = trades_from_output(lines)
    summary = pd.read_csv(summ, header=None)
    by_exit = tr.sort_values("exit_time")
    tr["day"] = tr.exit_time.dt.normalize()
    daily = tr.groupby("day").pnl.sum()
    print("== Reference run, rebuilt from its executions")
    print(f"trades {len(tr)} (summary: {summary_value(summary, 'Total # of trades')})")
    print(f"profit before commissions ${tr.pnl.sum():,.2f} (summary net: {summary_value(summary, 'Total net profit')},"
          f" commission {summary_value(summary, 'Commission')}, slippage {summary_value(summary, 'Total slippage')})")
    dd = closed_drawdown(by_exit.pnl)
    print(f"closed-trade drawdown ${dd:,.2f} (summary: {summary_value(summary, 'Max. drawdown')})")
    print(f"longest losing streak {streak(by_exit.pnl)} (summary: {summary_value(summary, 'Max. consec. losers')})")
    print(f"days with trades {len(daily)}, losing days {(daily < 0).sum()}, winning days {(daily > 0).sum()}")
    print(f"round-trip contract units {tr.qty.sum()}")
    print(f"winners {(tr.pnl > 0).sum()}, losers {(tr.pnl < 0).sum()}, even {(tr.pnl == 0).sum()}")
    print(f"first entry {tr.entry_time.min()}, last exit {tr.exit_time.max()}")
    comp = tr.groupby("component").agg(trades=("pnl", "size"), contracts=("qty", "sum"), pnl=("pnl", "sum"))
    print("\n== By component (before commissions)")
    print(comp.to_string())
    print("\n== By month (exit month, before commissions)")
    print(tr.groupby([tr.exit_time.dt.to_period("M"), "component"]).pnl.sum().unstack(fill_value=0)
          .assign(total=lambda x: x.sum(axis=1)).to_string())
    top = tr.pnl.nlargest(5)
    print(f"\n== Largest five winners ${top.sum():,.2f}; the other {len(tr) - 5}: ${tr.pnl.sum() - top.sum():,.2f}")
    print(tr.loc[top.index, ["entry_time", "name", "qty", "entry", "exit", "exit_name", "pnl"]].to_string())
    twenty = tr[(tr.pnl == 20.0) & tr.name.isin(["Long", "Short"])]
    print(f"momentum trades at exactly +$20: {len(twenty)} (exits: {twenty.exit_name.value_counts().to_dict()})")
    print("\n== Commission on these same trades (arithmetic, not a rerun)")
    for side in (0.0, 0.62, 0.95):
        c = tr.qty * 2 * side
        net = tr.pnl - c
        print(f"${side:.2f} a side: commission ${c.sum():,.2f}, net ${net.sum():,.2f}, "
              f"closed-trade drawdown ${closed_drawdown(net.loc[by_exit.index]):,.2f}")
    days = sorted({m.group(1) for line in lines if (m := DAILY.match(line))})
    bd = pd.bdate_range(days[0], days[-1])
    bd = bd[~bd.strftime("%Y-%m-%d").isin(HOLIDAYS)]
    missing = [d.strftime("%Y-%m-%d") for d in bd if d.strftime("%Y-%m-%d") not in days]
    print(f"\n== Sessions: {len(days)} with a 09:30 bar from {days[0]} to {days[-1]}; {len(bd)} scheduled "
          f"(holidays out); missing {len(missing)}: {' .. '.join(missing[:1] + missing[-1:])}")
    if prev is not None:
        p = pd.read_csv(prev)
        p["entry_time"] = pd.to_datetime(p["Entry time"])
        p["exit_time"] = pd.to_datetime(p["Exit time"])
        money = lambda s: s.astype(str).str.replace(r"[$,)]", "", regex=True).str.replace("(", "-").astype(float)  # noqa: E731
        p["profit"], p["commission"] = money(p["Profit"]), money(p["Commission"])
        p["gross"] = p.profit + p.commission
        key = ["entry_time", "exit_time", "Entry price", "Exit price", "Qty", "Entry name"]
        cur = tr.rename(columns={"entry": "Entry price", "exit": "Exit price", "qty": "Qty", "name": "Entry name"})
        m = p.merge(cur, on=key, how="left", indicator=True)
        same = m[m._merge == "both"]
        equal = bool((same.gross - same.pnl).abs().max() < 1e-6)
        print(f"\n== Previous export: {len(p)} trades; found unchanged here {len(same)} "
              f"(entry, exit, prices, contracts, entry name); gross equal: {equal}")
        print(f"   previous: gross ${p.gross.sum():,.2f}, commission ${p.commission.sum():,.2f}, "
              f"net ${p.profit.sum():,.2f}")
        rest = tr.pnl.sum() - same.pnl.sum()
        print(f"   the other {len(tr) - len(same)} trades here: ${rest:,.2f} before costs; "
              f"${same.pnl.sum():,.2f} + ${rest:,.2f} = ${tr.pnl.sum():,.2f}")
        earlier = tr[tr.entry_time < p.entry_time.min()]
        later = tr[tr.entry_time > p.exit_time.max()]
        print(f"   of those: {len(earlier)} before the previous run's first trade (${earlier.pnl.sum():,.2f}), "
              f"{len(later)} after its last (${later.pnl.sum():,.2f})")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        tr.drop(columns="day").to_csv(out_dir / "reference_172_trades.csv", index=False)


if __name__ == "__main__":
    main()
