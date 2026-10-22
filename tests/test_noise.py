"""Noise-area momentum: hand-built cases for mnqbot/noise.py, and parity with pine/mnq_noise_momentum.pine.

Hand-built history: 14 quiet sessions whose every half-hour check sits exactly 0.1% above the 09:30 open,
so on the next session the noise area is open (= previous close) * (1 +/- 0.001) at every check.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import synth_bars

from mnqbot.data import NY, annotate, resample
from mnqbot.noise import NoiseConfig, run

ROOT = Path(__file__).resolve().parents[1]
NOISE_PINE = ROOT / "pine" / "mnq_noise_momentum.pine"
FUNDED = "FUNDED ACCOUNT (tick for the funded contracts; untick for the evaluation's)"  # the script's account switch
LOCK = "Lock a small win: trigger, in max losses (0 = off)"  # the script's default is 0.85 (v1.7); the reference's 1.0
TIGHTEN = "Stop only ever tightens"  # the script's default is on (v1.8); the reference's off
MAX_LOSS = "Max loss per trade, $ (all contracts, 0 = off)"  # the script's default is $500 (v2.0); the reference's $350
TP = "Take profit, noise units from the entry (0 = off)"  # the script's default is 2.0 (v2.0); the reference's 1.5
AFTER_QTY = "After a losing trade: contracts (0 = the same)"  # the script's default is 9 (v2.1); the reference's off
AFTER_ML = "After a losing trade: max loss per trade, $ (0 = the same)"  # 700 (v2.1); the reference's off
LAST_ENTRY = "Last check for new entries"  # the script's default is 15:00 (v2.2); the reference's every check
V21 = {"max_loss_per_trade": 500.0, "lock_at": 0.75, "take_profit": 2.0, "tighten_only": True,
       "after_loss_qty_div": 10 / 9, "after_loss_ml_mult": 1.4, "last_entry_end": 900}  # the script's defaults, 10 MNQ
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


def below_all_day(p):
    return [p] * CHECK_10_00 + [p * 0.998] * (BARS_PER_DAY - CHECK_10_00)


CHECK_14_00 = 53  # the bar whose close is 14:00, the Fed statement
TEST_DAY = "2026-03-20"  # the session after quiet_history's 14 sessions


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


def test_ten_contracts_scale_the_trade():
    bars, _ = scenario(above_all_day)
    one, ten = run(bars).trades[0], run(bars, NoiseConfig(qty=10)).trades[0]
    assert ten.qty == 10 and ten.pnl == pytest.approx(10 * one.pnl)


def test_max_loss_cap_is_a_second_stop_live_from_the_fill():
    bars, p = scenario(above_all_day)
    entry = p * 1.002 + 0.25  # the fill, with slippage; the line stop is about 25 points below it
    cap = NoiseConfig(max_loss_per_trade=20.0)  # 1 contract: a stop $20 = 10 points from the fill
    t = run(with_low(bars, bar(14, 8), entry - 12), cap).trades[0]  # dips 12 points: past the cap, not the line
    assert (t.exit_bar, t.reason) == (bar(14, 8), "Max loss") and t.exit == pytest.approx(entry - 10 - 0.25)
    assert t.pnl == pytest.approx(-20 - 0.5 - 1.24)  # the cap, plus the exit tick and fees
    default = run(with_low(bars, bar(14, 8), entry - 12)).trades[0]
    assert default.reason == "16:00 close"  # with the default $350 cap the line stop is the closer one
    same_bar = run(with_low(bars, bar(14, CHECK_10_00 + 1), entry - 12), cap).trades[0]
    # on the fill bar the cap works too, like a bracket order, measured from the expected fill (signal close + tick)
    expected_fill = bars.close.iloc[bar(14, CHECK_10_00)] + 0.25
    assert (same_bar.exit_bar, same_bar.reason) == (bar(14, CHECK_10_00 + 1), "Max loss")
    assert same_bar.exit == pytest.approx(expected_fill - 10 - 0.25)
    gap_up = bars.copy()  # the fill comes in above the signal close: the fill-bar cap still sits from the close
    gap_up.iloc[bar(14, CHECK_10_00 + 1), gap_up.columns.get_loc("open")] += 3
    gap_up.iloc[bar(14, CHECK_10_00 + 1), gap_up.columns.get_loc("high")] += 3
    t = run(with_low(gap_up, bar(14, CHECK_10_00 + 1), expected_fill - 10.5), cap).trades[0]
    assert t.reason == "Max loss" and t.exit == pytest.approx(expected_fill - 10 - 0.25)
    ten = run(with_low(bars, bar(14, 8), entry - 12), NoiseConfig(max_loss_per_trade=200.0, qty=10)).trades[0]
    assert ten.reason == "Max loss" and ten.exit == pytest.approx(entry - 10 - 0.25)  # $200 over 10 = $20 each


def with_high(bars: pd.DataFrame, i: int, high: float) -> pd.DataFrame:
    out = bars.copy()
    out.iloc[i, out.columns.get_loc("high")] = high
    return out


def test_take_profit_fills_a_tick_through_from_the_bar_after_the_fill():
    bars, p = scenario(above_all_day)
    entry = p * 1.002 + 0.25
    tp = entry * (1 + 1.5 * 0.001)  # 1.5 noise units; the quiet history's noise is 0.1%
    t = run(with_high(bars, bar(14, 8), tp + 0.25)).trades[0]
    assert (t.exit_bar, t.reason) == (bar(14, 8), "Target") and t.exit == pytest.approx(tp)
    assert t.pnl == pytest.approx((tp - entry) * 2 - 1.24)  # a limit: no slippage on the exit
    assert run(with_high(bars, bar(14, 8), tp + 0.25)).events[1] == (bar(14, 8), "TARGET")
    assert run(with_high(bars, bar(14, 8), tp)).trades[0].reason == "16:00 close"  # touched, not traded through
    fill_bar = run(with_high(bars, bar(14, CHECK_10_00 + 1), tp + 1)).trades[0]
    assert fill_bar.reason == "16:00 close"  # the limit needs the fill price: it starts the bar after
    off = run(with_high(bars, bar(14, 8), tp + 1), NoiseConfig(take_profit=0)).trades[0]
    assert off.reason == "16:00 close"
    check = run(with_high(bars, bar(14, 8), tp + 1), CHECK).trades[0]
    assert check.reason != "Target"  # the half-hour-check exit has no take-profit


def test_fed_day_no_shorts_before_14_00():
    bars, p = scenario(below_all_day)
    assert scenario(below_all_day)[0].index[bar(14, 0)].strftime("%Y-%m-%d") == TEST_DAY
    assert run(bars).events[0] == (bar(14, CHECK_10_00), "SELL")  # an ordinary day: short at 10:00
    fed = NoiseConfig(fed_dates=f"2026-01-28,{TEST_DAY}")
    res = run(bars, fed)
    assert res.events[0] == (bar(14, CHECK_14_00), "SELL")  # the first check at or after the 14:00 statement
    assert res.trades[0].direction == -1 and res.trades[0].entry_bar == bar(14, CHECK_14_00 + 1)
    off = NoiseConfig(fed_dates=TEST_DAY, fed_no_shorts=False)
    assert run(bars, off).events[0] == (bar(14, CHECK_10_00), "SELL")


def test_fed_day_keeps_longs_and_turns_a_morning_reversal_into_an_exit():
    bars, _ = scenario(above_all_day)
    fed = NoiseConfig(fed_dates=TEST_DAY)
    assert trades_of(run(bars, fed)) == trades_of(run(bars))  # longs as usual
    bars, _ = scenario(above_then_below)
    res = run(bars, NoiseConfig(fed_dates=TEST_DAY, exit_mode="check"))
    assert res.events[:3] == [(bar(14, CHECK_10_00), "BUY"), (bar(14, CHECK_10_30), "EXIT"),
                              (bar(14, CHECK_14_00), "SELL")]


def test_default_fed_dates_are_wednesdays_or_thursdays_and_eight_a_year():
    from mnqbot.noise import FED_DATES
    days = pd.to_datetime(FED_DATES.split(","))
    assert set(days.year) == {2026, 2027} and all((days.year == y).sum() == 8 for y in (2026, 2027))
    assert set(days.dayofweek) <= {2, 3}


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
    hooks = [(i, msg) for i, msg in rt.alerts if msg.startswith("{")]  # webhook messages, sent with order fills
    heads = [(i, 1 if " BUY likely" in msg else -1) for i, msg in rt.alerts if msg.startswith("HEADS-UP")]
    events = [(i, msg.split()[0].rstrip(":")) for i, msg in rt.alerts
              if not msg.startswith("{") and not msg.startswith("HEADS-UP")]
    labels = [(i, text.split()[0]) for i, text in rt.labels]
    assert labels == events, "every alert has a matching label on the chart"
    logs = [t for t in rt.tables if t.columns == 7]
    assert len(logs) == 1, "one trade-log table"
    return trades, events, {i: (u, lo) for i, u, lo in bands}, logs[0].grid(), hooks, heads


LOG_HEADER = ["Opened (NY)", "Side", "Entry", "Closed (NY)", "Exit", "P/L", "Why"]
WHY = {"Back inside": "stop at the line", "Max loss": "max loss stop", "16:00 close": "16:00 close",
       "Session ended": "session ended", "reversed": "reversed", "Target": "take profit", "Lock": "locked win"}


def money(text):
    return float(text.replace("$", "").replace(",", ""))


def assert_trade_log(log, res, exit_mode, rows=10):
    """The chart's trade log shows the last trades, newest first: times, side, prices, P/L and why."""
    assert log[0] == LOG_HEADER
    body = log[1:]
    if body and body[0][3] == "OPEN":  # the data ended mid-trade
        body = body[1:]
    why = dict(WHY, **({"Back inside": "back inside at a check"} if exit_mode == "check" else {}))
    expected = []
    for t in reversed(res.trades[-rows:]):
        expected.append([t.entry_time.strftime("%m-%d %H:%M"), f"{'LONG' if t.direction > 0 else 'SHORT'} {t.qty}",
                         t.entry, t.exit_time.strftime("%m-%d %H:%M"), t.exit, round(t.pnl, 2), why[t.reason]])
    got = [[r[0], r[1], float(r[2]), r[3], float(r[4]), money(r[5]), r[6]] for r in body]
    assert len(got) == len(expected)
    for g, e in zip(got, expected, strict=True):
        assert g[:2] == e[:2] and g[3] == e[3] and g[6] == e[6], (g, e)
        assert g[2] == pytest.approx(e[2], abs=0.125) and g[4] == pytest.approx(e[4], abs=0.125)  # to the tick
        assert g[5] == pytest.approx(e[5], abs=0.006), (g, e)


