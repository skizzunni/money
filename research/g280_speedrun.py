"""G280 (docs/NINJATRADER_V38.md): the "speedrun" from the user's video, measured. One all-in bracket per attempt.

Each NQ session 2015-2025 is one attempt: the bot's first entry of the day (U53's signal settings, k317, 5-minute
bars) opens a bracket with the stop S points and the target R x S points away (S = the account's drawdown over the
size; R = the target over the drawdown, e.g. 1.25 for a $1,250 target on a $1,000 drawdown). Walked on 1-minute bars
from the entry; a minute reaching both counts the stop; still open at 16:00 counts as neither. The same entries in the
opposite direction give the coin-flip baseline. Reported: win %, loss %, and the fee per pass (1 / win %).

    python research/g280_speedrun.py <data dir> <MNQ 09-26> <MNQ 12-26>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
K317 = {"lookback": 18, "entry_k": 0.7, "range_pos_min": 0.7, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2,
        "skip_checks": "", "max_losers": 3, "time_stop": 30, "trend_n": 0, "big_day_k": 0.0, "stop_buffer": 0.24,
        "lock_plus": 2.5, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go": False}
STOPS = (25.0, 50.0, 100.0)
RATIOS = (1.0, 1.25, 1.5)


def main() -> None:
    S.init({}, *sys.argv[1:4])
    bars, _, skip = S.D["nq"]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 0.0, "trail_dd": 0.0, "qty": 1, **K317})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    tf["day"] = tf.entry_time.dt.tz_convert(NY).dt.date
    first = tf.sort_values("entry_time").groupby("day").first()
    m1 = pd.read_pickle(f"{sys.argv[1]}/nq1m_scaled.pkl")[["high", "low"]]
    t = m1.index.tz_convert(NY)
    m1 = m1[(t.hour * 60 + t.minute >= 570) & (t.hour * 60 + t.minute < 960)]
    days = pd.Series(m1.index.tz_convert(NY).date, index=m1.index)
    groups = {d: g for d, g in m1.groupby(days.values)}
    rows = []
    for day, r in first.iterrows():
        g = groups.get(day)
        if g is None:
            continue
        g = g[g.index >= r.entry_time]
        hi, lo = g.high.to_numpy(), g.low.to_numpy()
        for sgn, side in ((r.direction, "bot"), (-r.direction, "opposite")):
            for s_pts in STOPS:
                for ratio in RATIOS:
                    tp = r.entry + sgn * ratio * s_pts
                    sl = r.entry - sgn * s_pts
                    hit_s = (lo <= sl) if sgn > 0 else (hi >= sl)
                    hit_t = (hi >= tp) if sgn > 0 else (lo <= tp)
                    i_s = int(np.argmax(hit_s)) if hit_s.any() else 10 ** 9
                    i_t = int(np.argmax(hit_t)) if hit_t.any() else 10 ** 9
                    res = "open" if i_s == i_t == 10 ** 9 else ("win" if i_t < i_s else "loss")
                    rows.append({"year": day.year, "side": side, "stop": s_pts, "ratio": ratio, "res": res})
    d = pd.DataFrame(rows)
    d.to_csv("verification/noise_v2/g280_speedrun.csv", index=False)
    out = d.groupby(["side", "stop", "ratio"]).res.value_counts(normalize=True).unstack().fillna(0).round(3)
    out["attempts per pass"] = (1 / out["win"]).round(1)
    print(f"{len(first)} sessions with a bot entry, NQ 2015-25\n" + out.to_string(), flush=True)
    late = d[d.year >= 2020].groupby(["side", "stop", "ratio"]).res.value_counts(normalize=True).unstack().fillna(0)
    print("\n2020-25 only:\n" + late.round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
