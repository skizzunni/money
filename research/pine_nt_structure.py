"""Pine source against the NinjaTrader code on identical MNQ 5-minute bars: which differences are structural (always
the same sign, from the rules) and which depend on the bars (docs/PINE_REFERENCE.md section 1b).

    python research/pine_nt_structure.py [<verification/pine_reference>]

Reads the joined trade files written by research/pine_reference.py. Per run and category: trades, how many came out
better / worse / the same for NinjaTrader, the net, the largest single trade's share and the net without it, and the
net by month.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "verification/pine_reference"
    rows = []
    for run in ("R4_1t", "R4_2t", "R2_1t", "R2_2t"):
        j = pd.read_csv(folder / f"joined_{run}_pine_vs_nt.csv")
        j["delta"] = j.pnl_nt.fillna(0) - j.pnl_pine.fillna(0)  # a knock-on trade can be on one side only
        j["month"] = j["entry time"].str[:7]
        j["cat"] = j.category.where(j.category.str.startswith("knock-on"), j.category.str[:1])
        for cat, g in j[j.category != "match"].groupby("cat"):
            big = g.delta.abs().idxmax()
            months = g.groupby("month").delta.sum().round(2)
            rows.append({"run": run, "category": cat[:9], "trades": len(g),
                         "NinjaTrader better": int((g.delta > 0.005).sum()),
                         "NinjaTrader worse": int((g.delta < -0.005).sum()),
                         "same": int((g.delta.abs() <= 0.005).sum()),
                         "NinjaTrader minus Pine $": round(g.delta.sum(), 2),
                         "largest single trade $": round(g.delta[big], 2),
                         "its entry": g["entry time"][big],
                         "without it $": round(g.delta.sum() - g.delta[big], 2),
                         "by month $": "; ".join(f"{m} {v:+.2f}" for m, v in months.items())})
    df = pd.DataFrame(rows)
    df.to_csv(folder / "structure.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 80):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