def assert_parity(bars, minutes=5, lookback=14, skip_dates=None, exit_mode="stop", stop_buffer=None, qty=1,
                  max_loss=None, fed_dates=None, fed_no_shorts=None, take_profit=None, hook=None, lock_at=None,
                  max_losers=None, after_loss=None, last_entry=None):
    cfg = NoiseConfig(lookback=lookback, exit_mode=exit_mode, qty=qty)
    inputs = {"Sessions in the noise average": lookback}
    if lock_at is not None:
        cfg.lock_at = lock_at
    inputs[LOCK] = cfg.lock_at  # explicit: the script's default (0.85) is not the reference's (1.0)
    if max_losers is not None:
        cfg.max_losers = inputs["Max losing trades a day (0 = no limit)"] = max_losers
    if hook is not None:  # webhook orders on, for this contract
        inputs["Webhook orders"], inputs["Contract for the webhook (blank = the chart's)"] = "TradersPost", hook
        cfg.tighten_only = True
    inputs[TIGHTEN] = cfg.tighten_only  # explicit: the script's default (on) is not the reference's (off)
    if after_loss is not None:  # (contracts, max loss) after a losing trade, as the script takes them
        cfg.after_loss_qty_div, cfg.after_loss_ml_mult = qty / after_loss[0], after_loss[1] / (max_loss or 350.0)
    inputs[AFTER_QTY], inputs[AFTER_ML] = after_loss if after_loss is not None else (0, 0.0)
    if last_entry is not None:
        cfg.last_entry_end = last_entry
    inputs[LAST_ENTRY] = "15:00" if cfg.last_entry_end == 900 else "15:30"
    inputs["Exit"] = "Resting stop at the line" if exit_mode == "stop" else "Half-hour check"
    inputs[FUNDED] = True  # the script's default is the evaluation's 3 contracts
    inputs["Contracts on a funded account"] = qty  # the script's default is 10; the reference's is 1
    if take_profit is not None:
        cfg.take_profit = take_profit
    inputs[TP] = cfg.take_profit  # explicit: the script's default (2.0) is not the reference's (1.5)
    if max_loss is not None:
        cfg.max_loss_per_trade = max_loss
    inputs[MAX_LOSS] = cfg.max_loss_per_trade  # explicit: the script's default ($450) is not the reference's ($350)
    if stop_buffer is not None:
        cfg.stop_buffer = inputs["Stop distance past the line, in noise units"] = stop_buffer
    if skip_dates is not None:
        cfg.skip_dates = inputs["Don't trade on these dates"] = skip_dates
    if fed_dates is not None:
        cfg.fed_dates = inputs["Fed announcement days"] = fed_dates
    if fed_no_shorts is not None:
        cfg.fed_no_shorts = inputs["Fed days: no shorts before 14:00"] = fed_no_shorts
    res = run(bars, cfg, minutes=minutes)
    trades, events, pine_bands, log, hooks, heads = run_pine(bars, inputs, minutes)
    assert trades == trades_of(res)
    assert events == res.events
    assert heads == res.headsups, "the heads-up alerts five minutes before a check"
    for i, u, lo in res.bands:
        assert pine_bands[i] == (u, lo)
    assert_trade_log(log, res, exit_mode)
    if hook is None:
        assert hooks == [], "no webhook messages unless webhook orders are on"
    else:
        assert_webhooks(hooks, res, hook or "MNQ1!", qty)
    return res


