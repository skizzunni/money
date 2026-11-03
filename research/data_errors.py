"""Data errors: a regular-hours bar whose open is more than 1.2% from the last bar's close in the same session, the
mark of two contracts mixed in one session (found 2026-11-03 on 2025-06-20, see docs/NINJATRADER_V38.md, G67). The
sets are as research/v24_scan.py loads them (its BAD_SESSIONS already dropped, so a clean run lists only real moves).

    python research/data_errors.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import v24_scan as S

S.init({}, *sys.argv[1:4])
for name, (bars, _, _) in S.D.items():
    t = bars.index.tz_convert("America/New_York")
    m = t.hour * 60 + t.minute
    rth = (m >= 570) & (m < 960)
    b, tt = bars[rth], t[rth]
    o, c = b.open.to_numpy(), b.close.to_numpy()
    same = np.r_[False, tt.date[1:] == tt.date[:-1]]
    jump = np.r_[0, np.abs(o[1:] / c[:-1] - 1)]
    k = np.where(same & (jump > 0.012))[0]
    print(name, len(k), "jumps")
    for i in k:
        vol = b.volume.iloc[i] if "volume" in b else ""
        print("  ", tt[i], f"{100 * jump[i]:.2f}%", c[i - 1], "->", o[i], "volume", vol)
