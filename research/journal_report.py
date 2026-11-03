"""A report on MnqNoiseV38's journal (MnqNoiseV38_backtest.csv or MnqNoiseV38_live_<account>.csv, in
Documents\\NinjaTrader 8): the results, every loss broken down, the streaks, the days and the months, and checks that
the rules held (no day at the $1,000 limit, the journal's own totals adding up).

    python research/journal_report.py <journal.csv> [daily limit, default 1000] [goal, default 50000]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd


def money(x: float) -> str:
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(out)


def group(t: pd.DataFrame, key) -> pd.DataFrame:
    rows = []
    for k, x in t.groupby(key, observed=True):
        lost = x.loc[x["P/L"] <= 0, "P/L"]
        rows.append({key: k, "trades": len(x), "losers": len(lost), "net": money(x["P/L"].sum()),
                     "lost on losers": money(lost.sum()), "average loss": money(lost.mean()) if len(lost) else "-"})
    return pd.DataFrame(rows)


def main() -> None:
    j = pd.read_csv(sys.argv[1])
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else 1000.0
    goal = float(sys.argv[3]) if len(sys.argv) > 3 else 50000.0
    t = j[j.kind == "TRADE"].copy()
    d = j[j.kind == "DAY"].copy()
    if t.empty:
        print("No trades in the journal yet.")
        return
    t["entry time"] = pd.to_datetime(t["entry time"])
    t["exit time"] = pd.to_datetime(t["exit time"])
    p = t["P/L"].to_numpy(float)
    wins, losses = p[p > 0], p[p <= 0]
    eq = np.r_[0.0, np.cumsum(p)]
    print(f"# MnqNoiseV38 journal report: {t['entry time'].min():%Y-%m-%d} to {t['exit time'].max():%Y-%m-%d}\n")
    print("## Results\n")
    print(table(pd.DataFrame([{
        "trades": len(p), "net": money(p.sum()), "winners": f"{100 * len(wins) / len(p):.1f}%",
        "profit factor": f"{wins.sum() / -losses.sum():.2f}" if len(losses) and losses.sum() < 0 else "-",
        "average win": money(wins.mean()) if len(wins) else "-",
        "average loss": money(losses.mean()) if len(losses) else "-",
        "largest win": money(p.max()), "largest loss": money(p.min()),
        "closed drawdown": money(float((np.maximum.accumulate(eq) - eq).max()))}])))
    print("\n## Every loss, broken down\n")
    lt = t[t["P/L"] <= 0]
    print(f"{len(lt)} losing trades, {money(lt['P/L'].sum())} in all.\n")
    print("**By how they ended**\n")
    print(table(group(t, "exit kind")))
    print("\n**By side**\n")
    print(table(group(t, "side")))
    t["hour"] = t["entry time"].dt.strftime("%H:00")
    print("\n**By entry hour (New York)**\n")
    print(table(group(t, "hour")))
    t["size"] = pd.cut(t["contracts"], [0, 1, 3, 6, 10, 1000], labels=["1", "2-3", "4-6", "7-10", "11+"])
    print("\n**By size**\n")
    print(table(group(t, "size")))
    print("\n**The 10 largest losses**\n")
    big = lt.nsmallest(10, "P/L")[["entry time", "exit time", "side", "contracts", "entry", "exit", "exit kind", "P/L",
                                   "day P/L"]].copy()
    big["P/L"] = big["P/L"].map(money)
    big["day P/L"] = big["day P/L"].map(money)
    print(table(big))
    print("\n## Streaks\n")
    runs, run, worst_run, run_loss, worst_run_loss = [], 0, 0, 0.0, 0.0
    for x in p:
        if x <= 0:
            run += 1
            run_loss += x
        else:
            if run:
                runs.append(run)
            run, run_loss = 0, 0.0
        worst_run = max(worst_run, run)
        worst_run_loss = min(worst_run_loss, run_loss)
    print(f"Longest losing streak: {worst_run} trades; the costliest streak: {money(worst_run_loss)}; "
          f"streaks of 3 or more: {sum(r >= 3 for r in runs + [run])}.\n")
    print("## Days and months\n")
    if len(d):
        dp = d["day P/L"].astype(float)
        traded = d[d["trades today"].fillna(0) > 0]
        tp = traded["day P/L"].astype(float)
        print(f"Days with trades: {len(traded)}; green {int((tp > 0).sum())}, red {int((tp < 0).sum())}; best "
              f"{money(dp.max())}, worst {money(dp.min())}.\n")
        print(f"Days at or past -{money(limit)[1:]}: {int((dp <= -limit).sum())}; days past -$800: "
              f"{int((dp <= -800).sum())}.\n")
    print("**Weeks** (Monday to Friday, by exit)\n")
    week = t["exit time"].dt.normalize() - pd.to_timedelta(t["exit time"].dt.weekday, unit="D")
    w = t.groupby(week.dt.strftime("%Y-%m-%d"))["P/L"].agg(["count", "sum"]).reset_index()
    w.columns = ["week of", "trades", "net"]
    print(f"{len(w)} weeks: {int((w.net > 0).sum())} green, {int((w.net < 0).sum())} red; best {money(w.net.max())}, "
          f"worst {money(w.net.min())}.\n")
    w["net"] = w["net"].map(money)
    print(table(w.tail(12)))
    print("\n**Months**\n")
    m = t.groupby(t["exit time"].dt.strftime("%Y-%m"))["P/L"].agg(["count", "sum"]).reset_index()
    m.columns = ["month", "trades", "net"]
    m["net"] = m["net"].map(money)
    print(table(m))
    span = (t["exit time"].max() - t["entry time"].min()).days / 30.44
    if span >= 1:
        pace = p.sum() / span
        left = goal - p.sum()
        when = ("goal reached" if left <= 0 else f"about {int(np.ceil(left / pace))} more months to {money(goal)}"
                if pace > 0 else "no progress yet")
        print(f"\n**Pace:** {money(pace)} a month over {span:.1f} months; {when}.")
    if "entry slip ticks" in t:
        es, xs = t["entry slip ticks"].dropna(), t["exit slip ticks"].dropna()
        if len(es):
            print(f"\n**Fills vs plan:** entries {es.mean():+.1f} ticks on average ({len(es)} trades), stops and market "
                  f"exits {xs.mean() if len(xs) else 0:+.1f} ({len(xs)}). The backtests assume 1 tick; at 3 or more, turn "
                  "on Gentle start (docs/NINJATRADER_V38.md, G29-G30).")
    print("\n## Checks\n")
    ok_total = abs(float(t["total P/L"].iloc[-1]) - (float(t["total P/L"].iloc[0]) - p[0] + p.sum())) < 0.05
    ok_days = len(d) == 0 or abs(float(d["day P/L"].astype(float).sum()) - p.sum()) < 0.05 * max(1, len(d))
    print(f"- The trades add up to the journal's running total: {'yes' if ok_total else 'NO'}")
    print(f"- The days add up to the trades: {'yes' if ok_days else 'NO'}")
    no_limit = len(d) == 0 or bool((d["day P/L"].astype(float) > -limit).all())
    print(f"- No day at the {money(limit)} limit: {'yes' if no_limit else 'NO'}")


if __name__ == "__main__":
    main()
