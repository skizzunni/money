"""G421 (docs/NINJATRADER_V38.md): the funded account traded more often. U48 without its skipped checks, then without
the range-position filter, the loser limit, with narrower entry lines (entry_k 0.8) and entries to 15:30. G415's fresh
starts (trades a session, $ a session, lost, green days / months), then G372's unseen starts (G386's runner).

    python research/g421_trade_more.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F

A = {"skip_checks": ""}
B = {**A, "range_pos_min": 0.0}
C = {**B, "max_losers": 0}
D = {**C, "entry_k": 0.8}
E = {**D, "last_entry_end": 930}
V = {"U48": {}, "A: every check": A, "B: A + no range filter": B, "C: B + no loser limit": C,
     "D: C + entry lines 0.8": D, "E: D + entries to 15:30": E}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
