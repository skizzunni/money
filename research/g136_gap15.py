"""G136 (docs/NINJATRADER_V38.md): 15 gap contracts once the floor has stopped, sized for a jumped stop; G135's screen.

    python research/g136_gap15.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{"gap_go_locked_qty": 15, "gap_slip_pts": 2.0}, {"gap_go_locked_qty": 15, "gap_slip_pts": 4.0},
              {"gap_go_locked_qty": 12, "gap_slip_pts": 2.0}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