def assert_webhooks(hooks, res, ticker, qty):
    """With webhook orders on, every fill sends one TradersPost message: an entry (with the bracket the reference
    computed at the signal) when an entry fills, and an exit (cancelling the bracket) when a trade closes. A reversal
    is one buy/sell message, which TradersPost reads as close and reverse."""
    got = [(i, json.loads(m)) for i, m in hooks]  # every message is valid JSON
    orders = {o[0] + 1: o for o in res.orders}  # fill bar -> the order sent at the signal
    want = []
    for t in res.trades:
        _, d, est, stop, tp = orders[t.entry_bar]
        assert d == t.direction
        msg = {"ticker": ticker, "action": "buy" if d > 0 else "sell", "orderType": "market", "quantity": qty,
               "price": est}
        if not math.isnan(stop):
            msg["stopLoss"] = {"type": "stop", "stopPrice": stop}
        if not math.isnan(tp):
            msg["takeProfit"] = {"limitPrice": tp}
        want.append((t.entry_bar, msg))
        if t.reason != "reversed":
            want.append((t.exit_bar, {"ticker": ticker, "action": "exit", "cancel": True}))
    want.sort(key=lambda x: x[0])  # stable: an entry before an exit on the same bar
    assert len(got) == len(want)
    for (gi, g), (wi, w) in zip(got, want, strict=True):
        assert gi == wi, (gi, g, wi, w)
        assert g.keys() == w.keys() and g["ticker"] == w["ticker"] and g["action"] == w["action"], (g, w)
        if "price" in w:
            assert g["orderType"] == "market" and g["quantity"] == w["quantity"]
            assert g["price"] == pytest.approx(w["price"], abs=0.005)
        for k, field in (("stopLoss", "stopPrice"), ("takeProfit", "limitPrice")):
            if k in w:
                assert g[k][field] == pytest.approx(w[k][field], abs=0.005), (k, g, w)


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
def test_pine_max_loss_cap():
    bars, p = scenario(above_all_day)
    entry = p * 1.002 + 0.25
    res = assert_parity(with_low(bars, bar(14, 8), entry - 12), max_loss=20.0)
    assert res.trades[0].reason == "Max loss"
    fill_bar = assert_parity(with_low(bars, bar(14, CHECK_10_00 + 1), entry - 12), max_loss=20.0)
    assert fill_bar.trades[0].reason == "Max loss"  # live from the fill bar, like a bracket order
    assert fill_bar.trades[0].exit_bar == bar(14, CHECK_10_00 + 1)
    assert assert_parity(synth_bars(sessions=60, seed=9), max_loss=100.0).trades


