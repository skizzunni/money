"""Noise-area momentum: hand-built cases for mnqbot/noise.py, and parity with pine/mnq_noise_momentum.pine.

Hand-built history: 14 quiet sessions whose every half-hour check sits exactly 0.1% above the 09:30 open,
so on the next session the noise area is open (= previous close) * (1 +/- 0.001) at every check.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from conftest import synth_bars

from mnqbot.data import NY, annotate, resample
from mnqbot.noise import NoiseConfig, run

ROOT = Path(__file__).resolve().parents[1]
NOISE_PINE = ROOT / "pine" / "mnq_noise_momentum.pine"
P0 = 20_000.0
BARS_PER_DAY = 78  # 09:30 .. 15:55 on 5-minute bars
CHECK_10_00, CHECK_10_30, CLOSE_16_00 = 5, 11, 77  # bar numbers within a session


def session(date: str, open_: float, closes: list[float], minutes: int = 5) -> pd.DataFrame:
    idx = pd.date_range(f"{date} 09:30", periods=len(closes), freq=f"{minutes}min", tz=NY)
    opens = [open_] + closes[:-1]
    rows = [(o, max(o, c), min(o, c), c) for o, c in zip(opens, closes, strict=True)]
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 100.0
    return df


def quiet_history(n: int = 14, start: str = "2026-03-02") -> tuple[list[pd.DataFrame], float, pd.Timestamp]:
    frames, price = [], P0
    days = pd.bdate_range(start, periods=n + 1)
    for d in days[:n]:
        frames.append(session(str(d.date()), price, [price * 1.001] * BARS_PER_DAY))
        price = price * 1.001
    return frames, price, days[n]


def scenario(path, n_hist: int = 14, extra: list[pd.DataFrame] | None = None) -> tuple[pd.DataFrame, float]:
    """History, then one test session whose closes are path(prev_close) (78 values unless it's a half day)."""
    frames, p, day = quiet_history(n_hist)
    frames.append(session(str(day.date()), p, path(p)))
    df = pd.concat(frames + (extra or []))
    return annotate(df), p


def bar(day_number: int, j: int) -> int:
    return day_number * BARS_PER_DAY + j


def above_all_day(p):
    return [p] * CHECK_10_00 + [p * 1.002] * (BARS_PER_DAY - CHECK_10_00)


def above_then_inside(p):
    return [p] * CHECK_10_00 + [p * 1.002] * (CHECK_10_30 - CHECK_10_00) + [p] * (BARS_PER_DAY - CHECK_10_30)


def above_then_below(p):
    return [p] * CHECK_10_00 + [p * 1.002] * (CHECK_10_30 - CHECK_10_00) + [p * 0.998] * (BARS_PER_DAY - CHECK_10_30)


CHECK = NoiseConfig(exit_mode="check")  # the paper's half-hour exit; the default is the resting stop
STOP0 = NoiseConfig(stop_buffer=0.0)  # the resting stop exactly on the line (the default sits 0.24 sigma past it)
BUF = 0.24 * 0.001  # the default buffer as a share of price in the quiet history, where sigma = 0.1%


def with_low(bars: pd.DataFrame, i: int, low: float, open_: float | None = None) -> pd.DataFrame:
    """A copy of bars with bar i's low (and optionally open) changed, so a stop can be touched."""
    out = bars.copy()
    out.iloc[i, out.columns.get_loc("low")] = low
    if open_ is not None:
        out.iloc[i, out.columns.get_loc("open")] = open_
        out.iloc[i, out.columns.get_loc("high")] = max(out.iloc[i]["high"], open_)
    return out


def trades_of(res):
    return [(t.entry_bar, t.exit_bar, t.direction, round(t.entry, 6), round(t.exit, 6), round(t.pnl, 6), t.reason)
            for t in res.trades]


def test_quiet_history_gives_a_0_1_percent_noise_area():
    bars, p = scenario(above_all_day)
    res = run(bars)
    first = res.bands[0]
    assert first[0] == bar(14, CHECK_10_00)
    assert first[1] == pytest.approx(p * 1.001) and first[2] == pytest.approx(p * 0.999)
    assert all(b[1] == pytest.approx(p * 1.001) for b in res.bands)


def test_buy_above_the_noise_area_and_flat_at_the_close():
    bars, p = scenario(above_all_day)
    res = run(bars)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CLOSE_16_00), "FLAT")]
    hi = p * 1.002
    assert trades_of(res) == [(bar(14, CHECK_10_00 + 1), bar(14, CLOSE_16_00), 1, round(hi + 0.25, 6),
                               round(hi - 0.25, 6), round(-0.5 * 2 - 1.24, 6), "16:00 close")]


