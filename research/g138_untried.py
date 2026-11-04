"""G138 (docs/NINJATRADER_V38.md): settings never tried on the growth bot, one at a time on U33; G135's screen.

    python research/g138_untried.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{"storm_k": 1.6}, {"storm_k": 2.0}, {"touch_entry": True}, {"limit_entry_frac": 0.5}, {"side_cooldown": 1}, {"streak_k": 3}, {"eq_n": 20}, {"confirm": True}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
