"""Candidate F (docs/CANDIDATE_F.md): E's sweep chain with the initial stop at the selected FVG's far boundary -/+ 2
ticks. Only the new behaviour is tested here; the rest is tests/test_candidate_d.py (whose MNQ parity runs D + F1,
D + F2 and F alone too, through research/d_parity.py's configurations).

Every case runs on the NinjaTrader stand-in (MnqCandidateD.cs, SweepStop = FvgFarEdge) and on the Python model
(DConfig.e_stop = "fvg"), position by position, against values computed by hand in the docstrings: the FVG selected,
the rounded limit and stop in both directions (an off-grid boundary at a half tick included), R and the $125 boundary,
the breakeven trigger and the case where the breakeven stop cannot legally be placed (R < 1.50), the half at +2R and
the runner's exit, net P/L, gaps through the stop, one contract of two filled and a fill during a pending
cancellation.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest
from test_candidate_d import NY, Bars, P, both, needs_dotnet, stand_in, sweep_day  # noqa: F401
from test_ninjatrader import sim  # noqa: F401

from mnqbot.candidate_d import DConfig, run, sweep_prices

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

D = "2026-03-11"
F = {"noise": False, "williams": False, "e1": True, "e_stop": "fvg"}
E = {"noise": False, "williams": False, "e1": True}


def f_day(far: float | None = None, limit_low: float | None = None) -> Bars:
    """sweep_day's sequence (previous-day low 1000 swept at 09:52, reclaim at the 09:50 close, BOS at the 09:55 close
    over the 1015 swing, the FVG completed by the 10:00 bar, the decision at the 10:04 close). Its gap runs from the
    09:50 bar's high (1004, the far boundary) to the 10:00 bar's low (1007, the entry): F's stop is 1003.50, R 3.50.
    After the decision price stays at 1010 (under the +2R run-away level 1014), retraces to fill at 10:07, then holds
    1017."""
    b, _ = sweep_day(retrace=False)
    if far is not None:
        b.bar(D, "09:50", 1002, far, 1001, 1001)
    if limit_low is not None:
        b.bar(D, "10:00", 1016, 1018, limit_low, 1016)
    b.hold(D, "10:05", "10:06", 1010.0, 0.5)
    return b.bar(D, "10:07", 1010, 1010, 1006.5, 1008)


def mirror(frame: pd.DataFrame) -> pd.DataFrame:
    """The same bars reflected about 1000 (p -> 2000 - p): a swept previous-day high and a short."""
    return pd.DataFrame({"open": 2000 - frame.open, "high": 2000 - frame.low, "low": 2000 - frame.high,
                         "close": 2000 - frame.close}, index=frame.index)


def agree(sim, frame, tmp_path, kw=F, n=1, fmt="%.2f"):  # noqa: F811
    """Both implementations; fmt "%.4f" keeps off-grid prices exact in the stand-in's file."""
    if fmt == "%.2f":
        nt, py, model, out = both(sim, frame, tmp_path, kw)
    else:
        csv = tmp_path / "bars.csv"
        f = frame.copy()
        f.insert(0, "t", f.index.tz_convert(NY).strftime("%Y-%m-%d %H:%M"))
        f.to_csv(csv, header=False, index=False, float_format=fmt)
        nt, out = P.nt_positions(sim, csv, kw, 125.0, 2)
        py, model = P.py_positions(frame, kw, 125.0, 2)
    assert len(py) == len(nt) == n
    assert (nt.astype(str).values == py.astype(str).values).all()
    return py, model, out


