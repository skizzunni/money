"""The v2.4 study (docs/RESULTS.md): variants of the noise strategy's settings and research options on four sets of
5-minute bars: the user's chart window (MNQ, trades from 2026-08-24), the long-view stand-in (research/v24_proxy.py,
trades from 2025-01-02), NQ futures 2015-2025 and the Nasdaq-100 index 2011-2026 (both scaled to today's price level).

    python research/v24_scan.py '<variants: JSON list of NoiseConfig overrides>' <out.csv> '<base: JSON overrides>' \
        <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>

The first row is the base (v2.3's settings plus the base overrides); each variant adds its overrides to the base. A
position closed in parts counts as one trade for drawdown and losing streaks; winners, profit factor and trade
counts take each exit, as TradingView's strategy tester does. For the histories: net and net per drawdown against the
base's, and the years in which the variant beat it. SCAN_MINUTES=30 (environment)
resamples every set to 30-minute bars (the stand-in from proxy_30m.pkl).
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v18_scan as V  # noqa: E402
from v21_streak_scan import streak  # noqa: E402

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
V23 = {"qty": 10, "max_loss_per_trade": 500.0, "tighten_only": True, "take_profit": 2.0, "lock_at": 0.75,
       "max_losers": 4, "after_loss_qty_div": 10 / 9, "after_loss_ml_mult": 1.4, "last_entry_end": 900,
       "big_day_k": 1.5, "big_day_n": 10}
V24 = {**V23, "max_loss_per_trade": 1500.0, "lock_at": 0.5, "max_losers": 3}  # the Pine script's defaults since v2.4
D: dict = {}
BASE: dict = {}
MIN = [5]  # the bar length: SCAN_MINUTES=30 runs every set on 30-minute bars


def init(base: dict, data: str, sep: str, dec: str) -> None:
    BASE.update(base)
    MIN[0] = int(os.environ.get("SCAN_MINUTES", "5"))
    V.init([sep, dec, f"{data}/nq5m_scaled.pkl", f"{data}/bars5_scaled.pkl"])
    m = MIN[0]

    def bars(b: pd.DataFrame) -> pd.DataFrame:
        return b if m == 5 else resample(b, f"{m}min")
    D["win"] = (bars(V.DATA["mnq"][0]), "2026-08-24", True)
    D["proxy"] = (pd.read_pickle(f"{data}/proxy_{m}m.pkl"), "2025-01-02", True)
    D["nq"] = (bars(V.DATA["nq"][0]), None, False)
    D["index"] = (bars(V.DATA["index"][0]), None, False)


def job(kw: dict) -> dict:
    out = {"rule": json.dumps(kw) if kw else "base"}
    for name, (bars, first, keep_dates) in D.items():
        cfg = NoiseConfig(**{**V23, **BASE, **kw})
        if not keep_dates:
            cfg.skip_dates, cfg.fed_dates = "", ""
        tf = run(bars, cfg, minutes=MIN[0]).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
        p = tf.groupby("exit_bar", sort=True).pnl.sum().to_numpy()  # one trade per position
        lg = tf.pnl.to_numpy()  # each exit, as TradingView lists them (a partial exit is a trade)
        e = np.r_[0, np.cumsum(p)]
        out.update({f"{name} net": round(p.sum()), f"{name} dd": round((np.maximum.accumulate(e) - e).max()),
                    f"{name} win": round(100 * (tf.pnl > 0).mean(), 1),
                    f"{name} pf": round(lg[lg > 0].sum() / -lg[lg < 0].sum(), 3), f"{name} n": len(lg),
                    f"{name} streak": streak(p)})
        if name in ("nq", "index"):
            out[f"{name} yrs"] = json.dumps(tf.groupby(tf.entry_time.dt.year).pnl.sum().round().astype(int).tolist())
    return out


def main() -> None:
    variants, out, base = json.loads(sys.argv[1]), Path(sys.argv[2]), json.loads(sys.argv[3])
    with ProcessPoolExecutor(4, initializer=init, initargs=(base, *sys.argv[4:7])) as ex:
        rows = list(ex.map(job, [{}] + variants))
    d = pd.DataFrame(rows)
    b = d.iloc[0]
    for k in ("nq", "index"):
        d[f"{k} r/b"] = ((d[f"{k} net"] / d[f"{k} dd"]) / (b[f"{k} net"] / b[f"{k} dd"])).round(2)
        d[f"{k} net/b"] = (d[f"{k} net"] / b[f"{k} net"]).round(2)
        by = np.array(json.loads(b[f"{k} yrs"]))
        d[f"{k} yrs+"] = [int((np.array(json.loads(x)) > by).sum()) for x in d[f"{k} yrs"]]
    d.to_csv(out, index=False)
    pd.set_option("display.width", 320)
    pd.set_option("display.max_colwidth", 80)
    print(d[["rule", "win net", "win dd", "win win", "proxy net", "proxy dd", "proxy win", "proxy pf", "proxy streak",
             "nq net/b", "nq r/b", "nq yrs+", "nq pf", "index net/b", "index r/b", "index yrs+", "index pf"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
