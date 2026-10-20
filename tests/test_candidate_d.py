"""Candidates D and E (docs/CANDIDATE_D.md): the NinjaScript strategy against the Python model, and every rule of the
position manager and of the sweep sequence on synthetic sequences with independently computed expectations.

- Parity: MnqCandidateD.cs on the NinjaTrader stand-in and mnqbot/candidate_d.py agree position by position (fills,
  exits, reasons, R, planned risk, P/L) on the user's MNQ bars (full electronic session), at the $125 budget and at a
  test-only $2,000 budget that makes every sleeve trade, and on the synthetic sequences.
- Causality: every decision made up to a bar is the same when the bars after it are removed.
- The position manager: two contracts within $125 all-in or no trade; the fee-aware breakeven from the actual fill;
  exactly half at +2R; the runner's 1R trail; 15:55; three campaigns a day, one at a time; overruns logged.
- Execution state (stand-in only): the pending guard until a cancellation is confirmed, a fill during a cancellation,
  one contract filled of two, the account's highest equity kept across a restart.
"""
from __future__ import annotations

import gzip
import hashlib
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import controlled as K  # noqa: E402
import d_parity as P  # noqa: E402

from mnqbot.candidate_d import DConfig, run  # noqa: E402
from mnqbot.noise import FED_DATES, SKIP_DATES  # noqa: E402

SAMPLE = ROOT / "tests" / "data" / "mnq_traded_eth_2026-06-28_2026-10-16.csv.gz"
SAMPLE_SHA256 = "66169bfa73c954a06442299f3ebc2fce6c29550e86a99caade65dc5fb7e23892"
NY = "America/New_York"
needs_dotnet = pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")


