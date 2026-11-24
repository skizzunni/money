"""The user's TradingView window as an adoption gate (2026-11-24): Aug 27 - Nov 23 2026 on the live MNQ set, a fresh
50K, 1 / 2 / 3 contracts from +$2,000 / +$4,500, the news rule (mild: no trading, big: +1), the $600 day stop, the
take-profit from the next bar as Pine. It matched TradingView's direction for three versions (+$6,364 / +$6,421 /
+$6,068 against TradingView's +$6,322 / +$6,345 / +$5,371). A change ships only if this does not go down.
Usage: tv_window(sets["live"][0], gap=dict(...), band=dict(...))."""
from __future__ import annotations

import numpy as np
import pandas as pd
import strats as S


def tv_window(d: list, gap: dict, band: dict, start: str = "2026-08-27") -> dict:
    cum, n, w, gw, gl, peak, dd = 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0
    for i in range(21, len(d)):
        if pd.Timestamp(d[i]["d"]) < pd.Timestamp(start):
            continue
        sp = d[i]["news"][0]
        q = 3 if cum >= 4500 else 2 if cum >= 2000 else 1
        if not np.isnan(sp):
            if 2 <= sp < 3:
                continue
            if sp >= 6:
                q = min(q + 1, 3)
        legs = S.gap_go(d, i, 0.25, **gap) + S.noise(d, i, 0.25, stop_slip=1, nt=True, tp_fill_bar=False, **band)
        day = 0.0
        for side, _eb, e, x, _why, *_ in legs:
            if day <= -600:
                break
            p = ((x - e) * side * 2 - 1.24) * q
            day += p
            n += 1
            if p > 0:
                w, gw = w + 1, gw + p
            else:
                gl -= p
        cum += day
        peak, dd = max(peak, cum), max(dd, peak - cum)
    return dict(net=cum, trades=n, win=w / max(n, 1), pf=gw / max(gl, 1e-9), max_dd=dd)
