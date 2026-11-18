"""G522 (docs/NINJATRADER_V38.md): Pine v4.3's rules exactly (v3.8's engine: no gap trade, fill-ins or brake; the lock at
0.75, the stop 0.5 noise units out, a 45-minute time stop, the trend over 45 sessions, 3 losers a day, $150 a contract)
at a fixed 2 / 3 / 4 MNQ on the 50K's $2,000 trailing floor, against Funded growth, on G495's measure.

    python research/g522_pine_rules_funded.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import json
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

from mnqbot.noise import NoiseConfig

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "tests"))
from test_pine_v4 import V4  # noqa: E402

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}


def pine(q: int, daily: float) -> dict:
    """Every setting the U48 base sets, back to the default, then Pine v4.3's at q MNQ on the account's limits."""
    base = json.load(open(sys.argv[4]))
    dflt = NoiseConfig()
    v = {k: getattr(dflt, k) for k in base}
    v.update({k: x for k, x in V4.items() if k != "trail_from"})
    v.update(qty=q, max_loss_per_trade=150.0 * q, trail_dd=2000.0, daily_loss_limit=daily)
    return v


if __name__ == "__main__":
    V = {"Funded growth (G511)": FG}
    for q in (2, 3, 4):
        V[f"Pine v4.3 at {q} MNQ"] = pine(q, 0.0)
    V["Pine v4.3 at 3 MNQ, $900 a day"] = pine(3, 900.0)
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