@pytest.fixture(scope="module")
def mnq(tmp_path_factory):
    raw = gzip.decompress(SAMPLE.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == SAMPLE_SHA256, "the fixed sample changed"
    bars = pd.read_csv(pd.io.common.BytesIO(raw), header=None, names=["t", "open", "high", "low", "close"])
    bars.index = pd.to_datetime(bars.pop("t")).dt.tz_localize(NY)
    return bars


# ---- synthetic minute bars ------------------------------------------------------------------------------------
class Bars:
    """09:30-15:59 sessions of 1-minute bars; every minute not set explicitly is flat at the last close."""

    def __init__(self):
        self.rows: dict[pd.Timestamp, tuple] = {}

    def day(self, date: str, price: float, rng: float = 0.5):
        t = pd.Timestamp(f"{date} 09:30", tz=NY)
        for k in range(390):
            self.rows[t + pd.Timedelta(minutes=k)] = (price, price + rng, price - rng, price)
        return self

    def bar(self, date: str, hhmm: str, o: float, h: float, l: float, c: float):
        self.rows[pd.Timestamp(f"{date} {hhmm}", tz=NY)] = (o, h, l, c)
        return self

    def hold(self, date: str, start: str, end: str, price: float, rng: float = 0.25):
        t, t1 = pd.Timestamp(f"{date} {start}", tz=NY), pd.Timestamp(f"{date} {end}", tz=NY)
        while t <= t1:
            self.rows[t] = (price, price + rng, price - rng, price)
            t += pd.Timedelta(minutes=1)
        return self

    def frame(self) -> pd.DataFrame:
        idx = sorted(self.rows)
        return pd.DataFrame([self.rows[t] for t in idx], index=pd.DatetimeIndex(idx),
                            columns=["open", "high", "low", "close"])


def both(sim, bars, tmp_path, kw, budget=125.0, extra=()):  # noqa: F811
    csv = tmp_path / "bars.csv"
    K.write_bars(bars, csv)
    nt, out = P.nt_positions(sim, csv, kw, budget, 2, extra)
    py, model = P.py_positions(bars, kw, budget, 2)
    return nt, py, model, out


# ---- parity on the user's MNQ bars ---------------------------------------------------------------------------
@needs_dotnet
@pytest.mark.parametrize("budget", [125.0, 2000.0])
@pytest.mark.parametrize("name", list(P.CONFIGS))
def test_ninjascript_and_python_agree_on_mnq(sim, mnq, tmp_path, name, budget):  # noqa: F811
    csv = tmp_path / "bars.csv"
    K.write_bars(mnq, csv)
    nt, _ = P.nt_positions(sim, csv, P.CONFIGS[name], budget)
    py, _ = P.py_positions(mnq, P.CONFIGS[name], budget)
    assert len(nt) == len(py)
    assert len(py) > 0 or (name.startswith("E only") and budget == 125.0)  # E alone never fits $125 here
    assert (nt.astype(str).values == py.astype(str).values).all()


def test_campaigns_one_at_a_time_and_at_most_three_a_day(mnq):
    led, _ = P.py_positions(mnq, {"e1": True, "e2": True}, 2000.0)
    entry = mnq.index[led.entry_bar.to_numpy()]
    days = pd.Series(1, index=(entry + pd.Timedelta(hours=6)).date).groupby(level=0).sum()
    assert days.max() <= 3 and (days == 3).any()
    assert (led.entry_bar.to_numpy()[1:] > led.exit_bar.to_numpy()[:-1]).all()  # one position at a time
    assert (led.planned.astype(float) <= 2000.0 + 1e-9).all()


def test_decisions_never_use_later_bars(mnq):
    """Causality: the model's log (entries, skips, stops, exits, cancels, every E decision) up to a bar is the same
    when every later bar is removed."""
    cfg = DConfig(e1=True, e2=True, budget=2000.0, skip_dates=frozenset(SKIP_DATES.split(",")),
                  fed_dates=frozenset(FED_DATES.split(",")))
    full = run(mnq, cfg).log
    assert any(x[1] == "E decision" for x in full) and any(x[1] == "enter" for x in full)
    rng = np.random.default_rng(7)
    for k in sorted(rng.integers(2000, len(mnq), 10)):
        cut = run(mnq.iloc[:k], cfg).log
        assert cut == [x for x in full if x[0] < k], k


# ---- the position manager, market entries (the Williams sleeve) ----------------------------------------------
def williams_setup(prev_range: float) -> Bars:
    """Day A's 09:30-16:00 range is prev_range (1000 to 1000 + prev_range). Day B opens at 1060: its up level is
    1060 + prev_range / 2. The 10:00 bar reaches it and closes at 1119 (up level 1118.5 for a 117 range)."""
    b = Bars().day("2026-03-10", 1050.0)
    b.bar("2026-03-10", "10:00", 1050, 1050, 1000, 1050).bar("2026-03-10", "11:00", 1050, 1000 + prev_range, 1050, 1050)
    b.day("2026-03-11", 1060.0, 0.25).hold("2026-03-11", "09:31", "09:59", 1060.0)
    return b.bar("2026-03-11", "10:00", 1060, 1119, 1060, 1119)


W = {"noise": False, "williams": True}


@needs_dotnet
def test_two_contracts_within_125_or_no_trade(sim, tmp_path):  # noqa: F811
    """A 117-point range gives R = 0.25 x 117 = 29.25 points: 2 x (29.25 x $2 + 2 x $0.95 + 4 ticks x $0.50) =
    $124.80, taken; 118 gives R 29.50, $125.80, skipped."""
    fits = williams_setup(117).hold("2026-03-11", "10:01", "15:59", 1119.0).frame()
    nt, py, _, _ = both(sim, fits, tmp_path, W)
    assert len(py) == len(nt) == 1 and (nt.astype(str).values == py.astype(str).values).all()
    p = py.iloc[0]
    assert p.r == "29.25" and p.planned == "124.80" and p.stop0 == "1089.75"
    assert math.isclose(2 * (29.25 * 2.0 + 2 * 0.95 + 4 * 0.5), 124.80)
    over = williams_setup(118).hold("2026-03-11", "10:01", "15:59", 1119.0).frame()
    nt, py, model, _ = both(sim, over, tmp_path, W)
    assert len(py) == len(nt) == 0
    assert any(x[1] == "skip" and x[2] == "williams" and math.isclose(x[4], 125.8) for x in model.log)


@needs_dotnet
def test_breakeven_half_and_trail(sim, tmp_path):  # noqa: F811
    """Fill 1119.50 (the 10:01 open 1119 + 2 ticks). 10:02 reaches +1R (1148.75): from 10:03 the stop is 1121.00 (fill
    + 1.50). 10:03 trades through +2R: the half fills at 1178.00; best 1178.25, so from 10:04 the runner's stop is
    1178.25 - 29.25 = 1149.00. 10:04 falls to 1148: the runner exits at 1149 - 2 ticks = 1148.50."""
    b = williams_setup(117)
    b.bar("2026-03-11", "10:01", 1119, 1125, 1118, 1124).bar("2026-03-11", "10:02", 1124, 1149, 1123, 1140)
    b.bar("2026-03-11", "10:03", 1140, 1178.25, 1139, 1170).bar("2026-03-11", "10:04", 1170, 1171, 1148, 1150)
    b.hold("2026-03-11", "10:05", "15:59", 1150.0)
    nt, py, _, _ = both(sim, b.frame(), tmp_path, W)
    assert (nt.astype(str).values == py.astype(str).values).all() and len(py) == 1
    p = py.iloc[0]
    assert (p.runner_fill, p.half_fill) == ("1119.50", "1119.50")
    assert (p.half_exit, p.half_why) == ("1178.00", "Profit target")
    assert (p.runner_exit, p.runner_why) == ("1148.50", "Stop loss")
    pnl = (1178.0 - 1119.5) * 2 - 1.9 + (1148.5 - 1119.5) * 2 - 1.9
    assert p.pnl == f"{pnl:.2f}"


@needs_dotnet
def test_breakeven_is_fee_aware_from_the_actual_fill(sim, tmp_path):  # noqa: F811
    """After +1R the price returns: both contracts exit at the breakeven stop 1121.00 less 2 ticks = 1120.50; each
    nets (1120.50 - 1119.50) x $2 - $1.90 = +$0.10, not a loss."""
    b = williams_setup(117)
    b.bar("2026-03-11", "10:01", 1119, 1125, 1118, 1124).bar("2026-03-11", "10:02", 1124, 1149, 1123, 1140)
    b.bar("2026-03-11", "10:03", 1140, 1141, 1110, 1112).hold("2026-03-11", "10:04", "15:59", 1112.0)
    nt, py, _, _ = both(sim, b.frame(), tmp_path, W)
    assert (nt.astype(str).values == py.astype(str).values).all()
    p = py.iloc[0]
    assert (p.runner_exit, p.half_exit) == ("1120.50", "1120.50") and p.pnl == "0.20"


@needs_dotnet
def test_runner_flat_at_1555(sim, tmp_path):  # noqa: F811
    """The half fills at +2R; the runner's trail is never reached; at 15:55 it is closed at the open less 2 ticks."""
    b = williams_setup(117)
    b.bar("2026-03-11", "10:01", 1119, 1125, 1118, 1124).bar("2026-03-11", "10:02", 1124, 1179, 1123, 1178)
    b.hold("2026-03-11", "10:03", "15:54", 1178.0).bar("2026-03-11", "15:55", 1180, 1181, 1179, 1180)
    b.hold("2026-03-11", "15:56", "15:59", 1180.0)
    nt, py, _, _ = both(sim, b.frame(), tmp_path, W)
    assert (nt.astype(str).values == py.astype(str).values).all()
    p = py.iloc[0]
    assert (p.half_exit, p.runner_exit, p.runner_why) == ("1178.00", "1179.50", "Flat 15:55")


@needs_dotnet
def test_a_gap_through_the_stop_is_logged_as_an_overrun(sim, tmp_path):  # noqa: F811
    """$125 is a planned budget, not a ceiling: a bar opening at 1080, under the 1089.75 stop, fills at 1079.50;
    each contract loses (1079.50 - 1119.50) x $2 + $1.90 = $81.90, $163.80 in all, flagged."""
    b = williams_setup(117)
    b.bar("2026-03-11", "10:01", 1119, 1120, 1118, 1119).bar("2026-03-11", "10:02", 1080, 1081, 1078, 1080)
    b.hold("2026-03-11", "10:03", "15:59", 1080.0)
    nt, py, _, out = both(sim, b.frame(), tmp_path, W)
    assert (nt.astype(str).values == py.astype(str).values).all()
    assert py.iloc[0].pnl == "-163.80" and ",overrun" in out


# ---- the sweep sequence (E1, a swept previous-day low) -------------------------------------------------------
def sweep_day(retrace: bool = True) -> tuple[Bars, dict]:
    """Day A: previous-day low 1000, high 1100, late session near 1008. Day B, five-minute bars:
    09:30 high 1012; 09:35 high 1015 (the swing, confirmed by 09:45); 09:40 high 1011; 09:45 high 1008;
    09:50 penetration (09:52 low 999.50), close 1003 (the reclaim); 09:55 close 1016 > 1015 (the BOS);
    10:00 low 1007 > 09:50's high 1004: the FVG, its edge 1007; the decision at the 10:04 close."""
    b = Bars().day("2026-03-10", 1050.0)
    b.bar("2026-03-10", "10:00", 1050, 1050, 1000, 1050).bar("2026-03-10", "11:00", 1050, 1100, 1050, 1050)
    b.hold("2026-03-10", "14:00", "15:59", 1008.0, 0.5)
    d = "2026-03-11"
    b.day(d, 1010.0, 0.5)
    b.bar(d, "09:30", 1010, 1012, 1009, 1010)
    b.bar(d, "09:37", 1010, 1015, 1009, 1011)
    b.bar(d, "09:42", 1010, 1011, 1008, 1009)
    b.hold(d, "09:45", "09:49", 1006.0, 0.5).bar(d, "09:45", 1006, 1008, 1005.5, 1006)
    b.hold(d, "09:50", "09:54", 1002.0, 0.5)
    b.bar(d, "09:50", 1002, 1004, 1001, 1001).bar(d, "09:52", 1001, 1002, 999.5, 1000.5)
    b.bar(d, "09:54", 1001, 1003.5, 1001, 1003)
    b.hold(d, "09:55", "09:59", 1010.0, 0.5).bar(d, "09:55", 1003, 1008, 1003, 1008)
    b.bar(d, "09:59", 1012, 1016.5, 1011, 1016)
    b.hold(d, "10:00", "10:04", 1015.0, 0.5).bar(d, "10:00", 1016, 1018, 1007, 1016)
    b.bar(d, "10:04", 1016, 1018, 1015, 1017)
    b.hold(d, "10:05", "15:59", 1017.0, 0.5)
    if retrace:
        b.bar(d, "10:07", 1016, 1016, 1006.5, 1008)
    return b, {"limit": 1007.0, "extreme": 999.5}


def five_minute_atr(frame: pd.DataFrame, until: pd.Timestamp) -> float:
    """Wilder's 14-period ATR of the completed five-minute bars up to `until` (independent of the model)."""
    f = frame[frame.index <= until]
    agg = f.resample("5min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min",
                                                                "close": "last"}).dropna()
    prev = agg.close.shift()
    tr = np.maximum(agg.high - agg.low, np.maximum((agg.high - prev).abs(), (agg.low - prev).abs()))
    tr.iloc[0] = agg.high.iloc[0] - agg.low.iloc[0]
    atr = tr.iloc[:14].mean()
    for x in tr.iloc[14:]:
        atr = (atr * 13 + x) / 14
    return float(atr)