def test_exit_when_back_inside():
    bars, p = scenario(above_then_inside)
    res = run(bars, CHECK)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "EXIT")]
    t = res.trades[0]
    assert (t.entry_bar, t.exit_bar, t.reason) == (bar(14, CHECK_10_00 + 1), bar(14, CHECK_10_30 + 1), "Back inside")
    assert t.exit == pytest.approx(p - 0.25)
    assert t.pnl == pytest.approx((p - 0.25 - (p * 1.002 + 0.25)) * 2 - 1.24)


def test_reverse_when_through_the_other_side():
    bars, p = scenario(above_then_below)
    res = run(bars, CHECK)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "REVERSE"),
                          (bar(14, CLOSE_16_00), "FLAT")]
    long, short = res.trades
    lo = p * 0.998
    assert (long.direction, long.exit_bar, long.reason) == (1, bar(14, CHECK_10_30 + 1), "reversed")
    assert long.exit == pytest.approx(lo - 0.25)
    assert (short.direction, short.entry_bar, short.exit_bar) == (-1, bar(14, CHECK_10_30 + 1), bar(14, CLOSE_16_00))
    assert short.entry == pytest.approx(lo - 0.25) and short.exit == pytest.approx(lo + 0.25)
    assert short.pnl == pytest.approx(-0.5 * 2 - 1.24)


def test_stop_exits_at_the_line_when_a_bar_dips_inside():
    bars, p = scenario(above_then_inside)
    res = run(bars, STOP0)
    ub = p * 1.001
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "EXIT")]
    t = res.trades[0]
    # the 10:30 bar opens above the line and closes inside it: the stop fills at the line on that bar
    assert (t.entry_bar, t.exit_bar, t.reason) == (bar(14, CHECK_10_00 + 1), bar(14, CHECK_10_30), "Back inside")
    assert t.exit == pytest.approx(ub - 0.25)
    assert t.pnl == pytest.approx((ub - 0.25 - (p * 1.002 + 0.25)) * 2 - 1.24)


def test_stop_fills_on_a_touch_between_checks_then_reenters_at_the_next_check():
    bars, p = scenario(above_all_day)
    ub = p * 1.001
    bars = with_low(bars, bar(14, 8), p * 1.0005)  # 10:10 bar wicks below the line, closes back above it
    res = run(bars, STOP0)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, 8), "EXIT"), (bar(14, CHECK_10_30), "BUY"),
                          (bar(14, CLOSE_16_00), "FLAT")]
    first, second = res.trades
    assert (first.exit_bar, first.reason, first.exit) == (bar(14, 8), "Back inside", pytest.approx(ub - 0.25))
    assert (second.entry_bar, second.reason) == (bar(14, CHECK_10_30 + 1), "16:00 close")


def test_stop_can_fill_on_the_entry_bar_at_the_line_or_the_open():
    bars, p = scenario(above_all_day)
    ub = p * 1.001
    touched = run(with_low(bars, bar(14, CHECK_10_00 + 1), p * 1.0005), STOP0)  # entry bar dips to the line
    t = touched.trades[0]
    entry_bar = bar(14, CHECK_10_00 + 1)
    assert (t.entry_bar, t.exit_bar, t.exit) == (entry_bar, entry_bar, pytest.approx(ub - 0.25))
    gapped = run(with_low(bars, bar(14, CHECK_10_00 + 1), p * 1.0005, open_=p * 1.0005), STOP0)  # opens inside
    t = gapped.trades[0]
    assert t.entry == pytest.approx(p * 1.0005 + 0.25) and t.exit == pytest.approx(p * 1.0005 - 0.25)
    assert t.pnl == pytest.approx(-0.5 * 2 - 1.24)
    assert run(with_low(bars, bar(14, CHECK_10_00 + 1), p * 1.0005), CHECK).trades[0].reason == "16:00 close"


