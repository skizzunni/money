"""v2.2 against variants of its settings and the research-only options of mnqbot/noise.py, on the user's TradingView
window (trades from 8/24/2026) and NQ 2015-2025 / index 2011-2026 (docs/RESULTS.md, v2.3 studies).

    python research/v23_scan.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <nq5m_scaled.pkl> <bars5_scaled.pkl> \
        <out.csv> <set>

Sets: "dials" (lookback, stop buffer, entry band, late take-profit), "risk" (max loss, take-profit and after-loss max
loss together), "bigday" (no entries in a big session's direction the next day). Net, closed-trade drawdown, win
rate, longest losing streak and back-to-back rate; for the histories, net per drawdown against v2.2's, the years in
which a variant beat it, and each history's early and late halves.
"""
from __future__ import annotations

import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v18_scan as V  # noqa: E402
from v21_streak_scan import streak  # noqa: E402
from v22_after_loss import back_to_back  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

V22 = {"qty": 10, "max_loss_per_trade": 500.0, "tighten_only": True, "take_profit": 2.0, "lock_at": 0.75,
       "max_losers": 4, "after_loss_qty_div": 10 / 9, "after_loss_ml_mult": 1.4, "last_entry_end": 900}


def sets() -> dict[str, list[dict]]:
    dials = ([{"lookback": k} for k in (10, 20)] + [{"stop_buffer": k} for k in (0.0, 0.5, 1.0)]
             + [{"entry_k": k} for k in (0.9, 1.1, 1.25)]
             + [{"late_tp": t, "late_tp_from": f} for t, f in ((1.5, 840), (1.25, 840), (1.5, 780))])
    risk = [{"max_loss_per_trade": ml, "take_profit": tp, "after_loss_ml_mult": aml / ml}
            for ml, tp, aml in itertools.product((475.0, 500.0, 525.0), (1.9, 2.0, 2.1), (650.0, 700.0, 750.0))
            if (ml, tp, aml) != (500.0, 2.0, 700.0)]
    bigday = [{"big_day_k": k, "big_day_n": n} for k in (1.25, 1.5, 1.75, 2.0) for n in (10, 20)]
    against = [{"big_day_k": 1.5, "big_day_n": 10, "big_day_against_tp": t} for t in (0.0, 2.5, 3.0)]
    # v2.3 with one component at a time back to its earlier value (the sets after "against" start from v2.3)
    ablate = [{"big_day_k": 1.5, "big_day_n": 10, **k} for k in (
        {"after_loss_qty_div": 1.0, "after_loss_ml_mult": 1.0}, {"last_entry_end": 0}, {"tighten_only": False},
        {"max_loss_per_trade": 350.0, "take_profit": 1.5, "lock_at": 0.85, "after_loss_qty_div": 1.0,
         "after_loss_ml_mult": 1.0}, {"max_losers": 0})]
    return {"dials": dials, "risk": risk, "bigday": bigday, "against": against, "ablate": ablate}


def job(kw: dict) -> dict:
    out = {"rule": json.dumps(kw) if kw else "v2.2"}
    for name, (bars, _) in V.DATA.items():
        cfg = NoiseConfig(**{**V22, **kw})
        if name != "mnq":
            cfg.skip_dates, cfg.fed_dates = "", ""
        tf = run(bars, cfg, minutes=5).trades_frame()
        if name == "mnq":
            tf = tf[tf.entry_time.dt.strftime("%Y-%m-%d") >= "2026-08-24"]
        p = tf.pnl.to_numpy()
        e = np.r_[0, np.cumsum(p)]
        out.update({f"{name} net": round(p.sum()), f"{name} dd": round((np.maximum.accumulate(e) - e).max()),
                    f"{name} n": len(p), f"{name} win": round(100 * (p > 0).mean(), 1), f"{name} streak": streak(p),
                    f"{name} b2b": round(back_to_back(p), 1)})
        if name != "mnq":
            years = tf.groupby(tf.entry_time.dt.year).pnl.sum()
            out[f"{name} 23+"] = round(tf[tf.entry_time.dt.year >= 2023].pnl.sum())
            split = 2020 if name == "nq" else 2019  # the two halves of each history
            out[f"{name} early"] = round(tf[tf.entry_time.dt.year < split].pnl.sum())
            out[f"{name} late"] = round(tf[tf.entry_time.dt.year >= split].pnl.sum())
            out[f"{name} years"] = json.dumps(years.round().astype(int).tolist())
    return out


def main() -> None:
    paths, out, which = sys.argv[1:5], Path(sys.argv[5]), sys.argv[6]
    base = [{"big_day_k": 1.5, "big_day_n": 10}] if which in ("against", "ablate") else [{}]  # v2.3 from "against"
    variants = base + sets()[which]
    with ProcessPoolExecutor(4, initializer=V.init, initargs=(paths,)) as ex:
        rows = list(ex.map(job, variants))
    d = pd.DataFrame(rows)
    b = d.iloc[0]
    for k in ("nq", "index"):
        d[f"{k} r/b"] = ((d[f"{k} net"] / d[f"{k} dd"]) / (b[f"{k} net"] / b[f"{k} dd"])).round(2)
        d[f"{k} net/b"] = (d[f"{k} net"] / b[f"{k} net"]).round(2)
        base_years = np.array(json.loads(b[f"{k} years"]))
        d[f"{k} yrs+"] = [int((np.array(json.loads(x)) > base_years).sum()) for x in d[f"{k} years"]]
    d.to_csv(out, index=False)
    pd.set_option("display.width", 340)
    pd.set_option("display.max_colwidth", 90)
    print(d[["rule", "mnq net", "mnq dd", "mnq win", "mnq streak", "nq net/b", "nq r/b", "nq yrs+", "nq early",
             "nq late", "nq 23+", "index net/b", "index r/b", "index yrs+", "index early", "index late",
             "index 23+"]].to_string(index=False))


if __name__ == "__main__":
    main()