E = {"noise": False, "williams": False, "e1": True}


@needs_dotnet
def test_sweep_sequence_enters_at_the_gap_edge(sim, tmp_path):  # noqa: F811
    b, exp = sweep_day()
    frame = b.frame()
    nt, py, model, _ = both(sim, frame, tmp_path, E)
    assert len(py) == len(nt) == 1 and (nt.astype(str).values == py.astype(str).values).all()
    dec = [x for x in model.log if x[1] == "E decision"]
    assert len(dec) == 1 and dec[0][2] == "PDL"
    assert frame.index[dec[0][0]] == pd.Timestamp("2026-03-11 10:04", tz=NY)  # the FVG's completion, not earlier
    assert (dec[0][3], dec[0][4]) == (exp["limit"], exp["extreme"])
    atr = five_minute_atr(frame, pd.Timestamp("2026-03-11 10:04", tz=NY))
    assert math.isclose(dec[0][5], atr, rel_tol=1e-12)
    stop = math.floor((999.5 - 0.1 * atr) / 0.25 + 1e-7) * 0.25
    p = py.iloc[0]
    assert p.sleeve == "E:PDL" and p.kind == "limit" and p.stop0 == f"{stop:.2f}"
    assert p.r == f"{1007 - stop:.2f}"
    assert p.runner_fill == "1007.00" and frame.index[p.entry_bar] == pd.Timestamp("2026-03-11 10:07", tz=NY)