def widening_history_then_breakout() -> tuple[pd.DataFrame, float]:
    """14 sessions whose moves are 0.1% at 10:00 and 0.3% from 10:30 on, then a 10:00 breakout to +0.2%."""
    frames, price = [], P0
    days = pd.bdate_range("2026-03-02", periods=15)
    for d in days[:14]:
        closes = [price * 1.001] * CHECK_10_30 + [price * 1.003] * (BARS_PER_DAY - CHECK_10_30)
        frames.append(session(str(d.date()), price, closes))
        price = price * 1.003
    frames.append(session(str(days[14].date()), price, above_all_day(price)))
    return annotate(pd.concat(frames)), price


def test_stop_moves_with_the_line_and_fills_at_the_open_when_the_line_passes_the_price():
    bars, p = widening_history_then_breakout()
    res = run(bars, STOP0)
    assert res.bands[0][1] == pytest.approx(p * 1.001) and res.bands[1][1] == pytest.approx(p * 1.003)
    # long from the 10:00 check; at 10:30 the upper line moves to +0.3%, above the price: out at the next open
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30 + 1), "EXIT")]
    t = res.trades[0]
    assert (t.exit_bar, t.reason) == (bar(14, CHECK_10_30 + 1), "Back inside")
    assert t.exit == pytest.approx(p * 1.002 - 0.25)
    check = run(bars, CHECK)  # the half-hour rule reaches the same exit a different way
    assert check.trades[0].exit_bar == bar(14, CHECK_10_30 + 1)
    assert check.trades[0].exit == pytest.approx(p * 1.002 - 0.25)


def test_default_stop_sits_past_the_line():
    bars, p = scenario(above_all_day)
    ub = p * 1.001
    stop = ub * (1 - BUF)
    held = run(with_low(bars, bar(14, 8), stop + 0.05))  # dips below the line but not to the stop
    assert held.trades[0].reason == "16:00 close" and held.events == [(bar(14, CHECK_10_00), "BUY"),
                                                                       (bar(14, CLOSE_16_00), "FLAT")]
    assert run(with_low(bars, bar(14, 8), stop + 0.05), STOP0).trades[0].reason == "Back inside"  # on the line: out
    t = run(with_low(bars, bar(14, 8), stop - 0.05)).trades[0]  # dips through the stop
    assert (t.exit_bar, t.reason) == (bar(14, 8), "Back inside") and t.exit == pytest.approx(stop - 0.25)


def test_exit_mode_must_be_known():
    with pytest.raises(ValueError):
        run(scenario(above_all_day)[0], NoiseConfig(exit_mode="trailing"))


def test_no_trades_on_a_listed_date():
    bars, p = scenario(above_all_day)
    day = str(bars.index[-1].date())
    res = run(bars, NoiseConfig(skip_dates=f"2026-01-01,{day}"))
    assert res.trades == [] and res.events == []
    assert len(res.bands) == 12  # the noise area is still worked out
    assert run(bars, NoiseConfig(skip_dates="")).trades


def test_default_date_list_is_valid_and_covers_the_holidays():
    from mnqbot.noise import SKIP_DATES

    dates = pd.to_datetime(SKIP_DATES.split(","), format="%Y-%m-%d")
    assert dates.is_monotonic_increasing and len(set(dates)) == len(dates) == 23
    assert {"2026-11-26", "2026-11-27", "2026-12-24", "2027-07-05", "2027-11-26"} <= set(SKIP_DATES.split(","))


def test_no_trades_until_the_lookback_is_full():
    bars, _ = scenario(above_all_day)
    assert run(bars, NoiseConfig(lookback=15)).trades == []
    assert run(bars, NoiseConfig(lookback=14)).trades


def short_session_then_breakout() -> pd.DataFrame:
    """13 quiet sessions, a half day (checks after 13:00 missing), then a session that breaks out at 10:00."""
    frames, p, day = quiet_history(13)
    half = session(str(day.date()), p, [p * 1.001] * 42)  # 09:30 .. 12:55
    nxt = pd.bdate_range(day, periods=2)[1]
    frames += [half, session(str(nxt.date()), p * 1.001, above_all_day(p * 1.001))]
    return annotate(pd.concat(frames))