@pytest.mark.slow
def test_pine_ten_contracts():
    bars, _ = scenario(above_then_below)
    res = assert_parity(bars, qty=10)
    assert res.trades[0].qty == 10 and all(t.qty == 10 for t in res.trades)


@pytest.mark.slow
@pytest.mark.slow
def test_pine_take_profit():
    bars, p = scenario(above_all_day)
    tp = (p * 1.002 + 0.25) * (1 + 1.5 * 0.001)
    assert assert_parity(with_high(bars, bar(14, 8), tp + 0.25)).trades[0].reason == "Target"
    assert assert_parity(with_high(bars, bar(14, 8), tp)).trades[0].reason == "16:00 close"
    res = assert_parity(synth_bars(sessions=90, seed=5))
    assert sum(t.reason == "Target" for t in res.trades) >= 3, "the random sessions reach the target too"


def lock_case(reach: float):
    """10 MNQ, $350 max loss (17.5 points a contract): the long's high reaches entry + reach at 10:40, then the bars
    sit a tick under the entry."""
    bars, p = scenario(above_all_day)
    entry = p * 1.002 + 0.25
    return with_high(bars, bar(14, 8), entry + reach), entry


def test_lock_moves_the_stop_the_bar_after_the_trigger():
    cfg = NoiseConfig(qty=10, max_loss_per_trade=350.0)
    bars, entry = lock_case(17.5 + 0.01)
    t = run(bars, cfg).trades[0]
    # the trigger was touched at 10:40; at 10:45 the bar opens a tick under the entry, below the lock at entry + 2.5,
    # so the stop fills at that open (on this chart the lock is a bar late; a broker's auto-breakeven fills at +2.5)
    assert (t.reason, t.exit_bar, t.exit) == ("Lock", bar(14, 9), pytest.approx(entry - 0.25 - 0.25))
    bars, _ = lock_case(17.5 - 0.25)  # a tick short of the trigger: no lock
    assert run(bars, cfg).trades[0].reason == "16:00 close"
    assert run(lock_case(17.5 + 0.01)[0], NoiseConfig(qty=10, max_loss_per_trade=350.0, lock_at=0)).trades[0].reason \
        == "16:00 close", "lock_at 0 turns it off"


def test_lock_fills_at_its_price_when_price_falls_through_it():
    cfg = NoiseConfig(qty=10, max_loss_per_trade=350.0)
    bars, entry = lock_case(17.5 + 0.01)
    up = bars.copy()
    for j in range(8, 12):  # the bars after the trigger trade higher, then one falls back through the lock
        i = bar(14, j)
        up.iloc[i, up.columns.get_loc("open")] = up.iloc[i, up.columns.get_loc("close")] = entry + 10
        up.iloc[i, up.columns.get_loc("low")] = entry + 9
        up.iloc[i, up.columns.get_loc("high")] = entry + 17.51 if j == 8 else entry + 11
    i = bar(14, 12)
    up.iloc[i, up.columns.get_loc("open")] = entry + 10
    up.iloc[i, up.columns.get_loc("high")] = entry + 10
    t = run(up, cfg).trades[0]
    assert (t.reason, t.exit_bar, t.exit) == ("Lock", i, pytest.approx(entry + 2.5 - 0.25))
    assert t.pnl > 0, "a locked trade closes as a small winner after fees and slippage"


def losers_before_each_entry(res):
    """For every trade, the losing trades (session ends aside) that closed earlier the same day."""
    out = []
    for t in res.trades:
        day = t.entry_time.date()
        out.append(sum(u.pnl < 0 and u.reason != "Session ended" and u.exit_time.date() == day
                       and u.exit_bar < t.entry_bar for u in res.trades))
    return out