@needs_dotnet
def test_f_long_stop_at_the_far_edge_half_and_runner(sim, tmp_path):  # noqa: F811
    """Limit 1007, stop 1004 - 0.50 = 1003.50, R 3.50; planned 2 x (7.00 + 1.90 + 1.00) = $19.80, price risk $14.00.
    Fill at 10:07 (low 1006.50). 10:08 (high 1017.50): the half fills at 1007 + 7 = 1014.00; at the close +1R is
    reached (1010.50), the breakeven stop is 1008.50 and the trail toward(1017.50 - 3.50) = 1014.00, so the stop is
    1014.00 (under the close 1017). The runner is closed at 15:55: 1017 - 2 ticks = 1016.50.
    Net (1014 - 1007) x 2 - 1.90 + (1016.50 - 1007) x 2 - 1.90 = $29.20."""
    py, model, _ = agree(sim, f_day().frame(), tmp_path)
    p = py.iloc[0]
    assert (p.sleeve, p.kind, p.stop0, p.r, p.planned) == ("F:PDL", "limit", "1003.50", "3.50", "19.80")
    assert (p.runner_fill, p.half_fill, p.half_exit, p.half_why) == ("1007.00", "1007.00", "1014.00", "Profit target")
    assert (p.runner_exit, p.runner_why, p.pnl) == ("1016.50", "Flat 15:55", "29.20")
    dec = [x for x in model.log if x[1] == "E decision"]
    assert len(dec) == 1 and (dec[0][3], dec[0][6]) == (1007.0, 1004.0)  # the proximal and far edges
    assert any(x[1] == "stop" and x[2] == 1014.0 for x in model.log)


@needs_dotnet
def test_f_short_is_the_mirror_image(sim, tmp_path):  # noqa: F811
    """Reflected: a swept previous-day high at 1000, a bearish gap from the 10:00 bar's high 993 (the entry) to the
    09:50 bar's low 996 (the far boundary): stop 996.50, R 3.50, half at 986.00, runner flat at 983 + 0.50 = 983.50,
    net $29.20."""
    py, _, _ = agree(sim, mirror(f_day().frame()), tmp_path)
    p = py.iloc[0]
    assert (p.sleeve, p.d, p.runner_fill, p.stop0, p.r) == ("F:PDH", -1, "993.00", "996.50", "3.50")
    assert (p.half_exit, p.runner_exit, p.pnl) == ("986.00", "983.50", "29.20")


@needs_dotnet
@pytest.mark.parametrize("short", [False, True])
def test_off_grid_boundary_rounds_away_from_the_entry(sim, tmp_path, short):  # noqa: F811
    """Far boundary 1004.125, entry boundary 1007.125 (off the grid, as a level carried across a rescaled month can
    be): the limit rounds down to 1007.00 and the stop 1004.125 - 0.50 = 1003.625, an exact half tick, rounds away to
    1003.50. Short (reflected): limit 992.875 rounds up to 993.00, stop 995.875 + 0.50 = 996.375 rounds up to 996.50."""
    frame = f_day(far=1004.125, limit_low=1007.125).frame()
    frame = mirror(frame) if short else frame
    py, _, _ = agree(sim, frame, tmp_path, fmt="%.4f")
    p = py.iloc[0]
    assert (p.runner_fill, p.stop0, p.r) == (("993.00", "996.50", "3.50") if short else ("1007.00", "1003.50", "3.50"))


def test_sweep_prices_rounding_and_scale():
    """The shared price function, E's convention: the stop away from the entry, the limit down (long) / up (short);
    a boundary in raw units converted by the bar's scale before the 2 ticks."""
    cfg = DConfig(e_stop="fvg")
    long_ = {"d": 1, "limit_raw": 1007.0, "far_raw": 1004.0, "extreme_raw": 999.5, "atr_raw": 10.0}
    assert sweep_prices(long_, 1.0, cfg) == (1007.0, 1003.5, 3.5, 19.8)
    assert sweep_prices({**long_, "far_raw": 1004.125}, 1.0, cfg)[1] == 1003.5
    assert sweep_prices({**long_, "far_raw": 1004.2}, 1.0, cfg)[1] == 1003.5
    assert sweep_prices({**long_, "far_raw": 1004.3}, 1.0, cfg)[1] == 1003.75
    half = {**long_, "limit_raw": 503.5, "far_raw": 502.0625}  # x 2: 1007.00 and 1004.125
    assert sweep_prices(half, 2.0, cfg)[:3] == (1007.0, 1003.5, 3.5)
    short = {"d": -1, "limit_raw": 993.0, "far_raw": 995.875, "extreme_raw": 1000.5, "atr_raw": 10.0}
    assert sweep_prices(short, 1.0, cfg)[:3] == (993.0, 996.5, 3.5)
    # E's stop, unchanged by the setting's existence
    assert sweep_prices(long_, 1.0, cfg, "extreme")[1] == math.floor((999.5 - 1.0) / 0.25 + 1e-7) * 0.25
    assert sweep_prices(long_, 1.0, DConfig())[1] == 998.5


