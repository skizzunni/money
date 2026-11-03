"""research/replay_day.py (U12): a day's replay from a NinjaTrader MNQ export equals the Python model's trades on it,
the chart page is written, and two contracts are joined at the roll with the older back-adjusted."""
from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT)]
import replay_day as R  # noqa: E402

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

SAMPLE = ROOT / "tests" / "data" / "mnq_traded_2026-06-29_2026-10-16.csv.gz"


def sample() -> pd.DataFrame:
    b = pd.read_csv(gzip.open(SAMPLE, "rt"), header=None, names=["t", "open", "high", "low", "close"])
    b.index = pd.to_datetime(b.pop("t")).dt.tz_localize("America/New_York")
    return b.assign(volume=1)


def export(bars: pd.DataFrame, path: Path) -> None:
    """As NinjaTrader exports: UTC, each bar's end."""
    end = (bars.index + pd.Timedelta(minutes=1)).tz_convert("UTC").strftime("%Y%m%d %H%M%S")
    with path.open("w") as f:
        for t, r in zip(end, bars.itertuples(), strict=True):
            f.write(f"{t};{r.open};{r.high};{r.low};{r.close};{r.volume}\n")


def test_replay_matches_the_model(tmp_path):
    one = sample()
    export(one, tmp_path / "MNQ.txt")
    day = "2026-10-16"
    r = subprocess.run([sys.executable, str(ROOT / "research" / "replay_day.py"), str(tmp_path / "MNQ.txt"), day,
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    bars = resample(one[(one.index.hour * 60 + one.index.minute >= 570)
                        & (one.index.hour * 60 + one.index.minute <= 960)], "5min")
    tf = run(bars, NoiseConfig(**R.GROWTH_1), minutes=5).trades_frame()
    tf = tf[tf.entry_time.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d") == day]
    assert len(tf) >= 2
    lines = [x for x in r.stdout.splitlines() if x.startswith("  LONG") or x.startswith("  SHORT")]
    assert len(lines) == len(tf)
    for x, t in zip(lines, tf.itertuples(), strict=True):
        assert f"{t.entry:.2f}" in x and f"{t.exit:.2f}" in x and t.reason in x and f"${abs(t.pnl):.2f}" in x, x
    page = (tmp_path / f"replay_{day}.html").read_text()
    assert "<svg" in page and page.count("<tr>") == len(tf) + 1 and f"${abs(tf.pnl.sum()):.2f} per MNQ" in page


def test_two_contracts_join_at_the_roll(tmp_path):
    """The newer contract 100 points above the older: the older is lifted by 100 up to the roll, so the joined series
    is the newer contract's prices throughout."""
    one = sample()
    old, new = one[one.index < "2026-09-20"], one[one.index >= "2026-09-10"].copy()
    new[["open", "high", "low", "close"]] += 100.0
    export(old, tmp_path / "old.txt")
    export(new, tmp_path / "new.txt")
    joined = R.load([str(tmp_path / "new.txt"), str(tmp_path / "old.txt")])  # either order
    want = resample(one[(one.index.hour * 60 + one.index.minute >= 570)
                        & (one.index.hour * 60 + one.index.minute <= 960)], "5min")
    pd.testing.assert_series_equal(joined.close, want.close + 100.0, check_freq=False)
