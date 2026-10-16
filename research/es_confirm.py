"""The S&P 500 at the bot's signals: does the move count more when the S&P is also outside its noise area?

    python research/es_confirm.py spx_1m.pkl nsx_1m_scaled.pkl

spx_1m.pkl: HistData SPXUSD 1-minute bars (load_histdata). Descriptive, on 2011-2018 only: v1.3's trades at 10 MNQ and
$350, split by where the S&P closed at the same check against its own noise area, computed by mnqbot.noise the same
way. See docs/RESULTS.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.noise import NoiseConfig, run  # noqa: E402

START, END = "2010-11-01", "2019-01-01"


def state(direction: int, close: float, upper: float, lower: float) -> str:
    if (close > upper) if direction > 0 else (close < lower):
        return "S&P beyond its line too"
    if (close < lower) if direction > 0 else (close > upper):
        return "S&P on the other side"
    return "S&P inside its noise area"


def main() -> None:
    spx = pd.read_pickle(sys.argv[1])
    spx = spx[(spx.index >= START) & (spx.index < END)]
    bands = run(spx, NoiseConfig(skip_dates="", fed_no_shorts=False), minutes=1).bands
    sb = pd.DataFrame([(spx.index[i], u, lo, spx.close.iloc[i]) for i, u, lo in bands],
                      columns=["t", "u", "l", "c"]).set_index("t")
    nsx = pd.read_pickle(sys.argv[2])
    nsx = nsx[(nsx.index >= START) & (nsx.index < END)]
    res = run(nsx, NoiseConfig(qty=10, max_loss_per_trade=350, skip_dates="", fed_no_shorts=False), minutes=1)
    rows = []
    for t in res.trades:
        if t.entry_time.year < 2011:
            continue
        ts = nsx.index[t.entry_bar - 1]  # the check bar
        s = "no S&P data" if ts not in sb.index else state(t.direction, *sb.loc[ts, ["c", "u", "l"]])
        rows.append({"state": s, "win": t.pnl > 0, "pnl": t.pnl})
    df = pd.DataFrame(rows)
    g = df.groupby("state").agg(n=("win", "size"), win=("win", "mean"), pnl=("pnl", "mean"), total=("pnl", "sum"))
    g["win"] = (100 * g.win).round(1)
    print(g.round({"pnl": 1, "total": 0}).to_string())


if __name__ == "__main__":
    main()