def test_daily_loser_limit_blocks_new_entries_only():
    bars = synth_bars(sessions=120, seed=3)
    free = run(bars, NoiseConfig(qty=10, max_loss_per_trade=350.0, max_losers=0, skip_dates=""))
    capped = run(bars, NoiseConfig(qty=10, max_loss_per_trade=350.0, max_losers=2, skip_dates=""))
    assert max(losers_before_each_entry(free)) > 2, "the random sessions have days with more than 2 losers"
    assert max(losers_before_each_entry(capped)) <= 2, "no entry after the 2nd loser of the day"
    assert len(capped.trades) < len(free.trades)
    first_of_day = [{t.entry_time.date(): t.entry_bar for t in reversed(r.trades)} for r in (free, capped)]
    assert first_of_day[0] == first_of_day[1], "the limit never touches a day's first trade"


def test_headsups_come_five_minutes_before_most_signals():
    bars = synth_bars(sessions=120, seed=3)
    res = run(bars, NoiseConfig(qty=10, max_loss_per_trade=350.0))
    signals = {o[0]: o[1] for o in res.orders}
    assert len(res.headsups) >= 10
    followed = sum(signals.get(i + 1) == d for i, d in res.headsups)  # the check is the next 5-minute bar
    assert followed / len(res.headsups) > 0.5
    idx = bars.index.tz_convert(NY)
    for i, _ in res.headsups:
        assert (idx[i].hour * 60 + idx[i].minute + 10 - 600) % 30 == 0, "the bar ending five minutes before a check"


def test_tighten_only_stop_never_loosens():
    """Webhook mode: the stop is the tightest one so far in the trade. Over random sessions it exits some trades
    earlier than the moving line would (so it is exercised), and never later."""
    bars = synth_bars(sessions=120, seed=3)
    base, held = (run(bars, NoiseConfig(tighten_only=t, skip_dates="")) for t in (False, True))
    a = {t.entry_bar: t for t in base.trades}
    earlier = 0
    for t in held.trades:
        b = a.get(t.entry_bar)
        if b is None:
            continue  # the trades diverged after an earlier exit
        assert t.exit_bar <= b.exit_bar
        earlier += t.exit_bar < b.exit_bar
    assert earlier >= 1


@pytest.mark.slow
def test_pine_lock():
    assert assert_parity(lock_case(17.5 + 0.01)[0], qty=10, max_loss=350.0).trades[0].reason == "Lock"
    assert assert_parity(lock_case(17.5 - 0.25)[0], qty=10, max_loss=350.0).trades[0].reason == "16:00 close"
    assert assert_parity(lock_case(17.5 + 0.01)[0], qty=10, max_loss=350.0, lock_at=0).trades[0].reason == "16:00 close"
    res = assert_parity(synth_bars(sessions=120, seed=3), qty=10, max_loss=350.0)
    assert sum(t.reason == "Lock" for t in res.trades) >= 5
    assert len(res.headsups) >= 10, "the heads-ups are checked against the script too"
    res = assert_parity(synth_bars(sessions=120, seed=3), qty=10, max_loss=350.0, hook="MNQZ2026")
    assert sum(t.reason == "Lock" for t in res.trades) >= 5, "the lock with webhook orders"


@pytest.mark.slow
def test_pine_daily_loser_limit():
    bars = synth_bars(sessions=120, seed=3)
    res = assert_parity(bars, qty=10, max_loss=350.0, max_losers=2)
    assert max(losers_before_each_entry(res)) <= 2
    assert len(res.trades) < len(run(bars, NoiseConfig(qty=10, max_loss_per_trade=350.0, max_losers=0)).trades)
    assert_parity(bars, qty=10, max_loss=350.0, max_losers=0)
    assert_parity(bars, qty=10, max_loss=350.0, max_losers=1, exit_mode="check")


def eval_walk(day_pnl, target, dd, cons, min_days):
    """The evaluation's end-of-day walk, as the chart's tracker does it (mnqbot.report.run_eval's rules)."""
    rel = peak = best = 0.0
    tdays, state = 0, "in progress"
    for pnl in day_pnl:
        failed = rel + min(pnl, 0.0) <= min(peak - dd, 0.0)
        rel += pnl  # the failing day's balance is shown too
        tdays += 1
        best = max(best, pnl)
        peak = max(peak, rel)
        if failed:
            state = "FAILED"
            break
        if rel >= target and tdays >= min_days and (cons <= 0 or best < cons / 100 * rel):
            state = "PASSED"
            break
    return state, rel, peak, best, tdays


