from conftest import bars_from_rows

from mnqbot.config import BotConfig
from mnqbot.engine import backtest
from mnqbot.strategy import scan

FLAT = (20000, 20003, 19997, 20000)


def overnight():
    rows = [FLAT] * 18  # 08:00 .. 09:25
    rows[5] = (20001, 20010, 20000, 20005)  # overnight high 20010
    rows[10] = (20001, 20002, 19990, 19995)  # overnight low 19990
    return rows


def short_day(sweep_close=20006, after=None):
    rows = overnight() + [
        (20000, 20004, 19998, 20002),  # 09:30
        (20002, 20014, 20001, sweep_close),  # 09:35 runs ONH 20010, closes back below
        (20006, 20007, 19992, 19991),  # 09:40 displacement candle
        (19991, 19995, 19991, 19993),  # 09:45 leaves FVG 19995..20001 -> setup
    ]
    rows += after or [
        (19993, 19999, 19992, 19996),  # 09:50 retrace fills limit at 19998
        (19996, 19997, 19978, 19980),  # 09:55 reaches +1R -> stop to breakeven
        (19980, 19982, 19960, 19962),  # 10:00 target 19964
    ]
    rows += [(19962, 19964, 19960, 19962)] * 5
    return bars_from_rows("2026-10-14 08:00", rows)


def cfg_no_swings():
    cfg = BotConfig()
    cfg.strategy.use_swings = False
    return cfg


def test_sweep_and_fvg_produce_short_setup():
    bars = short_day()
    setups = scan(bars, cfg_no_swings().strategy, cfg_no_swings().instrument)
    assert len(setups) == 1
    s = setups[0]
    assert s.direction == -1
    assert s.level_name == "ONH" and s.level_price == 20010
    assert bars.index[s.bar].strftime("%H:%M") == "09:45"
    assert (s.fvg_low, s.fvg_high) == (19995, 20001)
    assert s.entry == 19998  # gap midpoint
    assert s.stop == 20015  # sweep high 20014 + 4 ticks
    assert s.target == 19964  # 2R
    assert s.risk_points == 17


def test_close_above_level_is_a_breakout_not_a_sweep():
    bars = short_day(sweep_close=20012)
    assert scan(bars, cfg_no_swings().strategy, cfg_no_swings().instrument) == []


def test_winning_trade_is_sized_and_costed():
    res = backtest(short_day(), cfg_no_swings())
    assert len(res.trades) == 1
    t = res.trades[0]
    # per contract risk = 17 pts * $2 + $1.24 commission + 1 tick slippage = $35.74 -> 4 contracts for $150
    assert t.qty == 4
    assert t.entry_time.strftime("%H:%M") == "09:50"
    assert t.reason == "target" and t.exit == 19964
    assert round(t.pnl, 2) == round(34 * 4 * 2 - 4 * 1.24, 2)


def test_bar_touching_stop_and_target_counts_as_a_loss():
    after = [
        (19993, 19999, 19992, 19996),  # fill
        (19996, 19997, 19985, 19990),  # not far enough for breakeven
        (19990, 20016, 19960, 19970),  # hits stop 20015 and target 19964 in one bar
    ]
    res = backtest(short_day(after=after), cfg_no_swings())
    t = res.trades[0]
    assert t.reason == "stop"
    assert t.exit == 20015.25  # stop + 1 tick slippage
    assert round(t.r, 6) == -1.0  # lost exactly the planned risk


def test_no_same_bar_target_on_fill_bar():
    after = [(19993, 19999, 19960, 19962)]  # fills at 19998 then trades to target in the same bar
    res = backtest(short_day(after=after), cfg_no_swings())
    t = res.trades[0]
    assert t.reason == "target"
    assert t.exit_time.strftime("%H:%M") == "09:55"  # credited on the next bar, not the fill bar


def test_unfilled_order_expires():
    after = [(19993, 19996, 19990, 19994)] * 8  # never trades up to 19998.25
    res = backtest(short_day(after=after), cfg_no_swings())
    assert res.trades == []