@needs_dotnet
def test_f_budget_boundary(sim, tmp_path):  # noqa: F811
    """The sweep runs down to 970 in the 09:50 bar (high 977.75); the 10:00 bar's low 1007 leaves a gap from 977.75:
    F's stop 977.25, R 29.75, planned 2 x (59.50 + 1.90 + 1.00) = $124.80, taken (E's stop under the 970 extreme does
    not fit). With the 09:50 high at 977.50: R 30.00, $125.80, skipped. Taken: flat at 15:55, 2 x ((1016.50 - 1007)
    x 2 - 1.90) = $34.20."""
    def frame(high):
        b = f_day()
        b.hold(D, "09:50", "09:54", 975.0, 0.5).bar(D, "09:50", 976, high, 970, 975)
        return b.frame()
    py, model, _ = agree(sim, frame(977.75), tmp_path)
    p = py.iloc[0]
    assert (p.stop0, p.r, p.planned, p.pnl) == ("977.25", "29.75", "124.80", "34.20")
    py_e, model_e = P.py_positions(frame(977.75), E, 125.0)
    assert len(py_e) == 0 and any(x[1] == "skip" and x[2] == "PDL" and x[4] > 125 for x in model_e.log)
    _, model, _ = agree(sim, frame(977.5), tmp_path, n=0)
    assert any(x[1] == "skip" and x[2] == "PDL" and math.isclose(x[3], 30.0) and math.isclose(x[4], 125.8)
               for x in model.log)


def small_r(after: list[tuple]) -> Bars:
    """A one-tick gap: far boundary 1006.75 (the 09:50 high), entry 1007: stop 1006.25, R 0.75, the +1R trigger at
    1007.75, the half at 1008.50, the breakeven stop at 1008.50, beyond the trigger. Price waits at 1007.75 (under the
    run-away level 1008.50), fills at 10:07 (low 1006.75, a tick through), then the bars given."""
    b = f_day(far=1006.75)
    b.hold(D, "10:05", "10:06", 1007.75, 0.25).bar(D, "10:07", 1007.75, 1007.75, 1006.75, 1007.25)
    for hhmm, o, h, l, c in after:
        b.bar(D, hhmm, o, h, l, c)
    return b


@needs_dotnet
def test_breakeven_beyond_the_trigger_cannot_be_placed_so_the_position_is_closed(sim, tmp_path):  # noqa: F811
    """10:08 reaches +1R (high 1007.75) but closes at 1007.50, under the breakeven stop 1008.50: a sell stop there
    cannot be placed, so the position is closed at the 10:09 open 1007.50 less 2 ticks, 1007.00 ("Stop passed"), as
    E's protocol says. Net 2 x (0 - 1.90) = -$3.80. No stop is simulated at 1008.50."""
    b = small_r([("10:08", 1007.25, 1007.75, 1007.0, 1007.5)]).hold(D, "10:09", "15:59", 1007.5, 0.25)
    py, model, _ = agree(sim, b.frame(), tmp_path)
    p = py.iloc[0]
    assert (p.stop0, p.r, p.planned) == ("1006.25", "0.75", "8.80")
    assert (p.runner_exit, p.runner_why, p.half_exit, p.half_why, p.pnl) == \
           ("1007.00", "Stop passed", "1007.00", "Stop passed", "-3.80")
    assert not any(x[1] == "stop" for x in model.log)


