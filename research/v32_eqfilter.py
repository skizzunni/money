"""An equity-curve filter on the noise strategy (docs/RESULTS.md, after v3.1): a shadow run takes every signal at 1
contract with no loss limits; the real run trades a day only if the shadow's closed P/L at the previous day's end is
at or above its average over the last n days (or skips the days below it). Two passes through mnqbot.noise.run, the
second skipping the filtered days through skip_dates.

    python research/v32_eqfilter.py '<base: JSON overrides>' <out.csv> <data dir> \
        <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
SCAN_MINUTES=30 (environment): 30-minute bars.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
SHADOW_OFF = {"daily_loss_limit": 0.0, "trail_dd": 0.0, "profit_step": 0.0, "qty": 1, "squeeze_min": 0.0}


def blocked_days(bars: pd.DataFrame, cfg: NoiseConfig, m: int, n: int) -> set[str]:
    """The sessions whose previous end-of-day shadow equity was under its n-day average."""
    tf = run(bars, cfg, minutes=m).trades_frame()
    days = sorted(set(bars.index.tz_convert(NY).strftime("%Y-%m-%d")))
    eod = pd.Series(0.0, index=days)
    if len(tf):
        pnl = tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.strftime("%Y-%m-%d")).pnl.sum()
        eod = eod.add(pnl, fill_value=0.0)
    eq = eod.cumsum()
    ma = eq.rolling(n, min_periods=n).mean()
    ok = (eq >= ma).shift(1, fill_value=True)  # yesterday's state decides today
    return set(ok.index[~ok.astype(bool)])


def main() -> None:
    base, out = json.loads(sys.argv[1]), sys.argv[2]
    m = int(os.environ.get("SCAN_MINUTES", "5"))
    S.init({}, *sys.argv[3:6])
    rows = []
    for n in (0, 10, 20, 40, 60):
        r = {"n": n}
        for name, (bars, first, skip) in S.D.items():
            cfg = NoiseConfig(**{**S.V23, **base})
            if isinstance(skip, str):
                cfg.skip_dates, cfg.fed_dates = skip, ""
            if cfg.trail_dd > 0 and first:
                cfg.trail_from = first
            if n:
                shadow = NoiseConfig(**{**cfg.__dict__, **SHADOW_OFF})
                cfg.skip_dates = cfg.skip_dates + "," + ",".join(sorted(blocked_days(bars, shadow, m, n)))
            tf = run(bars, cfg, minutes=m).trades_frame()
            if first:
                tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
            p = tf.pnl.to_numpy()
            e = p.cumsum()
            r.update({f"{name} net": round(p.sum()), f"{name} n": len(p),
                      f"{name} win": round(100 * (p > 0).mean(), 1) if len(p) else 0,
                      f"{name} pf": round(p[p > 0].sum() / max(1e-9, -p[p < 0].sum()), 3),
                      f"{name} dd": round(max(0.0, (pd.Series(e).cummax().clip(lower=0) - e).max())) if len(p) else 0})
            r.update(S.trail_stats(name, tf))
        rows.append(r)
        print(r, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