def gappy_session_then_breakout() -> pd.DataFrame:
    """13 quiet sessions, one that reaches 16:00 but is missing the bar ending 12:30, then a 10:00 breakout."""
    frames, p, day = quiet_history(13)
    gappy = session(str(day.date()), p, [p * 1.001] * BARS_PER_DAY)
    gappy = gappy.drop(gappy.index[35])  # the 12:25 bar, so there is no 12:30 check
    nxt = pd.bdate_range(day, periods=2)[1]
    frames += [gappy, session(str(nxt.date()), p * 1.001, above_all_day(p * 1.001))]
    return annotate(pd.concat(frames))


def test_short_session_is_not_added_to_the_history():
    res = run(short_session_then_breakout())
    assert res.trades == [] and res.bands == []


def test_session_missing_a_check_is_not_added_to_the_history():
    res = run(gappy_session_then_breakout())
    assert res.trades == [] and res.bands == []


def test_position_left_open_by_a_short_session_is_closed_at_the_next_open_bar():
    frames, p, day = quiet_history(14)
    half = session(str(day.date()), p, above_all_day(p)[:42])
    nxt = pd.bdate_range(day, periods=2)[1]
    frames += [half, session(str(nxt.date()), p * 1.002, [p * 1.002] * BARS_PER_DAY)]
    res = run(annotate(pd.concat(frames)))
    t = res.trades[0]
    assert t.reason == "Session ended" and t.exit_bar == bar(14, 42)  # first bar of the next session
    assert res.events[-1] == (bar(14, 42), "EXIT")


def test_15_minute_bars_trade_the_same_as_5_minute_bars():
    """True for the half-hour exit. With the resting stop, a fill can land on a different bar's open, so the
    5-minute chart is the reference and other bar lengths can differ slightly."""
    five = synth_bars(sessions=60, seed=11)
    fifteen = annotate(resample(five[["open", "high", "low", "close", "volume"]], "15min"))
    a, b = run(five, CHECK), run(fifteen, CHECK)
    def key(r):  # the 16:00 exit is stamped with its bar's open time, which differs by bar length
        return [(t.entry_time, t.exit_time.date() if t.reason == "16:00 close" else t.exit_time, t.direction,
                 round(t.entry, 6), round(t.exit, 6), t.reason) for t in r.trades]

    assert len(a.trades) > 10 and key(a) == key(b)


def test_bar_length_must_divide_30_minutes():
    with pytest.raises(ValueError):
        run(synth_bars(sessions=3, seed=1), minutes=45)


# ----------------------------------------------------------------- Pine parity (slow)

def run_pine(bars, inputs=None, minutes=5):
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine

    rt = PineRuntime(load_pine(NOISE_PINE), bars, inputs or {}, timeframe_seconds=60 * minutes)
    bands = []

    def on_bar(i, g):
        bands.append((i, g["ub"], g["lb"]))

    rt.run(on_bar)
    trades = [(t["entry_bar"], t["exit_bar"], t["dir"], round(t["entry"], 6), round(t["exit"], 6),
               round(t["pnl"], 6), t["reason"]) for t in rt.strategy.closed]
    events = [(i, msg.split()[0].rstrip(":")) for i, msg in rt.alerts]
    labels = [(i, text.split()[0]) for i, text in rt.labels]
    assert labels == events, "every alert has a matching label on the chart"
    return trades, events, {i: (u, lo) for i, u, lo in bands}


def assert_parity(bars, minutes=5, lookback=14, skip_dates=None, exit_mode="stop", stop_buffer=None):
    cfg, inputs = NoiseConfig(lookback=lookback, exit_mode=exit_mode), {"Sessions in the noise average": lookback}
    inputs["Exit"] = "Resting stop at the line" if exit_mode == "stop" else "Half-hour check"
    if stop_buffer is not None:
        cfg.stop_buffer = inputs["Stop distance past the line, in noise units"] = stop_buffer
    if skip_dates is not None:
        cfg.skip_dates = inputs["Don't trade on these dates"] = skip_dates
    res = run(bars, cfg, minutes=minutes)
    trades, events, pine_bands = run_pine(bars, inputs, minutes)
    assert trades == trades_of(res)
    assert events == res.events
    for i, u, lo in res.bands:
        assert pine_bands[i] == (u, lo)
    return res


