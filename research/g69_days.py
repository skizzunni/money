"""G69 (docs/NINJATRADER_V38.md): a trade on 70% of days, with 1-MNQ fill-in trades. Packages P0 (today's default),
P1 (small gaps), P2 (+ uptrend shorts), P3 (+ opening drive).

    [NT_EXEC=1] python research/g69_days.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> [P0,P1,...]
"""
import os
import sys

import numpy as np
import pandas as pd
import shadow_gate as SG
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run


def with_1600(bars: pd.DataFrame, m: int) -> pd.DataFrame:
    """A 16:00 bar at the last price where a session's data stops at 16:00 (as research/g6_time_stop.py)."""
    t = bars.index.tz_convert("America/New_York")
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()


S.init({}, *sys.argv[1:4])
NT = bool(os.environ.get("NT_EXEC"))
if NT:
    S.D = {k: (with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items()}
PACK = {"P0": {}, "P1": {"gap_go_small_k": 0.0}, "P2": {"gap_go_small_k": 0.0, "trend_small": True},
        "P3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5},
        # G70: the same fill-in trades only once the floor has stopped
        "P2L": {"gap_go_small_k": 0.0, "trend_small": True, "fill_after_lock": True},
        "P3L": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True},
        # G71: with a cushion, and today's gains don't widen today's budget
        "A": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
              "fill_min_room": 3000.0, "day_keep": 1.0},
        "B": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
              "fill_min_room": 4000.0, "day_keep": 1.0},
        # G72: G71 without day_keep
        "A2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0},
        "B2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 4000.0},
        # G73: the fill-ins don't raise the contract steps
        "A3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0, "fill_no_steps": True},
        "B3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 4000.0, "fill_no_steps": True},
        # G74: A2 and a gap win doesn't widen the day's budget
        "A4": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0, "gap_no_budget": True},
        # G75: the room for a new trade at most $950, today's default and U21 on
        "P0c": {"trade_risk_cap": 950.0},
        "A2c": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                "fill_min_room": 3000.0, "trade_risk_cap": 950.0},
        # G76: sizing with 2 points more stop slippage
        "P0s": {"size_slip_pts": 2.0},
        "A2s": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                "fill_min_room": 3000.0, "size_slip_pts": 2.0},
        # G80: U22 with up to 5 gap contracts once the floor has stopped
        "U22q5": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 5},
        # G81: U23 with a $2,000 cushion
        "U23c2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 2000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 5},
        # G82: U23 with up to 7 gap contracts once stopped
        "U23q7": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 7},
        # G83: U24 with the gap trade at the bot's size once stopped
        "U24q15": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 15},
        # G84: up to 10 gap contracts once stopped
        "U24q10": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10},
        # G85: up to 12 gap contracts once stopped
        "U25q12": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 12},
        # G86: gap sizing with 5 points of stop slippage, up to 15 once stopped
        "U25g": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                 "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 15, "gap_slip_pts": 5.0},
        # G87: U25 with the shadow gate near the floor
        "U25pA": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "protect_room": 1000.0},
        "U25pB": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "protect_room": 1500.0},
        # G88: U25 on the 100K and 150K limits
        "U25_100": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10,
                    "daily_loss_limit": 1800.0, "trail_dd": 3000.0},
        "U25_150": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10,
                    "daily_loss_limit": 2700.0, "trail_dd": 4500.0},
        # G89: U25 with a 45- or 90-minute time stop
        "U25t45": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "time_stop": 45},
        "U25t90": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "time_stop": 90},
        # G90: U25 with a take-profit of 1.5 or 2.5 noise units
        "U25tp15": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "take_profit": 1.5},
        "U25tp25": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "take_profit": 2.5},
        # G91: U25 with the lock at 0.25 or 0.5 of the max loss
        "U25l25": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "lock_at": 0.25},
        "U25l50": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "lock_at": 0.5},
        # G92: U25 with the stop 0.18 or 0.30 noise units past the line
        "U25sb18": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "stop_buffer": 0.18},
        "U25sb30": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "stop_buffer": 0.30},
        # G93: U25 with the stop 0.21 noise units past the line
        "U25sb21": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "stop_buffer": 0.21},
        # G94: G93 with a 3-point sizing allowance
        "U25sb21s3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                      "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "stop_buffer": 0.21},
        # G95: U25 with calm-stretch fill-ins
        "U25calm": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "calm_small": True},
        # G96: U25 with the fill-ins at 2 MNQ $6,000 above the floor
        "U25f2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0},
        # G97: G96 with a 3-point sizing allowance
        "U25f2s3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0},
        # G98: U26 with gap contracts at most 1 per $400 above the stopped floor
        "U26g400": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "gap_go_room_per_c": 400.0},
        # G99: U26 with the giveback brake at half the best profit
        "U26gb": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.5},
        # G100: U27 with the gap trade squeezed near the floor
        "U27sq": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.5, "gap_squeeze": True},
        # G101: U27 with the brake at 0.7
        "U27gb7": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                   "giveback_brake": 0.7},
        # G102: U28 with the fill-ins from day one
        "U28day1": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": False,
                    "fill_min_room": 0.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5},
        # G104: U28 with a contract per $1,000 once the floor has stopped
        "U28s1000": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                     "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                     "giveback_brake": 0.5, "profit_step_locked": 1000.0},
        # G105: U28 with up to 20 contracts
        "U28max20": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                     "fill_min_room": 3000.0, "size_slip_pts": 3.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                     "giveback_brake": 0.5, "size_up_to": 20},
        # G106: U28 with up to 20 contracts and a 4-point sizing allowance
        "U28max20s4": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                       "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                       "giveback_brake": 0.5, "size_up_to": 20},
        # G107: U29 with the fill-ins at 3 MNQ from $9,000 above the floor
        "U29f3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.5, "size_up_to": 20, "fill_qty3_room": 9000.0},
        # G108: U29 with the drive fill-in at 0.3
        "U29d3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.3, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.5, "size_up_to": 20},
        # G109: U29 with 2-MNQ fill-ins from $5,000
        "U29q2r5": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 5000.0,
                    "giveback_brake": 0.5, "size_up_to": 20},
        # G110: U29 with a $950 daily budget
        "U29d950": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "daily_loss_limit": 950.0},
        # G111: U29 with the gap stop at the middle of the 09:30 bar
        "U29gs5": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                   "giveback_brake": 0.5, "size_up_to": 20, "gap_go_stop_frac": 0.5},
        "U29rp55": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "range_pos_min": 0.55},
        "U29rp75": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "range_pos_min": 0.75},
        "U29ck6": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "calm_k": 0.6},
        "U29ck8": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "calm_k": 0.8},
        "U29bd13": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "big_day_k": 1.3},
        "U29bd18": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "big_day_k": 1.8},
        # G116: U29 with the after-loss trade's max loss as the others'
        "U29al1": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                   "giveback_brake": 0.5, "size_up_to": 20, "after_loss_ml_mult": 1.0},
        "U29t40": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                   "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                   "giveback_brake": 0.5, "size_up_to": 20, "trend_n": 40},
        "U29p1250": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                     "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                     "giveback_brake": 0.5, "size_up_to": 20, "profit_step": 1250.0},
        # G119: U29 with the after-loss max loss as the others' once the floor has stopped
        "U29al1L": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "size_up_to": 20, "after_loss_ml_locked": 1.0},
        # G120: U30 with up to 25 / 30 contracts
        "U30max25": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 25},
        "U30max30": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 30},
        # G121: U31 with up to 40 / 50 contracts
        "U31max40": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 40},
        "U31max50": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50},
        # G124: U32 with no entries at the 13:00 and 14:30 checks
        "U32sk": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870"},
        # G125: G124 only until the floor has stopped
        "U32ske": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                   "skip_checks_early": True},
        # G126: U33 with each trade risking part of the day's budget left
        "U33bf6": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "budget_frac": 0.6},
        "U33bf8": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "budget_frac": 0.8},
        # G127: U33 with no new entries once the day is this far up
        "U33ds15": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_stop_profit": 1500.0},
        "U33ds25": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_stop_profit": 2500.0},
        # G128: U33 with the bot sized to 1.5 / 2x the day's budget left and a $900 day guard
        "U33rm15": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult": 1.5},
        "U33rm20": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult": 2.0},
        # G129: G128b's 2x only once the floor has stopped
        "U33rm20L": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult": 2.0,
                     "room_mult_locked": True},
        # G130: the guard once the floor has stopped, 2x from $6,000 above it
        "U33g130": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult": 2.0,
                    "room_mult_room": 6000.0, "day_guard_locked": True},
        "U33g131": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult": 2.0,
                    "room_mult_room": 3000.0, "day_guard_locked": True},
        "U33rm3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult_room": 3000.0, "day_guard_locked": True, "room_mult": 3.0},
        "U33rm4": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 900.0, "room_mult_room": 3000.0, "day_guard_locked": True, "room_mult": 4.0},
        "U33rm4s2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                     "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                     "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                     "skip_checks_early": True, "day_guard": 900.0, "room_mult_room": 3000.0, "day_guard_locked": True,
                     "room_mult": 4.0, "guard_slip_pts": 2.0},
        # G133: the guard at $950 less 2 points a contract, stressed with 2-point guard fills
        "U33g133": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "day_guard": 950.0, "guard_reserve_pts": 2.0, "room_mult_room": 3000.0,
                    "day_guard_locked": True, "room_mult": 4.0, "guard_slip_pts": 2.0},
        # G140: U33 with the trend over 100 sessions
        "U33t100": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "trend_n": 100},
        # G142: U33 with a contract per $750 above $10,000 of profit
        "U33fs": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                  "skip_checks_early": True, "profit_step_fast": 750.0},
        # G145 k9: U34 with a contract per $1,250, per $600 above $10,000, the brake at 0.4
        "U34k9": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                  "giveback_brake": 0.4, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                  "skip_checks_early": True, "profit_step": 1250.0, "profit_step_fast": 600.0},
        # G146: U34 with a contract per $600 above $10,000 and the brake at 0.4
        "U34g146": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.4, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "profit_step_fast": 600.0},
        # G148: U34 with G131's 2x room and day guard, judged with the guard's fills 2 points worse
        "U34g148": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                    "fill_min_room": 3000.0, "size_slip_pts": 4.0, "gap_go_locked_qty": 10, "fill_qty2_room": 6000.0,
                    "giveback_brake": 0.5, "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870",
                    "skip_checks_early": True, "profit_step_fast": 750.0, "day_guard": 900.0, "room_mult": 2.0,
                    "room_mult_room": 3000.0, "day_guard_locked": True, "guard_slip_pts": 2.0}}
for pk in (sys.argv[4].split(",") if len(sys.argv) > 4 else list(PACK)):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "time_stop": 60, "gap_go": True, "gap_go_skip_month_first": name != "proxy",
                             "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 3, **PACK[pk]})
        if NT:
            cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if first:
            cfg.trail_from = first
        if cfg.protect_room > 0:  # G87: the shadow gate's closed days
            cfg.protect_dates = SG.closed_days(bars, cfg, S.MIN[0])
        tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        p = tf.pnl.to_numpy()
        t_ny = bars.index.tz_convert("America/New_York")
        sess = {d for d in t_ny[(t_ny.hour == 9) & (t_ny.minute == 30)].date if not first or str(d) >= first}
        traded = 100 * tf.entry_time.dt.tz_convert("America/New_York").dt.date.nunique() / max(1, len(sess))
        e = np.r_[0.0, np.cumsum(p)]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        S.TRAIL = cfg.trail_dd  # the account's own trailing drawdown, for the floor check
        print({"nt": NT, "pack": pk, "set": name, "days traded %": round(traded, 1),
               "gap trades": int(tf.reason.str.startswith("Gap").sum()), "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": S.trail_stats(name, tf)[f"{name} tb0"]}, flush=True)
