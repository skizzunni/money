"""A and B over the longest native MNQ history, rebuilt from the runs' own fills (docs/REFERENCE.md section 4e).

    python research/native_long.py <NinjaScript_Output.txt> <summaries folder> [<out folder>]

The Output holds many runs one after another (the window was not cleared between them). Each run is cut at its
"MNQ settings:" lines and its trades rebuilt from its execution lines (research/nt_reference.py); commission is
$1.90 a contract a round trip (confirmed by the summaries, section 4b); a run is named by the summary
(<run>_summary.csv) whose net it matches to the cent, and its configuration is read from its own settings line.
Per run, from 6/29 (the first session after the data hole, also shown without it): net after commission, positions,
contracts, profit factor, average win / loss, closed-trade drawdown (net, in exit order), longest losing streak,
worst day, months, components; between A and B at each slippage, trade by trade: B against A's momentum trades.
Intraday drawdown needs each trade's MAE (the Trades export) or the bars: not available from the Output.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nt_reference as R  # noqa: E402

FEE = 1.90
HOLE_AFTER = pd.Timestamp("2026-06-29")


def runs(lines):
    starts = [i for i, x in enumerate(lines) if x.startswith("MNQ settings: MNQ")] + [len(lines)]
    for a, b in zip(starts[:-1], starts[1:], strict=True):
        seg = lines[a:b]
        m = re.search(r"UseBreakout (\w+)", seg[1])
        sh = re.search(r"shorts (\w+)", seg[1])
        ready = next((x for x in seg if "2 engine ready" in x), "")
        yield seg, (m.group(1) if m else "?"), (sh.group(1) if sh else "-"), ready.strip()


def stats(t):
    t = t.sort_values(["exit_time", "entry_time"])
    net = t.pnl - FEE * t.qty
    eq = net.cumsum()
    run = best = 0
    for p in net:
        run = run + 1 if p < 0 else 0
        best = max(best, run)
    day = net.groupby(t.exit_time.dt.normalize()).sum()
    wins, losses = net[net > 0], net[net < 0]
    return {"positions": len(t), "contracts": int(t.qty.sum()), "net $": net.sum(),
            "profit factor": wins.sum() / -losses.sum(), "avg win": wins.mean(), "avg loss": losses.mean(),
            "closed DD": float((eq.cummax().clip(lower=0) - eq).max()), "losing streak": best,
            "worst day": day.min(), "losing days": int((day < 0).sum()), "days": len(day),
            "top-5 share %": 100 * net.nlargest(5).sum() / net.sum()}


def main() -> None:
    lines = Path(sys.argv[1]).read_text().splitlines()
    summ = {}
    for f in Path(sys.argv[2]).glob("*_summary.csv"):
        d = pd.read_csv(f, header=None)
        v = d[d[0] == "Total net profit"].iloc[0, 1]
        summ[f.name[:4]] = float(v.replace("$", "").replace(",", "").replace("(", "-").replace(")", ""))
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    named = {}
    for seg, ub, sh, ready in runs(lines):
        t = R.trades_from_output(seg)
        net = t.pnl.sum() - FEE * t.qty.sum()
        hit = [k for k, v in summ.items() if abs(v - net) < 0.005]
        if hit and hit[0] not in named:
            named[hit[0]] = t
            print(f"{hit[0]}: UseBreakout {ub}, shorts {sh}; {ready}; first entry {t.entry_time.min()}, last exit "
                  f"{t.exit_time.max()}; {len(t)} trades; net ${net:,.2f} = summary")
    print("\n== Per run, 6/29 to 10/16, after $1.90 a contract")
    print(pd.DataFrame({k: stats(t) for k, t in sorted(named.items())}).round(1).to_string())
    print("\n== Without 6/29 (its 'yesterday' is 5/21, before the data hole; retrospective view)")
    print(pd.DataFrame({k: stats(t[t.entry_time.dt.normalize() != HOLE_AFTER]) for k, t in sorted(named.items())})
          .round(1).loc[["positions", "net $", "closed DD", "losing streak", "worst day"]].to_string())
    print("\n== Net after commission by exit month")
    print(pd.DataFrame({k: (t.pnl - FEE * t.qty).groupby(t.exit_time.dt.to_period("M")).sum()
                        for k, t in sorted(named.items())}).round(1).to_string())
    print("\n== By component, before / after commission")
    for k, t in sorted(named.items()):
        g = t.assign(net=t.pnl - FEE * t.qty).groupby("component").agg(n=("pnl", "size"), gross=("pnl", "sum"),
                                                                         net=("net", "sum"))
        print(k, {c: (int(r.n), round(r.gross, 1), round(r.net, 1)) for c, r in g.iterrows()})
    print("\n== July, by component (after commission)")
    for k, t in sorted(named.items()):
        j = t[t.exit_time.dt.month == 7]
        print(k, (j.pnl - FEE * j.qty).groupby(j.component).sum().round(1).to_dict(), "total",
              round((j.pnl - FEE * j.qty).sum(), 1), "trades", len(j))
    print("\n== B against A's momentum trades (entry time, name, contracts, entry and exit price)")
    for s in "012":
        a, b = named.get(f"A_L{s}"), named.get(f"B_L{s}")
        if a is None or b is None:
            continue
        key = ["entry_time", "name", "qty", "entry", "exit", "exit_time"]
        mom = a[a.name.isin(["Long", "Short"])]
        m = mom.merge(b, on=key, how="outer", indicator=True)
        print(f"slippage {s}: A momentum {len(mom)}, B {len(b)}; identical {int((m._merge == 'both').sum())}; "
              f"only A {int((m._merge == 'left_only').sum())}; only B {int((m._merge == 'right_only').sum())}")
        for r in m[m._merge != "both"].itertuples():
            print(f"   {r._7}: {r.entry_time} {r.name} {r.qty} @ {r.entry} -> {r.exit} {r.exit_time}")
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        for k, t in named.items():
            t.assign(commission=FEE * t.qty, net=t.pnl - FEE * t.qty).to_csv(out / f"{k}_trades_from_output.csv",
                                                                              index=False)


if __name__ == "__main__":
    main()