@pytest.mark.slow
@pytest.mark.parametrize("target", [3000.0, 300.0])
def test_pine_evaluation_tracker(target):
    bars = synth_bars(sessions=120, seed=3)
    days = sorted({d.date() for d in bars.index.tz_convert(NY)})
    start = days[40]
    inputs = {FUNDED: True, "Contracts on a funded account": 10, LOCK: 1.0, TIGHTEN: False, TP: 1.5, AFTER_QTY: 0,
              AFTER_ML: 0.0, LAST_ENTRY: "15:30",
              "Max loss per trade, $ (all contracts, 0 = off)": 350.0,
              "Evaluation start date, YYYYMMDD (0 = off)": int(start.strftime("%Y%m%d")), "Profit target, $": target}
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine

    rt = PineRuntime(load_pine(NOISE_PINE), bars, inputs, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    tf = run(bars, NoiseConfig(qty=10, max_loss_per_trade=350.0)).trades_frame()
    tf = tf[tf.exit_time.dt.date >= start]
    day_pnl = tf.groupby(tf.exit_time.dt.date).pnl.sum().tolist()
    state, rel, peak, best, tdays = eval_walk(day_pnl, target, 2000.0, 50.0, 5)
    grid = [t.grid() for t in rt.tables if t.columns == 2 and t.grid() and t.grid()[0][0].startswith("Evaluation")][0]
    assert grid[0][1] == state
    assert money(grid[1][1].split(" of ")[0]) == pytest.approx(rel, abs=0.01)
    assert money(grid[2][1].split(":")[0]) == pytest.approx(min(peak - 2000.0, 0.0), abs=0.01)
    assert money(grid[3][1].split(" ")[0]) == pytest.approx(best, abs=0.01)
    assert int(grid[5][1]) == tdays
    if target == 300.0:
        assert state in ("PASSED", "FAILED"), "a low target decides the walk"


@pytest.mark.slow
def test_pine_dashboard_shows_the_next_checks_lines():
    """The dashboard's preview of the next check's lines equals the lines that check then uses."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine

    full = synth_bars(sessions=40, seed=7)
    res = run(full, NoiseConfig())
    i, upper, lower = res.bands[-5]  # a check late in the data; cut the bars ten minutes before it
    cut = full.iloc[: i - 1]
    rt = PineRuntime(load_pine(NOISE_PINE), cut, {FUNDED: True, "Contracts on a funded account": 1, LOCK: 1.0,
                                                    TIGHTEN: False, MAX_LOSS: 350.0, TP: 1.5,
                                                    AFTER_QTY: 0, AFTER_ML: 0.0, LAST_ENTRY: "15:30"},
                     timeframe_seconds=300)
    rt.run(lambda j, g: None)
    dash = [t.grid() for t in rt.tables if t.columns == 2 and t.grid() and t.grid()[0][0].startswith("MNQ Noise")][0]
    cell = dash[2][1]
    when = full.index[i].tz_convert(NY) + pd.Timedelta(minutes=5)  # the check's close
    assert f"at {when.hour}:{when.minute:02d}: {upper:.2f} / {lower:.2f}" in cell, cell


@pytest.mark.slow
@pytest.mark.parametrize("funded, eval_qty, qty", [(None, None, 10), (False, 3, 3), (True, 3, 10)])
def test_pine_account_switch(funded, eval_qty, qty):
    """The evaluation (the default) trades 10 MNQ as v1.5 did, or its own setting; the funded switch 10; the same max
    loss, so the stop and the lock scale. The script's defaults: at 10 MNQ the after-loss size and max loss (9 MNQ,
    $700) included; at 3 MNQ off."""
    bars = synth_bars(sessions=60, seed=11)
    inputs = {} if funded is None else {FUNDED: funded}
    cfg = NoiseConfig(qty=qty, **V21)
    if eval_qty is not None:
        inputs["Contracts in an evaluation"] = eval_qty
    if qty == 3:
        inputs[AFTER_QTY], inputs[AFTER_ML] = 0, 0.0
        cfg.after_loss_qty_div = cfg.after_loss_ml_mult = 1.0
    trades, events, _, _, _, heads = run_pine(bars, inputs, 5)
    res = run(bars, cfg)
    assert trades == trades_of(res) and events == res.events and heads == res.headsups
    assert len(trades) >= 10


@pytest.mark.slow
def test_pine_webhooks():
    bars, p = scenario(above_all_day)
    tp = (p * 1.002 + 0.25) * (1 + 1.5 * 0.001)
    assert assert_parity(bars, hook="MNQZ2026").trades[0].reason == "16:00 close"
    assert assert_parity(with_high(bars, bar(14, 8), tp + 0.25), hook="").trades[0].reason == "Target"
    stopped = with_low(bars, bar(14, 8), P0 * 1.001 ** 14 * 1.0005)
    assert assert_parity(stopped, hook="MNQZ2026", max_loss=0).trades[0].reason == "Back inside"
    bars, _ = scenario(above_then_below)
    res = assert_parity(bars, hook="MNQZ2026", exit_mode="check")
    assert [t.reason for t in res.trades[:1]] == ["reversed"]
    res = assert_parity(synth_bars(sessions=120, seed=3), hook="MNQZ2026", qty=10, max_loss=1166.67)
    assert {"Back inside", "Max loss", "Target"} <= {t.reason for t in res.trades}


@pytest.mark.slow
def test_pine_fed_day():
    bars, _ = scenario(below_all_day)
    res = assert_parity(bars, fed_dates=TEST_DAY)
    assert res.events[0] == (bar(14, CHECK_14_00), "SELL")
    assert assert_parity(bars, fed_dates=TEST_DAY, fed_no_shorts=False).events[0] == (bar(14, CHECK_10_00), "SELL")
    bars, _ = scenario(above_then_below)
    res = assert_parity(bars, fed_dates=TEST_DAY, exit_mode="check")
    assert [e for _, e in res.events[:3]] == ["BUY", "EXIT", "SELL"]


@pytest.mark.slow
def test_pine_fed_days_on_random_sessions():
    bars = synth_bars(sessions=60, seed=11)
    days = sorted({str(d.date()) for d in bars.index[bars.is_rth]})
    fed = ",".join(days[16::3])  # every third session once the history is full
    res = assert_parity(bars, fed_dates=fed)
    assert len(res.trades) > 20
    base = run(bars, NoiseConfig(fed_dates=""))
    assert len(res.trades) != len(base.trades) or trades_of(res) != trades_of(base), "the rule changed something"
    assert_parity(bars, fed_dates=fed, exit_mode="check")


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


# ----------------------------------------------------------------- stress: a harsher market, random settings

def stress_bars(seed: int, sessions: int = 70, start: str = "2026-02-16") -> pd.DataFrame:
    """5-minute bars on CME hours with what real markets do and the plain random walk doesn't: price gaps between
    bars, missing bars, half-day sessions that stop at 13:00, trend days, volatility that changes day to day, and
    a daylight-saving change inside the window (March 8 or November 1, 2026)."""
    rng = np.random.default_rng(seed)
    price = 20_000.0
    frames = []
    for day in pd.bdate_range(start, periods=sessions):
        prev = day - pd.Timedelta(days=1)
        end = "12:55" if rng.random() < 0.04 else "16:55"
        idx = pd.date_range(f"{prev.date()} 18:00", f"{day.date()} {end}", freq="5min", tz=NY)
        rth = ((idx.hour * 100 + idx.minute) >= 930) & ((idx.hour * 100 + idx.minute) < 1600)
        day_vol = float(np.exp(rng.normal(0.0, 0.5)))
        drift = float(rng.choice([0, 0, 0, 1, -1]) * rng.uniform(0.3, 1.2))
        rows, kept = [], []
        for t, is_rth in zip(idx, rth, strict=True):
            if rng.random() < 0.01:  # a missing bar
                continue
            sigma = (3.0 if is_rth else 1.2) * day_vol
            o = price
            if is_rth and rng.random() < 0.03:  # a gap between bars
                o = price + float(rng.choice([-1, 1]) * rng.integers(4, 60)) * 0.25
            path = o + np.cumsum(rng.standard_t(3, size=5) * sigma + (drift if is_rth else 0.0))
            c = round(float(path[-1]) * 4) / 4
            hi = math.ceil(max(o, float(path.max())) * 4) / 4
            lo = math.floor(min(o, float(path.min())) * 4) / 4
            rows.append((o, hi, lo, c))
            kept.append(t)
            price = c
        frames.append(pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.DatetimeIndex(kept)))
    df = pd.concat(frames)
    df["volume"] = 100.0
    return annotate(df)


def stress_case(i: int) -> dict:
    r = random.Random(1000 + i)
    return {"seed": 2000 + i, "minutes": r.choice([5, 5, 5, 10, 15]), "mode": r.choice(list(MODES)),
            "qty": r.choice([1, 3, 10]), "max_loss": r.choice([0.0, 50.0, 350.0, 1170.0]),
            "take_profit": r.choice([0.0, 1.0, 1.5]), "lookback": r.choice([5, 14]),
            "start": r.choice(["2026-02-16", "2026-09-14"]), "rth_only": r.random() < 0.25,
            "fed_every": r.choice([0, 3, 4]), "skip_every": r.choice([0, 0, 7])}


STRESS_CASES = list(range(40))


@pytest.mark.slow
@pytest.mark.parametrize("i", STRESS_CASES)
def test_pine_stress(i, hook=None):
    """The Pine script and the reference agree trade for trade, alert for alert and on every trade-log row, on a
    harsh market with random settings."""
    c = stress_case(i)
    bars = stress_bars(c["seed"], start=c["start"])
    if c["rth_only"]:
        bars = bars[bars.is_rth]
    if c["minutes"] != 5:
        bars = annotate(resample(bars[["open", "high", "low", "close", "volume"]], f"{c['minutes']}min"))
    days = sorted({str(d.date()) for d in bars.index[bars.is_rth]})
    fed = ",".join(days[c["lookback"] + 2 :: c["fed_every"]]) if c["fed_every"] else ""
    skip = ",".join(days[c["lookback"] + 3 :: c["skip_every"]]) if c["skip_every"] else ""
    exit_mode, buf = MODES[c["mode"]]
    res = assert_parity(bars, c["minutes"], lookback=c["lookback"], exit_mode=exit_mode, stop_buffer=buf,
                        qty=c["qty"], max_loss=c["max_loss"], take_profit=c["take_profit"], fed_dates=fed,
                        skip_dates=skip, hook=hook)
    assert len(res.trades) >= 10, c


@pytest.mark.slow
@pytest.mark.parametrize("i", STRESS_CASES[::2])
def test_pine_stress_webhooks(i):
    """The same harsh markets with webhook orders on: every message matches the reference's orders and exits."""
    test_pine_stress(i, hook="MNQZ2026" if i % 4 else "")


