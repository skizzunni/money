"""Opening range breakout with a retest entry, on hand-built bars."""
from conftest import bars_from_rows

from mnqbot.config import BotConfig
from mnqbot.engine import backtest
from mnqbot.strategy import _plus_minutes, scan

PRE = [(20000, 20003, 19997, 20000)] * 6  # 09:00 .. 09:25
OR_BAR = (20000, 20010, 19990, 20005)  # 09:30: range 19990 .. 20010


def long_day(after=None):
    rows = PRE + [
        OR_BAR,
        (20005, 20016, 20004, 20014),  # 09:35 closes above 20010 -> buy limit 20010, stop 20000, target 20030
    ]
    rows += after or [
        (20014, 20015, 19999.75 + 10, 20012),  # 09:40 retest to 20009.75 fills 20010
        (20012, 20022, 20011, 20020),  # 09:45 reaches +1R (20020) -> stop to breakeven
        (20020, 20031, 20019, 20029),  # 09:50 target 20030
    ]
    rows += [(20029, 20030, 20028, 20029)] * 5
    return bars_from_rows("2026-10-14 09:00", rows)


def short_day():
    rows = PRE + [
        OR_BAR,
        (20005, 20006, 19984, 19986),  # 09:35 closes below 19990 -> sell limit 19990, stop 20000, target 19970
        (19986, 19990.25, 19985, 19988),  # 09:40 retest fills 19990
        (19988, 20001, 19987, 19999),  # 09:45 stop 20000
    ] + [(19999, 20000, 19998, 19999)] * 5
    return bars_from_rows("2026-10-14 09:00", rows)


def orb_only(**kw):
    cfg = BotConfig()
    cfg.strategy.use_sweep = False
    cfg.strategy.use_swings = False
    for k, v in kw.items():
        setattr(cfg.strategy, k, v)
    return cfg


def test_plus_minutes():
    assert [_plus_minutes(930, m) for m in (5, 15, 30, 45, 90)] == [935, 945, 1000, 1015, 1100]


def test_long_breakout_retest_to_target():
    bars = long_day()
    cfg = orb_only()
    (s,) = scan(bars, cfg.strategy, cfg.instrument)
    assert (s.direction, s.level_name, s.entry, s.stop, s.target) == (1, "ORH", 20010, 20000, 20030)
    assert bars.index[s.bar].strftime("%H:%M") == "09:35"
    (t,) = backtest(bars, cfg).trades
    # 10-point stop: $20 + $1.24 fees + $0.50 slippage = $21.74 per contract -> 6 contracts for $150
    assert t.qty == 6 and t.entry_time.strftime("%H:%M") == "09:40"
    assert t.reason == "target" and t.exit == 20030
    assert round(t.pnl, 2) == round(20 * 6 * 2 - 6 * 1.24, 2)


def test_short_breakout_retest_to_stop():
    bars = short_day()
    (t,) = backtest(bars, orb_only()).trades
    assert (t.direction, t.entry, t.stop, t.target) == (-1, 19990, 20000, 19970)
    assert t.reason == "stop" and t.exit == 20000.25
    assert round(t.r, 6) == -1.0


def test_both_setups_is_the_default_and_finds_the_breakout():
    cfg = BotConfig()
    cfg.strategy.use_swings = False
    assert cfg.strategy.use_sweep and cfg.strategy.use_orb
    assert [s.level_name for s in scan(long_day(), cfg.strategy, cfg.instrument)] == ["ORH"]


def test_one_breakout_per_day():
    after = [(20014, 20016, 20011, 20012)] * 6 + [  # never retests 20009.75, order expires
        (20012, 20012, 19980, 19982),  # later closes below the range: no second setup
    ] + [(19982, 19983, 19981, 19982)] * 3
    bars = long_day(after)
    res = backtest(bars, orb_only())
    assert len(res.orders) == 1 and res.trades == []
    assert res.funnel["breakouts"] == 1 and res.funnel["never_filled"] == 1


def test_orb_off():
    cfg = orb_only(use_orb=False)
    assert scan(long_day(), cfg.strategy, cfg.instrument) == []


def test_longer_opening_range_waits_for_it_to_finish():
    # 15-minute range = 09:30, 09:35, 09:40 bars; the 09:35 close above 20010 is inside the range period
    cfg = orb_only(or_minutes=15)
    (s,) = scan(long_day(), cfg.strategy, cfg.instrument)
    assert bars_time(long_day(), s.bar) >= "09:45"
    assert s.level_name in ("ORH", "ORL")


def bars_time(bars, i):
    return bars.index[i].strftime("%H:%M")


def test_stop_at_far_side_of_range():
    cfg = orb_only(or_stop_frac=1.0)
    (s,) = scan(long_day(), cfg.strategy, cfg.instrument)
    assert (s.entry, s.stop, s.target) == (20010, 19990, 20050)


def test_half_tick_midpoint_rounds_up():
    rows = PRE + [(20000, 20010.25, 19990, 20005), (20005, 20016, 20004, 20014)] + [(20014, 20015, 20012, 20013)] * 3
    cfg = orb_only()
    (s,) = scan(bars_from_rows("2026-10-14 09:00", rows), cfg.strategy, cfg.instrument)
    # range 20.25, half 10.125 -> stop 20000.125 rounds up to 20000.25, risk 10.0
    assert (s.entry, s.stop) == (20010.25, 20000.25)


def test_breakout_must_be_in_entry_window():
    cfg = orb_only(window_start="0945")
    (s,) = scan(long_day(), cfg.strategy, cfg.instrument)  # 09:35 close above is ignored
    assert bars_time(long_day(), s.bar) >= "09:45"
