"""The daily candidate against frozen B, on identical dates, costs and account starts (docs/DAILY_AUDIT.md).

    python research/comparison_report.py

From the committed outputs of research/eval_d.py --f (verification/candidate_f/{nq,mnq}/): net, intraday drawdown,
their ratio, average net trade, profit factor, win rate, evaluation outcomes and gates, at 2 and 3 ticks; monthly
net; and participation over every eligible session (campaigns a session; the share of sessions with 0, 1, 2, 3 and,
for B, more than 3 entries). Writes verification/daily_audit/comparison_<kind>.csv and monthly_<kind>.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ["B", "D+F1", "D+F2"]


def participation(led: pd.DataFrame, eligible: int) -> dict:
    per = led.groupby("entry_day").size()
    out = {"campaigns a session (all eligible)": len(led) / eligible}
    for k in range(4):
        n = eligible - len(per) if k == 0 else int((per == k).sum())
        out[f"{k} campaigns %"] = 100 * n / eligible
    out["more than 3 %"] = 100 * int((per > 3).sum()) / eligible
    return out


def main() -> None:
    out = ROOT / "verification" / "daily_audit"
    out.mkdir(parents=True, exist_ok=True)
    for kind in ("mnq", "nq"):
        src = ROOT / "verification" / "candidate_f" / kind
        comp = pd.read_csv(src / "comparison.csv")
        gates = pd.read_csv(src / "gates.csv")
        led = pd.read_csv(src / "ledger.csv.gz", parse_dates=["entry_day"])
        summary = (src / "summary.txt").read_text().splitlines()[0]
        eligible = int(summary.split(":")[1].split("eligible")[0])
        rows = []
        for book in BOOKS:
            for slip in (2, 3):
                c = comp[(comp.candidate == book) & (comp.slippage == slip)].iloc[0]
                g = gates[(gates.candidate == book) & (gates.slippage == slip)].set_index("gate")
                lb = led[(led.candidate == book) & (led.slippage == slip)]
                part = {k: round(v, 3 if "session" in k else 1) for k, v in participation(lb, eligible).items()}
                rows.append({"book": book, "slippage ticks": slip, "positions": int(c.positions),
                             "net $": round(c["net $"], 2), "intraday DD $": round(c["intraday DD $"], 2),
                             "net / intraday DD": round(c["net / intraday DD"], 2),
                             "average net trade $": round(c["expectancy $"], 2),
                             "profit factor": round(c["profit factor"], 2), "win rate %": round(c["win rate %"], 1),
                             **part,
                             "evaluations, non-overlapping (pass / breach / expired / path-dependent)":
                                 c["non-overlapping: pass / breach / expired / path-dependent"],
                             "evaluations, overlapping": c["overlapping: pass / breach / expired / path-dependent"],
                             **{f"{gate} {g.loc[gate, 'threshold']}":
                                f"{g.loc[gate, 'result']:.2f} {g.loc[gate, 'verdict']}" for gate in g.index}})
        pd.DataFrame(rows).to_csv(out / f"comparison_{kind}.csv", index=False)
        m = led[led.candidate.isin(BOOKS)].assign(month=lambda x: x.entry_day.dt.to_period("M").astype(str))
        monthly = m.pivot_table(index="month", columns=["candidate", "slippage"], values="pnl $", aggfunc="sum",
                                fill_value=0.0).round(2)
        monthly.to_csv(out / f"monthly_{kind}.csv")
        print(kind, eligible, "eligible sessions")
        print(pd.DataFrame(rows).T.to_string())


if __name__ == "__main__":
    main()