@needs_dotnet
def test_breakeven_placed_when_legal_half_and_runner(sim, tmp_path):  # noqa: F811
    """10:08 trades to 1009 (the half fills at 1008.50) and closes at 1008.75: the breakeven stop 1008.50 (the trail,
    toward(1009 - 0.75) = 1008.25, is lower) is under the close and is placed. 10:09 falls to 1008: the runner exits at
    1008.50 - 2 ticks = 1008.00. Net (1008.50 - 1007) x 2 - 1.90 + (1008 - 1007) x 2 - 1.90 = $1.20."""
    b = small_r([("10:08", 1007.25, 1009.0, 1007.0, 1008.75), ("10:09", 1008.75, 1008.75, 1008.0, 1008.0)])
    b.hold(D, "10:10", "15:59", 1008.0, 0.25)
    py, _, _ = agree(sim, b.frame(), tmp_path)
    p = py.iloc[0]
    assert (p.half_exit, p.half_why, p.runner_exit, p.runner_why, p.pnl) == \
           ("1008.50", "Profit target", "1008.00", "Stop loss", "1.20")


@needs_dotnet
def test_gap_through_both_the_limit_and_the_stop(sim, tmp_path):  # noqa: F811
    """The 10:07 bar opens at 1000, under the limit 1007 and the stop 1003.50: the limit fills at the open, the stop is
    already passed, and both contracts are closed at the open less 2 ticks, 999.50 (the market close a rejected stop
    gets). Net 2 x ((999.50 - 1000) x 2 - 1.90) = -$5.80."""
    b = f_day().bar(D, "10:07", 1000, 1000.5, 999.75, 1000)
    py, _, _ = agree(sim, b.frame(), tmp_path)
    p = py.iloc[0]
    assert (p.runner_fill, p.runner_exit, p.half_exit, p.pnl) == ("1000.00", "999.50", "999.50", "-5.80")


@needs_dotnet
def test_gap_through_the_stop_after_the_fill_is_an_overrun(sim, tmp_path):  # noqa: F811
    """Filled at 1007 at 10:07; 10:08 opens at 1000, under the 1003.50 stop: both exit at 999.50. Net
    2 x ((999.50 - 1007) x 2 - 1.90) = -$33.80, beyond the $19.80 plan: an overrun."""
    b = f_day().bar(D, "10:08", 1000, 1001, 999, 1000).hold(D, "10:09", "15:59", 1000.0, 0.5)
    py, _, out = agree(sim, b.frame(), tmp_path)
    assert (py.iloc[0].runner_exit, py.iloc[0].pnl) == ("999.50", "-33.80") and ",overrun" in out


@needs_dotnet
def test_run_away_uses_f_r(sim, tmp_path):  # noqa: F811
    """sweep_day's own path holds 1017 after the decision: over 1007 + 2 x 3.50 = 1014, F's run-away level, so the
    limit is cancelled at 10:05 and the 10:07 retrace finds no order (E's wider R keeps it, and fills)."""
    b, _ = sweep_day()
    _, model, _ = agree(sim, b.frame(), tmp_path, n=0)
    assert any(x[1] == "cancel" and x[2] == "ran away" for x in model.log)
    py_e, _ = P.py_positions(b.frame(), E, 125.0)
    assert len(py_e) == 1


def test_e_and_f_see_the_same_decisions():
    """The chain up to the decision is the same: identical decision logs (bar, pool, edges, extreme, ATR)."""
    frame = f_day().frame()
    cfg = {"budget": 125.0}
    e = [x for x in run(frame, DConfig(**E, **cfg)).log if x[1] == "E decision"]
    f = [x for x in run(frame, DConfig(**F, **cfg)).log if x[1] == "E decision"]
    assert e == f and len(e) == 1


