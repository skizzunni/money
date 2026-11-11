"""G151 (docs/NINJATRADER_V38.md): six rarely used settings on U34; G135's screen against U34.

    python research/g151_rare.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
G.VARIANTS = [{}, {"tom_no_shorts": True}, {"tom_mult": 1.5}, {"late_lock_from": 900}, {"time_lock": 30},
    {"after_loss_same_side": True}, {"big_day_against_tp": 1.0}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
