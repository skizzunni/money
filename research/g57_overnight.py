"""G57 (docs/NINJATRADER_V38.md): Funded growth's rules on the overnight sessions (Asia 18:00-00:30, London
02:00-08:30 New York), each shifted onto a 09:30-16:00 clock so the day bot's model runs it unchanged.

    python research/g57_overnight.py <data dir>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
D = sys.argv[1]
SESSIONS = {"asia": (18 * 60, pd.Timedelta(hours=-8, minutes=-30)),  # 18:00 -> 09:30, same date
            "london": (2 * 60, pd.Timedelta(hours=7, minutes=30))}   # 02:00 -> 09:30, same date


def shifted(bars: pd.DataFrame, start_min: int, shift: pd.Timedelta) -> pd.DataFrame:
    """The 6.5 hours from start_min, moved onto 09:30-16:00 (the 16:00 bar at the session's last price added)."""
    t = bars.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    end = start_min + 390
    if end <= 1440:
        keep = (m >= start_min) & (m < end)
    else:
        keep = (m >= start_min) | (m < end - 1440)
    b = bars[keep].copy()
    loc = b.index.tz_convert(NY).tz_localize(None) + shift
    b.index = loc.tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    b = b[b.index.notna()]
    b = b[~b.index.duplicated()].sort_index()
    tt = b.index.tz_convert(NY)
    g = pd.DataFrame({"d": tt.strftime("%Y-%m-%d"), "m": tt.hour * 60 + tt.minute}).groupby("d").m.agg(
        ["count", "min", "max"])
    bad = set(g[(g["max"] < 955) | (g["min"] > 570) | (g["count"] < 70)].index)
    last = b[(tt.hour * 60 + tt.minute) == 955].copy()
    last.index = last.index + pd.Timedelta(minutes=5)
    for k in ("open", "high", "low"):
        last[k] = last["close"]
    return pd.concat([b, last]).sort_index(), bad


def stats(tf, first, last):
    x = tf[(tf.entry_time >= pd.Timestamp(first, tz=NY)) & (tf.entry_time < pd.Timestamp(last, tz=NY))]
    p = x.pnl.to_numpy()
    if not len(p):
        return {"trades": 0}
    e = np.r_[0.0, np.cumsum(p)]
    peak = np.maximum.accumulate(e)
    room = e - np.minimum(peak - 2000.0, 0.0)
    return {"trades": len(p), "net $": round(float(p.sum())), "win %": round(100 * float((p > 0).mean()), 1),
            "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 2) if (p <= 0).any() else None,
            "closed dd $": round(float((peak - e).max())), "lowest room $": round(float(room.min()))}


SETS = (("nq", f"{D}/nq5m_scaled.pkl", (("2015-01-01", "2020-01-01"), ("2020-01-01", "2025-08-01"))),
        ("index", f"{D}/bars5_scaled.pkl", (("2011-01-01", "2019-01-01"), ("2019-01-01", "2026-10-01"))))
for set_name, path, halves in SETS:
    raw = pd.read_pickle(path)[["open", "high", "low", "close"]]
    for sess, (start_min, shift) in SESSIONS.items():
        bars, bad = shifted(raw, start_min, shift)
        for first, last in halves:
            cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                                 "time_stop": 60, "trail_from": first})
            cfg.tv_path = False
            cfg.skip_dates = ",".join(sorted(bad))
            cfg.fed_dates = ""
            b = bars[(bars.index >= pd.Timestamp(first, tz=NY) - pd.Timedelta(days=150))
                     & (bars.index < pd.Timestamp(last, tz=NY))]
            tf = run(b, cfg, minutes=5).trades_frame()
            print({"set": set_name, "session": sess, "period": f"{first[:4]}-{last[:4]}", **stats(tf, first, last)},
                  flush=True)
