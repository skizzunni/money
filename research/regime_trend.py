"""Regime-conditional afternoon trend: the one family that survived discovery3.py. One final test.

    python research/regime_trend.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

What survived (2011-2018 discovery, 2019-2022 confirmation): when the overnight range is wide, or the
last month is down, price on the far side of the day's average (TWAP) or the open at 11:30-13:30 keeps
going into the close. Unconditionally the same idea failed its final test in afternoon.py.

Fixed before running:
  * One trade a day: at the entry time, go in the direction of price vs TWAP (since 09:30), hold to the
    16:00 close. 1 MNQ at the last price in the data, $1.24 fees + 1 tick each way.
  * Regimes use the cut-offs the discovery used: the 2011-2018 median of the overnight range (as a share
    of the previous close) and of the last 20 sessions' move.
  * Candidates: entry 13:30 or 11:30, times regime "overnight range wide", "last month down", "either".
  * Pick the highest 2011-2022 t-stat of daily P&L (those years were used to find the idea, so the bar is
    t >= 3). The pick runs once on 2023 - Sep 2026 and passes at t >= 2.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import discovery3 as D3  # noqa: E402
import noise_tuning as T  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

ENTRIES = {"13:30": D.CHECKS.index(240), "11:30": D.CHECKS.index(120)}  # half-hour slot index


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional, cost = ref * 2.0, 2 * 0.25 * 2.0 + 1.24
    feats, targets, meta = D.build(raw)
    days = L.Days(raw)
    feats.update(D3.overnight_features(raw, days, len(D.CHECKS)))
    year = meta.year.to_numpy()
    ok = meta.ok.to_numpy()
    disc = ok & (year >= 2011) & (year < 2019)
    fit = ok & (year >= 2011) & (year < 2023)
    test = ok & (year >= 2023)
    on_rng, month = feats["overnight_range"][:, 0], feats["last_month_move"][:, 0]
    wide = on_rng > np.nanmedian(on_rng[disc])
    down = month <= np.nanmedian(month[disc])
    regimes = {"overnight range wide": wide, "last month down": down, "either": wide | down}

    def day_pnl(entry_k: int, mask: np.ndarray, rows: np.ndarray):
        side = np.sign(feats["distance_from_twap"][:, entry_k])
        pos = np.where(mask, side, 0.0)
        r = targets["close"][:, entry_k]
        pnl = np.where(np.isnan(r), 0.0, pos * r * notional - np.abs(pos) * cost)
        # worst intraday dip from the entry price to the close, for the evaluation simulation
        m = D.CHECKS[entry_k]
        entry = np.where(np.isnan(days.o[:, m]), days.cf[:, m - 1], days.o[:, m])
        lo = np.nanmin(days.l[:, m:], axis=1)
        hi = np.nanmax(days.h[:, m:], axis=1)
        adverse = np.where(pos > 0, lo / entry - 1, np.where(pos < 0, 1 - hi / entry, 0.0))
        dip = np.where(np.isnan(adverse), 0.0, adverse) * notional - np.abs(pos) * cost
        worst = np.minimum(dip, np.minimum(pnl, 0))
        df = pd.DataFrame({"pnl": pnl[rows], "worst": worst[rows], "trades": np.abs(pos[rows])},
                          index=pd.Index(meta.day.to_numpy()[rows]))
        return df

    def tstat(s: pd.Series) -> float:
        return s.mean() / s.std(ddof=1) * math.sqrt(len(s))

    print(f"1 MNQ at {ref:,.0f}; sessions: 2011-2022 {int(fit.sum())}, 2023-2026 {int(test.sum())}")
    print(f"{'candidate':42s} {'days traded':>11s} {'$/day':>8s} {'t 2011-22':>9s}")
    best, best_t = None, -math.inf
    for ename, k in ENTRIES.items():
        for rname, mask in list(regimes.items()) + [("no filter (reference)", np.ones(len(ok), bool))]:
            df = day_pnl(k, mask, np.flatnonzero(fit))
            t = tstat(df.pnl)
            print(f"{ename} {rname:36s} {100 * df.trades.mean():>10.0f}% {df.pnl.mean():>+8.2f} {t:>9.2f}")
            if rname != "no filter (reference)" and t > best_t:
                best, best_t = (ename, rname, k, mask), t
    ename, rname, k, mask = best
    if best_t < 3:
        print(f"\nBest candidate t {best_t:.2f} < 3: nothing goes to the final test.")
        return
    df = day_pnl(k, mask, np.flatnonzero(test))
    t = tstat(df.pnl)
    traded = df[df.trades > 0]
    yrs = df.pnl.groupby(df.index.map(lambda d: d.year)).sum().round(0).astype(int)
    p, q = T.eval_odds(df)
    print(f"\nPicked: {ename}, {rname} (2011-22 t {best_t:.2f}).")
    print(f"FINAL TEST 2023 - Sep 2026: {len(df)} sessions, traded {100 * df.trades.mean():.0f}% of days, "
          f"${df.pnl.mean():+.2f}/day, t {t:+.2f}, win {100 * (traded.pnl > 0).mean():.0f}%, "
          f"worst dip ${df.worst.min():,.0f}, by year {yrs.to_dict()} -> {'PASS' if t >= 2 else 'FAIL'}")
    print(f"$25K evaluation, 125 sessions from every 2023-2026 start: pass {100 * p:.0f}%, fail {100 * q:.0f}%")
    full = day_pnl(k, mask, np.flatnonzero(ok & (year >= 2011)))
    p, q = T.eval_odds(full)
    yrs = full.pnl.groupby(full.index.map(lambda d: d.year)).sum().round(0).astype(int)
    stretch = (full.pnl.cumsum().cummax() - full.pnl.cumsum()).max()
    print(f"All years 2011-2026: ${full.pnl.mean():+.2f}/day, t {tstat(full.pnl):+.2f}, years up "
          f"{int((yrs > 0).sum())}/{len(yrs)}, max losing stretch ${stretch:,.0f}, "
          f"eval pass {100 * p:.0f}% / fail {100 * q:.0f}%")
    print(f"  by year {yrs.to_dict()}")


if __name__ == "__main__":
    main()
