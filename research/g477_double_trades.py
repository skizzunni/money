"""G477 (docs/NINJATRADER_V38.md): a measurement for the user, twice the trades. U58 (brake 0.25) against D1 = entry
lines at 0.6 noise every day (entry_k and entry_k_regime 0.6), no calm-day skip (calm_k 0), no trend filter (trend_n 0);
D2 = D1 + checks every 15 minutes; D3 = D1 + checks every 10 minutes. G415's fresh starts, then G372's development /
unseen starts (G386's runner).

    python research/g477_double_trades.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
D1 = {**B, "entry_k": 0.6, "entry_k_regime": 0.6, "calm_k": 0.0, "trend_n": 0}
V = {"U58 (brake 0.25)": B, "D1 loose entries": D1, "D2 = D1 + 15-min checks": {**D1, "check_step": 15},
     "D3 = D1 + 10-min checks": {**D1, "check_step": 10}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
