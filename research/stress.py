"""Stress tests of the bot as it trades now, on two independent datasets.

    python research/stress.py nsx_5m_scaled.pkl nq_5m_scaled.pkl

Each pickle is 5-minute bars rescaled to today's price level month by month (timeframes.scaled): the NSXUSD
index CFD 2011-2026 used in rounds 1-31, and the NQ futures 1-minute bars 2015-2025 from round 32. Per
contract: 1 MNQ, $116.67 max loss ($350 on 3), the 1.5-noise-unit take-profit, everything else at the
defaults, simulated with mnqbot.noise (the reference the Pine script is tested against).

Pass bars, fixed before running:
  costs:    2 ticks of slippage per side (double), and doubled fees: still profitable with t >= 2
  delay:    every entry filled one 5-minute bar late: still profitable
  settings: each setting nudged both ways (stop buffer 0.12 / 0.36, take-profit off / 1.0 / 2.0,
            lookback 10 / 20, max loss $80 / $160 a contract): every one profitable with t >= 2 (no cliff)
  luck:     10,000 reshuffled years (20-session blocks of the real daily P&L): reported, not judged
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

CAP = 350.0 / 3
BASE = {"qty": 1, "max_loss_per_trade": CAP, "skip_dates": "", "fed_dates": ""}
CASES = {
    "as it trades": {},
    "slippage 2 ticks a side": {"slippage_ticks": 2},
    "slippage 3 ticks a side": {"slippage_ticks": 3},
    "fees doubled": {"commission_per_side": 1.24},
    "stop buffer 0.12": {"stop_buffer": 0.12},
    "stop buffer 0.36": {"stop_buffer": 0.36},
    "take-profit off": {"take_profit": 0.0},
    "take-profit 1.0": {"take_profit": 1.0},
    "take-profit 2.0": {"take_profit": 2.0},
    "lookback 10": {"lookback": 10},
    "lookback 20": {"lookback": 20},
    "max loss $80 a contract": {"max_loss_per_trade": 80.0},
    "max loss $160 a contract": {"max_loss_per_trade": 160.0},
    "entries 5 minutes late": None,  # the research simulator, which has the delay
}
MUST = {"slippage 2 ticks a side": 2.0, "fees doubled": 2.0, "entries 5 minutes late": 0.0,
        **{k: 2.0 for k in CASES if k.startswith(("stop buffer", "take-profit", "lookback", "max loss"))}}


def _job(args):
    path, name = args
    bars = pd.read_pickle(path)
    if CASES[name] is None:
        return name, P.simulate(bars, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True, entry_delay=1)
    tf = run(bars, NoiseConfig(**{**BASE, **CASES[name]}), minutes=5).trades_frame()
    return name, tf.rename(columns={"direction": "dir"})


def sessions_of(bars: pd.DataFrame) -> tuple[pd.DatetimeIndex, set]:
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    return sessions[~sessions.isin(list(first))], first


def bootstrap(daily: pd.Series, n: int = 10_000, block: int = 20, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    x = daily.to_numpy()
    starts = rng.integers(0, len(x) - block, size=(n, math.ceil(252 / block)))
    years = np.stack([np.concatenate([x[s : s + block] for s in row])[:252] for row in starts])
    eq = years.cumsum(axis=1)
    dd = (np.maximum.accumulate(eq, axis=1) - eq).max(axis=1)
    total = years.sum(axis=1)
    return {"losing year %": 100 * (total < 0).mean(), "median year": np.median(total),
            "5th pct year": np.percentile(total, 5), "95th pct drawdown in a year": np.percentile(dd, 95)}


def main() -> None:
    out = {}
    for label, path in (("index data 2011-2026", sys.argv[1]), ("NQ futures 2015-2025", sys.argv[2])):
        bars = pd.read_pickle(path)
        sessions, first = sessions_of(bars)
        start = "2011-01-01" if "2011" in label else "2015-03-01"
        sessions = sessions[sessions >= start]
        with ProcessPoolExecutor(max_workers=4) as ex:
            runs = dict(ex.map(_job, [(path, n) for n in CASES]))
        rows = []
        for name, tf in runs.items():
            tf = MT.clean(tf, first)
            tf = tf[tf.entry_time.dt.tz_localize(None) >= pd.Timestamp(start)]
            s = MT.stats(tf, sessions)
            bar = MUST.get(name)
            ok = "" if bar is None else ("PASS" if s["$/day"] > 0 and s["t"] >= bar else "FAIL")
            rows.append((name, len(tf), s["win %"], s["$/day"], s["t"], s["worst stretch"], ok))
            if name == "as it trades":
                daily = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum()
                out[label] = bootstrap(daily.reindex(sessions).fillna(0.0))
        df = pd.DataFrame(rows, columns=["case", "trades", "win %", "$/day", "t", "worst stretch", "bar"])
        print(f"\n== {label}, per contract")
        print(df.round(2).to_string(index=False))
    print("\n== 10,000 reshuffled years, per contract")
    print(pd.DataFrame(out).round(1).to_string())


if __name__ == "__main__":
    main()