@needs_dotnet
def test_one_contract_of_two_filled_under_f(sim, tmp_path):  # noqa: F811
    """The half's limit never fills: it is cancelled and the runner is managed alone with F's stop and R: breakeven
    after 10:08 (1008.50), no half so no trail, flat at 15:55 at 1016.50: (1016.50 - 1007) x 2 - 1.90 = $17.10."""
    out = stand_in(sim, f_day().frame(), tmp_path, SweepStop="FvgFarEdge", SimLimitDelayName="Long half",
                   SimLimitDelayBars=-1)
    assert "one contract filled, cancelling the other" in out
    pos = [x.split(",") for x in out.splitlines() if x.startswith("P,D position,")]
    assert len(pos) == 1
    f = pos[0]
    assert (f[2], f[8], f[11], f[14], f[15], f[17]) == ("F:PDL", "1007.00", "-", "1003.50", "3.50", "17.10")


@needs_dotnet
def test_fill_during_a_pending_cancellation_is_managed_under_f(sim, tmp_path):  # noqa: F811
    """F's run-away cancellation is sent at 10:05 and takes 5 bars to confirm; the 10:07 retrace fills both contracts
    meanwhile: a real position, managed and logged, and nothing new is placed while the cancellation is pending."""
    b, _ = sweep_day()
    out = stand_in(sim, b.frame(), tmp_path, SweepStop="FvgFarEdge", SimCancelDelayBars=5)
    assert "limit entry: ran away" in out
    orders = [x for x in out.splitlines() if x.startswith("O,")]
    cancels = [k for k, x in enumerate(orders) if ",Cancel," in x]
    assert len(cancels) == 2
    assert not any(",EnterLimit," in x or ",Enter," in x for x in orders[cancels[-1]:])
    pos = [x.split(",") for x in out.splitlines() if x.startswith("P,D position,")]
    assert len(pos) == 1 and pos[0][2] == "F:PDL" and pos[0][8] == "1007.00" and pos[0][14] == "1003.50"


def test_setup_ledger_and_isolated_replay_on_the_hand_computed_day():
    """research/f_setups.py on f_day: one decision, affordable under both stops, taken and filled by the book; the
    isolated replay with F's stop gives the book's own position ($29.20), with E's stop E's book position; matched."""
    import f_setups as S
    frame = f_day().frame().assign(scale=1.0)
    cfg = DConfig(**F)
    m = run(frame, cfg)
    led = S.setup_ledger(frame, "F1 only", m.sweep_seen, m.log, m.campaigns, cfg)
    assert len(led) == 1
    row = led.iloc[0]
    assert (row["class"], row["book outcome"], row["F stop"], row["F R"], row["F planned $"]) == \
           ("affordable under both", "taken: filled", 1003.5, 3.5, 19.8)
    assert bool(row["E executable"]) and bool(row["F executable"]) and row["F price risk $"] == 14.0
    arrays = tuple(frame[x].to_numpy(float) for x in ("open", "high", "low", "close", "scale"))
    i, scale, dec, _ = m.sweep_seen[0]
    iso_f = S.isolated(frame, arrays, i, scale, dec, "fvg", 2)
    iso_e = S.isolated(frame, arrays, i, scale, dec, "extreme", 2)
    e_book = run(frame, DConfig(**E)).campaigns
    assert iso_f["filled"] and math.isclose(iso_f["pnl $"], 29.2) and iso_f["+1R"] and iso_f["+2R (half)"]
    assert not iso_f["initial stop exit"] and math.isclose(iso_f["declared cost % of risk"], 100 * 5.8 / 14)
    assert iso_e["filled"] and math.isclose(iso_e["pnl $"], e_book[0].pnl)
    iso = pd.DataFrame([{"bar_pool": f"{i}:PDL", "mode": "extreme", **iso_e}, {"bar_pool": f"{i}:PDL", "mode": "fvg",
                                                                                **iso_f}])
    t = S.matched_table(iso, led.assign(bar_pool=f"{i}:PDL"))
    assert t[(t.set == "all matched") & (t.stop == "F stop")].positions.iloc[0] == 1
