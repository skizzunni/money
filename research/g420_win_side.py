"""G420 (docs/NINJATRADER_V38.md): the funded account (U48) with no entries against the side of today's first winner
(win_side_target: the first winner that reached its target), alone or with G417's house money. G372's 12-month measure
(G386's runner).

    python research/g420_win_side.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g386_funded_chop_pause as R

R.VARIANTS.clear()
R.VARIANTS["U48"] = {}
R.VARIANTS["no entries against the first winner"] = {"win_side_only": True}
R.VARIANTS["no entries against the first target"] = {"win_side_only": True, "win_side_target": True}
R.VARIANTS["against the first winner + day up x1.5"] = {"win_side_only": True, "day_up_mult": 1.5}

if __name__ == "__main__":
    R.main()
