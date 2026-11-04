"""G156 (docs/NINJATRADER_V38.md), a robustness measurement: U29, U33 and U34 at 2 ticks of slippage.

    python research/g156_slip2.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

U29 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 20}
G.U33 = {}  # each variant below is a whole configuration
U33 = {**U29, "size_up_to": 50, "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True}
U34 = {**U33, "profit_step_fast": 750.0}
G.VARIANTS = [{**U29, "slippage_ticks": 2}, {**U33, "slippage_ticks": 2}, {**U34, "slippage_ticks": 2}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps({k: v for k, v in r.items() if "net" in k or "d1000" in k or k == "k"}), flush=True)
