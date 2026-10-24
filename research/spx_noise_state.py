"""The S&P 500's noise state at every half-hour check (research option confirm_map in mnqbot/noise.py; docs/RESULTS.md,
v2.8 study): the same noise area as the strategy (14 sessions) on the S&P 500 index's regular-hours 5-minute bars
(HistData SPXUSD, raw prices), and whether each check's close is above its upper line (1), below its lower (-1) or
inside (0).

    python research/spx_noise_state.py <spx1m.pkl> <out.pkl>
"""
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"


def main() -> None:
    raw = pd.read_pickle(sys.argv[1])
    t = raw.index.tz_convert(NY)
    tm = t.hour * 60 + t.minute
    rth = raw[(tm >= 570) & (tm < 960)]
    bars = resample(rth.assign(volume=rth.get("volume", 0.0)), "5min")
    res = run(bars, NoiseConfig(skip_dates="", fed_dates=""), minutes=5)
    idx = bars.index.tz_convert(NY)
    c = bars["close"].to_numpy(float)
    state = {}
    for i, up, lo in res.bands:
        ti = idx[i]
        key = (ti.strftime("%Y-%m-%d"), ti.hour * 60 + ti.minute + 5)
        state[key] = 1 if c[i] > up else -1 if c[i] < lo else 0
    with open(sys.argv[2], "wb") as f:
        pickle.dump(state, f)
    s = pd.Series(state)
    print(len(s), s.value_counts().to_dict(), min(k[0] for k in state), max(k[0] for k in state))


if __name__ == "__main__":
    main()