def test_stress_market_has_what_it_claims():
    bars = stress_bars(2000)
    rth = bars[bars.is_rth]
    gaps = (rth.open != rth.close.shift()).sum()
    steps = rth.index.to_series().diff().dt.total_seconds().div(60)
    assert gaps > 100 and (steps == 10).sum() > 5  # gaps between bars, and missing bars
    last = rth.groupby(rth.index.date).apply(lambda d: d.index[-1].hour * 100 + d.index[-1].minute)
    assert (last == 1255).any() and (last == 1555).any()  # half days and full days
    offsets = {t.utcoffset() for t in bars.index}
    assert len(offsets) == 2  # the daylight-saving change is inside the window


# ── research-only exits (round 138): defined rules, checked on generated bars
def _research_cfg(**kw):
    return NoiseConfig(qty=1, max_loss_per_trade=50.0, max_losers=0, skip_dates="", target_on_fill_bar=True, **kw)


def test_trail_exit_rule():
    """Once the lock has armed, the stop also sits trail_points behind the best high (long) / low (short) up to the
    previous bar; a 'Trail' exit fills at that stop (or the open past it) less a tick, and the trail never loosens."""
    bars = synth_bars(sessions=40, seed=7)
    h, lo, o = bars.high.to_numpy(), bars.low.to_numpy(), bars.open.to_numpy()
    res = run(bars, _research_cfg(trail_points=25.0), minutes=5)
    trails = [t for t in res.trades if t.reason == "Trail"]
    assert trails, "the trail ended some trades"
    for t in trails:
        best = h[t.entry_bar:t.exit_bar].max() if t.direction > 0 else lo[t.entry_bar:t.exit_bar].min()
        stop = best - t.direction * 25.0
        want = (min(o[t.exit_bar], stop) if t.direction > 0 else max(o[t.exit_bar], stop)) - t.direction * 0.25
        assert t.exit == pytest.approx(want), (t, stop)
        assert t.direction * (t.exit - t.entry) > 0  # it only works after the lock: always a win
    base = run(bars, _research_cfg(), minutes=5)
    assert len(base.trades) != len(res.trades) or [t.exit for t in base.trades] != [t.exit for t in res.trades]


