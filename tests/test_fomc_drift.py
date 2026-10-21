"""The pre-FOMC drift: ninjatrader/Strategies/MnqFomcDrift.cs on the NinjaTrader stand-in against mnqbot/fomc.py,
trade for trade, on the user's MNQ bars (full electronic session, the 2026 FOMC dates) and on synthetic sessions
checked against hand-computed values (the entry at 14:00 the weekday before, Friday to Monday, the 13:55 exit, the
catastrophe stop, a gap through it, $2 a point and $0.95 a side)."""
from __future__ import annotations

import gzip
import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import controlled as K  # noqa: E402

from mnqbot.fomc import trades  # noqa: E402
from mnqbot.noise import FED_DATES  # noqa: E402

SAMPLE = ROOT / "tests" / "data" / "mnq_traded_eth_2026-06-28_2026-10-16.csv.gz"
SAMPLE_SHA256 = "66169bfa73c954a06442299f3ebc2fce6c29550e86a99caade65dc5fb7e23892"
NY = "America/New_York"
needs_dotnet = pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
COLS = ["d", "eb", "en", "xb", "ex", "why", "pnl", "q"]


def stand_in(sim, frame, tmp_path, **props):  # noqa: F811
    csv = tmp_path / "bars.csv"
    K.write_bars(frame, csv)
    base = {"SimSlippageTicks": 2, "SimCommissionPerSide": 0.95}
    base.update(props)
    r = subprocess.run([DOTNET, str(sim), str(csv), "1", "Strategy=FOMC", *[f"{k}={v}" for k, v in base.items()]],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    rows = [{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]), "why": a[5],
             "pnl": float(a[6]), "q": int(b[1])} for a, b in zip(t, n, strict=True)]
    return pd.DataFrame(rows, columns=COLS), r.stdout


def py(frame, fed, **kw):
    return pd.DataFrame(trades(frame, set(fed.split(",")), **kw), columns=COLS)


def same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if len(a) != len(b):
        return False
    a, b = a.round(6).astype(str), b.round(6).astype(str)
    return bool((a.values == b.values).all())


@pytest.fixture(scope="module")
def mnq():
    raw = gzip.decompress(SAMPLE.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == SAMPLE_SHA256
    bars = pd.read_csv(pd.io.common.BytesIO(raw), header=None, names=["t", "open", "high", "low", "close"])
    bars.index = pd.to_datetime(bars.pop("t")).dt.tz_localize(NY)
    return bars


@needs_dotnet
def test_agrees_on_mnq(sim, mnq, tmp_path):  # noqa: F811
    """The 7/29 and 9/16/2026 announcements: in at 14:00 on 7/28 and 9/15, out at 13:55 on the day."""
    nt, _ = stand_in(sim, mnq, tmp_path, FedDates=FED_DATES)
    p = py(mnq, FED_DATES)
    assert same(nt, p) and len(p) == 2
    when = [(mnq.index[r.eb].strftime("%m-%d %H:%M"), mnq.index[r.xb].strftime("%m-%d %H:%M")) for r in p.itertuples()]
    assert when == [("07-28 14:00", "07-29 13:55"), ("09-15 14:00", "09-16 13:55")]
    assert set(p.why) == {"FOMC exit"}


def eth(days: list[str], price: float) -> dict:
    """Electronic sessions: each day's 18:00 (the evening before) to 16:59, flat at the price, a 0.25 range."""
    rows = {}
    for d in days:
        t, end = pd.Timestamp(d, tz=NY) - pd.Timedelta(hours=6), pd.Timestamp(d, tz=NY) + pd.Timedelta(hours=17)
        while t < end:
            rows[t] = (price, price + 0.25, price - 0.25, price)
            t += pd.Timedelta(minutes=1)
    return rows


def frame(rows: dict) -> pd.DataFrame:
    idx = sorted(rows)
    return pd.DataFrame([rows[t] for t in idx], index=pd.DatetimeIndex(idx), columns=["open", "high", "low", "close"])


@needs_dotnet
def test_friday_to_monday_and_the_exit_before_the_statement(sim, tmp_path):  # noqa: F811
    """A Monday 'announcement' (2026-03-09): bought Friday 3/6 at the 14:00 open 20000 + 2 ticks = 20000.50, held over
    the weekend; the 13:55 bar on Monday opens at 20100: sold at 20099.50. 2 MNQ: 2 x ((20099.50 - 20000.50) x $2 -
    $1.90) = $392.20."""
    rows = eth(["2026-03-05", "2026-03-06", "2026-03-09", "2026-03-10"], 20000.0)
    for t in [x for x in rows if x >= pd.Timestamp("2026-03-09 09:30", tz=NY)]:
        rows[t] = (20100.0, 20100.25, 20099.75, 20100.0)
    f = frame(rows)
    nt, _ = stand_in(sim, f, tmp_path, FedDates="2026-03-09")
    p = py(f, "2026-03-09")
    assert same(nt, p) and len(p) == 1
    r = p.iloc[0]
    assert f.index[r.eb] == pd.Timestamp("2026-03-06 14:00", tz=NY)
    assert f.index[r.xb] == pd.Timestamp("2026-03-09 13:55", tz=NY)
    assert (r.en, r.ex, r.why, round(r.pnl, 2)) == (20000.5, 20099.5, "FOMC exit", 392.2)


@needs_dotnet
@pytest.mark.parametrize("gap", [False, True])
def test_catastrophe_stop(sim, tmp_path, gap):  # noqa: F811
    """Stop 0.5% of the 13:59 close 20000 = 400 ticks = 100 points under the 20000.50 fill: 19900.50. A bar trading to
    19890 fills it at 19900.50 - 2 ticks = 19900.00; a bar opening at 19800 (a gap through it) fills at 19799.50."""
    rows = eth(["2026-03-09", "2026-03-10", "2026-03-11"], 20000.0)
    t = pd.Timestamp("2026-03-10 03:00", tz=NY)
    rows[t] = (19800.0, 19801.0, 19790.0, 19800.0) if gap else (20000.0, 20000.0, 19890.0, 19950.0)
    f = frame(rows)
    nt, _ = stand_in(sim, f, tmp_path, FedDates="2026-03-10", CatastropheStopPct=0.5)
    p = py(f, "2026-03-10", stop_pct=0.5)
    assert same(nt, p) and len(p) == 1
    r = p.iloc[0]
    assert (r.why, r.ex) == ("Stop loss", 19799.5 if gap else 19900.0)
    assert f.index[r.xb] == t
