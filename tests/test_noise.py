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
    res = run(bars)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "EXIT")]
    t = res.trades[0]
    assert (t.entry_bar, t.exit_bar, t.reason) == (bar(14, CHECK_10_00 + 1), bar(14, CHECK_10_30 + 1), "Back inside")
    assert t.exit == pytest.approx(p - 0.25)
    assert t.pnl == pytest.approx((p - 0.25 - (p * 1.002 + 0.25)) * 2 - 1.24)


def test_reverse_when_through_the_other_side():
    bars, p = scenario(above_then_below)
    res = run(bars)
    assert res.events == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "REVERSE"),
                          (bar(14, CLOSE_16_00), "FLAT")]
    long, short = res.trades
    lo = p * 0.998
    assert (long.direction, long.exit_bar, long.reason) == (1, bar(14, CHECK_10_30 + 1), "reversed")
    assert long.exit == pytest.approx(lo - 0.25)
    assert (short.direction, short.entry_bar, short.exit_bar) == (-1, bar(14, CHECK_10_30 + 1), bar(14, CLOSE_16_00))
    assert short.entry == pytest.approx(lo - 0.25) and short.exit == pytest.approx(lo + 0.25)
    assert short.pnl == pytest.approx(-0.5 * 2 - 1.24)


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
    five = synth_bars(sessions=60, seed=11)
    fifteen = annotate(resample(five[["open", "high", "low", "close", "volume"]], "15min"))
    a, b = run(five), run(fifteen)
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
    return trades, events, {i: (u, lo) for i, u, lo in bands}


def assert_parity(bars, minutes=5, lookback=14):
    res = run(bars, NoiseConfig(lookback=lookback), minutes=minutes)
    trades, events, pine_bands = run_pine(bars, {"Sessions in the noise average": lookback}, minutes)
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
}


@pytest.mark.slow
@pytest.mark.parametrize("name", list(HAND_BUILT))
def test_pine_hand_built(name):
    assert_parity(HAND_BUILT[name]())


@pytest.mark.slow
def test_pine_short_session_cases():
    frames, p, day = quiet_history(14)
    half = session(str(day.date()), p, above_all_day(p)[:42])
    nxt = pd.bdate_range(day, periods=2)[1]
    frames += [half, session(str(nxt.date()), p * 1.002, [p * 1.002] * BARS_PER_DAY)]
    res = assert_parity(annotate(pd.concat(frames)))
    assert res.trades[0].reason == "Session ended"


@pytest.mark.slow
@pytest.mark.parametrize("minutes", [5, 15])
def test_pine_random_sessions(minutes):
    bars = synth_bars(sessions=90, seed=5)
    if minutes != 5:
        bars = annotate(resample(bars[["open", "high", "low", "close", "volume"]], f"{minutes}min"))
    res = assert_parity(bars, minutes)
    assert len(res.trades) > 20 and {e for _, e in res.events} >= {"BUY", "SELL", "EXIT", "FLAT"}


@pytest.mark.slow
def test_pine_rth_only_chart_and_shorter_lookback():
    bars = synth_bars(sessions=60, seed=8)
    rth = bars[bars.is_rth]
    res = assert_parity(rth, lookback=5)
    assert len(res.trades) > 20