def test_partial_exit_rule():
    """partial_at 1R: half closes at the fill + 1R (25 points here), the other half is a separate record of the same
    entry; the two halves' P/L add up to the position's; a trade closed in two parts counts as one loser at most."""
    bars = synth_bars(sessions=40, seed=7)
    res = run(bars, _research_cfg(partial_at=1.0), minutes=5)
    parts = [t for t in res.trades if t.reason == "Partial"]
    assert parts
    by_entry = {}
    for t in res.trades:
        by_entry.setdefault(t.entry_bar, []).append(t)
    for p in parts:
        assert p.exit == pytest.approx(p.entry + p.direction * 25.0) and p.frac == 0.5
        assert p.pnl == pytest.approx(0.5 * (25.0 * 2.0 - 2 * 0.62))
        rest = [t for t in by_entry[p.entry_bar] if t is not p]
        assert len(rest) == 1 and rest[0].frac == 0.5 and rest[0].exit_bar >= p.exit_bar
    for t in res.trades:
        if t.reason != "Partial" and t.entry_bar not in {p.entry_bar for p in parts}:
            assert t.frac == 1.0


@pytest.mark.slow
def test_pine_after_loss_size_and_stop():
    """v2.1: the trade after a losing trade uses the after-loss contracts and max loss (a wider stop); a winner resets
    it. The script and the reference agree trade for trade, and the size follows the previous trade's result."""
    bars = synth_bars(sessions=60, seed=11)
    res = assert_parity(bars, qty=10, max_loss=500.0, take_profit=2.0, lock_at=0.75, after_loss=(9, 700.0))
    run_ = 0  # losers in a row before each trade, by the rule
    for x in res.trades:
        assert x.qty == (9 if run_ else 10)
        if x.pnl < 0 and x.reason != "Session ended":
            run_ += 1
        elif x.pnl >= 0:
            run_ = 0
    assert {x.qty for x in res.trades} == {9, 10}


@pytest.mark.slow
def test_pine_no_entries_from_the_last_check():
    """v2.2: with "Last check for new entries" at 15:00, the 15:30 check opens nothing (nor alerts a heads-up for it);
    the script and the reference agree trade for trade, and the setting changes trades on these bars."""
    bars = synth_bars(sessions=60, seed=11)
    res = assert_parity(bars, qty=10, max_loss=500.0, last_entry=900)
    assert not any(t.entry_time.tz_convert(NY).strftime("%H:%M") == "15:30" for t in res.trades)
    every = run(bars, NoiseConfig(qty=10, max_loss_per_trade=500.0))
    assert any(t.entry_time.tz_convert(NY).strftime("%H:%M") == "15:30" for t in every.trades)