@needs_dotnet
def test_no_sweep_entry_without_the_retrace(sim, tmp_path):  # noqa: F811
    """The limit at 1007 is never reached: it is cancelled after 30 minutes and no campaign is counted."""
    b, _ = sweep_day(retrace=False)
    nt, py, model, out = both(sim, b.frame(), tmp_path, E)
    assert len(py) == len(nt) == 0
    assert any(x[1] == "cancel" and x[2] == "expired" for x in model.log)
    assert "entry ended unfilled (Cancelled)" in out


# ---- execution state (the stand-in) ---------------------------------------------------------------------------
def stand_in(sim, frame, tmp_path, **props):  # noqa: F811
    csv = tmp_path / "bars.csv"
    K.write_bars(frame, csv)
    base = {"UseNoise": False, "UseWilliams": False, "UseE1": True, "UseE2": False, "SimSlippageTicks": 2,
            "SimCommissionPerSide": 0.95, "SimExitExecutions": True, "EvalTarget": 0, "EvalTrail": 0}
    base.update(props)
    r = subprocess.run([DOTNET, str(sim), str(csv), "1", "Strategy=D", *[f"{k}={v}" for k, v in base.items()]],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout


@needs_dotnet
def test_pending_guard_holds_until_the_cancellation_is_confirmed_and_a_late_fill_is_managed(sim, tmp_path):  # noqa: F811
    """The limit expires at 10:34 (placed at 10:04); the cancellation takes 5 bars to confirm. The retrace comes at
    10:36, while it is pending: both contracts fill and the position is managed and logged like any other."""
    b, _ = sweep_day(retrace=False)
    b.bar("2026-03-11", "10:36", 1016, 1016, 1006.5, 1008)
    out = stand_in(sim, b.frame(), tmp_path, SimCancelDelayBars=5)
    orders = [x for x in out.splitlines() if x.startswith("O,")]
    cancels = [k for k, x in enumerate(orders) if ",Cancel," in x]
    assert len(cancels) == 2  # both contracts' orders
    assert not any(",EnterLimit," in x or ",Enter," in x for x in orders[cancels[-1]:])  # nothing new while pending
    pos = [x for x in out.splitlines() if x.startswith("P,D position,")]
    assert len(pos) == 1 and ",1007.00," in pos[0]


@needs_dotnet
def test_one_contract_of_two_filled_is_one_campaign(sim, tmp_path):  # noqa: F811
    """The half's limit never fills: the strategy cancels it and manages the runner alone, logged once."""
    b, _ = sweep_day()
    out = stand_in(sim, b.frame(), tmp_path, SimLimitDelayName="Long half", SimLimitDelayBars=-1)
    assert "one contract filled, cancelling the other" in out
    pos = [x for x in out.splitlines() if x.startswith("P,D position,")]
    assert len(pos) == 1
    f = pos[0].split(",")
    assert f[8] == "1007.00" and f[11] == "-"  # the runner filled, the half did not


@needs_dotnet
def test_account_highest_equity_survives_a_restart(sim, tmp_path):  # noqa: F811
    """With the evaluation's limits on, the highest equity is written to the account file in real time and read back
    by a restarted strategy, which keeps the higher of its own and the file's."""
    b = williams_setup(117)
    b.bar("2026-03-11", "10:01", 1119, 1125, 1118, 1124).bar("2026-03-11", "10:02", 1124, 1179, 1123, 1178)
    b.hold("2026-03-11", "10:03", "15:59", 1178.0)
    frame = b.frame()
    props = {"UseE1": False, "UseWilliams": True, "EvalTarget": 3000, "EvalTrail": 2000, "SimRealtimeFrom": 1,
             "SimUserDataDir": str(tmp_path), "SimAccountName": "SimD"}
    stand_in(sim, frame, tmp_path, **props)
    saved = (tmp_path / "MnqCandidateD-SimD.txt").read_text().split(",")
    assert float(saved[0]) > 50000
    out = stand_in(sim, frame.iloc[:5], tmp_path, **props)
    assert f"D account: highest equity {float(saved[0]):.2f}" in out


# ---- rescaled NQ: levels carried across a month boundary ------------------------------------------------------
def _scaled(frame: pd.DataFrame, month: str, k: float) -> pd.DataFrame:
    f = frame.copy()
    f["scale"] = 1.0
    m = f.index.strftime("%Y-%m") == month
    f.loc[m, ["open", "high", "low", "close"]] *= k
    f.loc[m, "scale"] = k
    return f


def _moved(frame: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """The same bars with day a moved to 2026-03-31 and day b to 2026-04-01 (a month boundary between them)."""
    idx = frame.index.strftime("%Y-%m-%d")
    out = frame.copy()
    new = [t.replace(month=3, day=31) if d == a else t.replace(month=4, day=1)
           for t, d in zip(frame.index, idx, strict=True)]
    out.index = pd.DatetimeIndex(new)
    return out


@pytest.mark.parametrize("which", ["williams", "sweep"])
def test_levels_cross_a_rescaled_month_boundary(which):
    """The previous session's range (Williams) and the previous-day low, swings and ATR (the sweep) carried into a month
    whose prices are scaled by 2 (and its scale column 2) give the same positions at prices 2x the unscaled ones."""
    if which == "williams":
        b, kw = williams_setup(117), {"noise": False, "williams": True}
        # 1100 is under the up level (1118.5, or 2237 scaled) but over an unconverted one (2120 + 58.5 = 2178.5)
        b.bar("2026-03-11", "09:45", 1060, 1100, 1060, 1062)
        b.bar("2026-03-11", "10:01", 1119, 1125, 1118, 1124).hold("2026-03-11", "10:02", "15:59", 1124.0)
    else:
        b, kw = sweep_day()[0], {"noise": False, "williams": False, "e1": True}
    base = _moved(b.frame(), "2026-03-10", "2026-03-11")
    cfg = DConfig(budget=10_000.0, **kw)
    one = run(base.assign(scale=1.0), cfg).campaigns
    two = run(_scaled(base, "2026-04", 2.0), cfg).campaigns
    assert len(one) == len(two) == 1
    a, z = one[0], two[0]
    assert (a.sleeve, a.d, a.signal_bar, [x.fill_bar for x in a.lots]) == \
           (z.sleeve, z.d, z.signal_bar, [x.fill_bar for x in z.lots])
    tol = 1e-9 if which == "williams" else 0.25 + 1e-9  # an ATR-based stop rounds to the tick after scaling
    assert abs(z.expected - 2 * a.expected) <= 1e-9 and abs(z.stop0 - 2 * a.stop0) <= tol
    assert abs(z.r - 2 * a.r) <= tol
