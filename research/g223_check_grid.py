"""G223 (docs/NINJATRADER_V38.md): the check grid around U44; G195's runner (the chart's execution on the window, NQ and
the index).

    python research/g223_check_grid.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g195_wide as G
import v24_scan as S

G.U41 = {**G.U41, "max_losers": 3, "early_daily_loss": 750.0, "time_stop": 45, "range_pos_min": 0.7,
         "gap_go_k": 0.6, "profit_step_fast": 650.0, "profit_step_fast_from": 8000.0,
         "fill_qty3_room": 8000.0, "fill_qty2_room": 4000.0, "size_up_to": 75}  # U44
G.VARIANTS = [{}, {"check_step": 15}, {"check_step": 15, "first_check": 585}, {"first_check": 585},
              {"check_step": 20}, {"check_step": 15, "last_entry_end": 870}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, [(k, ["proxy", "nq", "index"]) for k in range(len(G.VARIANTS))]):
            print(json.dumps(r), flush=True)