HAND_BUILT = {
    "buy and flat": lambda: scenario(above_all_day)[0],
    "exit back inside": lambda: scenario(above_then_inside)[0],
    "reverse": lambda: scenario(above_then_below)[0],
    "short session not in the history": short_session_then_breakout,
    "session missing a check not in the history": gappy_session_then_breakout,
    "stop touched between checks": lambda: with_low(scenario(above_all_day)[0], bar(14, 8), P0 * 1.001 ** 14 * 1.0005),
    "stop touched on the entry bar": lambda: with_low(scenario(above_all_day)[0], bar(14, CHECK_10_00 + 1),
                                                      P0 * 1.001 ** 14 * 1.0005),
    "entry bar opens inside the line": lambda: with_low(scenario(above_all_day)[0], bar(14, CHECK_10_00 + 1),
                                                        P0 * 1.001 ** 14 * 1.0005, open_=P0 * 1.001 ** 14 * 1.0005),
    "line moves past the price": lambda: widening_history_then_breakout()[0],
    "stop buffer holds": lambda: with_low(scenario(above_all_day)[0], bar(14, 8),
                                          P0 * 1.001 ** 14 * 1.001 * (1 - BUF) + 0.05),
    "stop buffer hit": lambda: with_low(scenario(above_all_day)[0], bar(14, 8),
                                        P0 * 1.001 ** 14 * 1.001 * (1 - BUF) - 0.05),
}
MODES = {"stop": ("stop", None), "stop on the line": ("stop", 0.0), "check": ("check", None)}


@pytest.mark.slow
@pytest.mark.parametrize("name", list(HAND_BUILT))
@pytest.mark.parametrize("mode", list(MODES))
def test_pine_hand_built(name, mode):
    exit_mode, buf = MODES[mode]
    assert_parity(HAND_BUILT[name](), exit_mode=exit_mode, stop_buffer=buf)


@pytest.mark.slow
def test_pine_skips_listed_dates():
    bars, _ = scenario(above_all_day)
    day = str(bars.index[-1].date())
    assert assert_parity(bars, skip_dates=f"2026-01-01,{day}").trades == []
    assert assert_parity(bars, skip_dates="").trades


@pytest.mark.slow
def test_pine_short_session_cases():
    frames, p, day = quiet_history(14)
    half = session(str(day.date()), p, above_all_day(p)[:42])
    nxt = pd.bdate_range(day, periods=2)[1]
    frames += [half, session(str(nxt.date()), p * 1.002, [p * 1.002] * BARS_PER_DAY)]
    res = assert_parity(annotate(pd.concat(frames)))
    assert res.trades[0].reason == "Session ended"


RANDOM_CASES = [(5, "stop"), (15, "stop"), (5, "stop on the line"), (5, "check")]


@pytest.mark.slow
@pytest.mark.parametrize("minutes,mode", RANDOM_CASES)
def test_pine_random_sessions(minutes, mode):
    bars = synth_bars(sessions=90, seed=5)
    if minutes != 5:
        bars = annotate(resample(bars[["open", "high", "low", "close", "volume"]], f"{minutes}min"))
    exit_mode, buf = MODES[mode]
    res = assert_parity(bars, minutes, exit_mode=exit_mode, stop_buffer=buf)
    assert len(res.trades) > 20 and {e for _, e in res.events} >= {"BUY", "SELL", "EXIT", "FLAT"}
    if mode == "stop on the line":
        assert any(t.reason == "Back inside" and t.exit_bar == t.entry_bar for t in res.trades), "a fill-bar stop"


@pytest.mark.slow
def test_pine_rth_only_chart_and_shorter_lookback():
    bars = synth_bars(sessions=60, seed=8)
    rth = bars[bars.is_rth]
    res = assert_parity(rth, lookback=5)
    assert len(res.trades) > 20
