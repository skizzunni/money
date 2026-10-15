from collections import defaultdict

import pandas as pd
import pytest
from conftest import bars_from_rows, synth_bars

from mnqbot.config import BotConfig, PropRules
from mnqbot.data import annotate, load_csv
from mnqbot.engine import Backtester, backtest
from mnqbot.report import format_report, prop_monte_carlo, run_eval, summarize
from mnqbot.strategy import _hhmm


def loose_cfg():
    """Looser filters so random-walk data produces enough trades to test the rails."""
    cfg = BotConfig()
    s = cfg.strategy
    s.displacement_atr = 0.3
    s.min_fvg_ticks = 1
    s.max_bars_after_sweep = 30
    s.window_end = "1500"
    s.min_stop_points, s.max_stop_points = 4, 100
    return cfg


@pytest.fixture(scope="module")
def stress_bars():
    return synth_bars(sessions=250, seed=3)


@pytest.fixture(scope="module")
def result(stress_bars):
    return backtest(stress_bars, loose_cfg())


def test_random_data_produces_trades(result):
    assert len(result.trades) >= 40, "test data too quiet to exercise the engine"


# ------------------------------------------------------------------ sizing
@pytest.mark.parametrize(
    "risk_pts, day_pnl, buffer, expected",
    [
        (17, 0, 1500, 4),  # $150 / $35.74
        (17, -200, 1500, 2),  # only $100 left before the daily loss limit
        (17, 0, 200, 1),  # 25% of a $200 drawdown buffer = $50
        (60, 0, 1500, 1),
        (100, 0, 1500, 0),  # one contract would risk more than $150
        (2, 0, 1e9, 15),  # capped by max_contracts
        (17, -300, 1500, 0),  # daily limit already hit
    ],
)
def test_position_sizing(risk_pts, day_pnl, buffer, expected):
    bars = bars_from_rows("2026-10-14 09:30", [(1, 1, 1, 1)])
    assert Backtester(bars).size(risk_pts, day_pnl, buffer) == expected


# ------------------------------------------------------------ risk rails
def test_every_loss_is_capped_at_planned_risk(result):
    for t in result.trades:
        assert t.pnl >= -t.risk_dollars - 1e-6
        assert t.risk_dollars <= result.config.risk.risk_per_trade + 1e-6


def test_daily_rails_respected(result):
    risk = result.config.risk
    by_day = defaultdict(list)
    for t in result.trades:
        by_day[t.trade_date].append(t)
    for trades in by_day.values():
        assert len(trades) <= risk.max_trades_per_day
        realized = 0.0
        for t in sorted(trades, key=lambda t: t.entry_time):
            assert realized > -risk.daily_max_loss
            assert realized < risk.daily_profit_lock
            realized += t.pnl


def test_setups_only_in_window_and_flat_by_day_end(result):
    s = result.config.strategy
    for t in result.trades:
        hhmm = t.setup_time.hour * 100 + t.setup_time.minute
        assert _hhmm(s.window_start) <= hhmm < _hhmm(s.window_end)
        assert t.exit_time >= t.entry_time
        exit_day = (t.exit_time + pd.Timedelta(hours=6)).date()
        assert exit_day == t.trade_date
        assert t.exit_time.hour * 100 + t.exit_time.minute <= _hhmm(s.flatten_at)


def test_no_lookahead(stress_bars):
    """Cutting the data off early must not change any trade that finished before the cut."""
    cfg = loose_cfg()
    full = backtest(stress_bars, cfg).trades
    for frac in (0.3, 0.55, 0.8):
        cut = stress_bars.index[int(len(stress_bars) * frac)]
        part = backtest(stress_bars[stress_bars.index < cut], cfg).trades
        done = [t for t in part if t.reason != "end_of_data"]
        key = lambda t: (t.entry_time, t.entry, t.qty, t.exit_time, t.exit, t.reason)  # noqa: E731
        assert [key(t) for t in done] == [key(t) for t in full[: len(done)]]


def test_daily_frame_matches_trades(result):
    total = sum(t.pnl for t in result.trades)
    assert result.daily.pnl.sum() == pytest.approx(total)
    assert result.equity.iloc[-1] == pytest.approx(total)


def test_attempts_are_consistent(result):
    prop = result.config.prop
    for a in result.attempts:
        if a.outcome == "passed":
            assert a.profit >= prop.profit_target
            assert a.trading_days >= prop.min_trading_days
            assert a.best_day < prop.consistency_max_day_frac * a.profit
    assert [a.number for a in result.attempts] == list(range(1, len(result.attempts) + 1))


def test_report_renders(result):
    text = format_report(summarize(result, mc_sims=200))
    assert "Benchmark" in text and "Monte Carlo" in text


def two_setup_day():
    """A short off the overnight high that stops out, then a long off the overnight low."""
    from test_strategy import overnight

    rows = overnight() + [
        (20000, 20004, 19998, 20002),  # 09:30
        (20002, 20014, 20001, 20006),  # 09:35 sweep ONH
        (20006, 20007, 19992, 19991),  # 09:40 displacement down
        (19991, 19995, 19991, 19993),  # 09:45 bearish FVG -> short 19998, stop 20015
        (19993, 19999, 19992, 19996),  # 09:50 filled
        (19996, 20016, 19995, 20012),  # 09:55 stopped out
        (20012, 20013, 19998, 20000),  # 10:00
        (20000, 20001, 19986, 19994),  # 10:05 sweep ONL 19990, close back above
        (19994, 20015, 19993, 20014),  # 10:10 displacement up
        (20014, 20018, 20005, 20016),  # 10:15 bullish FVG 20001..20005 -> long 20003, stop 19985
        (20016, 20017, 20002, 20004),  # 10:20 fills
    ] + [(20004, 20006, 20002, 20004)] * 6
    cfg = BotConfig()
    cfg.strategy.use_swings = False
    cfg.strategy.use_orb = False
    return bars_from_rows("2026-10-14 08:00", rows), cfg


def test_second_trade_shrinks_to_fit_daily_loss_limit():
    bars, cfg = two_setup_day()
    cfg.risk.daily_max_loss = 250
    t1, t2 = backtest(bars, cfg).trades
    assert (t1.direction, t1.reason, t1.qty) == (-1, "stop", 4)
    # $250 - $142.96 already lost = $107.04 of room; 18 pts risk = $37.74 per contract -> 2
    assert (t2.direction, t2.entry, t2.stop, t2.qty) == (1, 20003, 19985, 2)
    assert t1.pnl - t2.risk_dollars > -250


def test_max_trades_per_day_blocks_second_setup():
    bars, cfg = two_setup_day()
    cfg.risk.max_trades_per_day = 1
    res = backtest(bars, cfg)
    assert len(res.trades) == 1
    assert res.skipped == {"max_trades": 1}


def test_no_trade_dates_and_blackouts():
    bars, cfg = two_setup_day()
    cfg.risk.no_trade_dates = ["2026-10-14"]
    res = backtest(bars, cfg)
    assert res.trades == [] and res.skipped == {"no_trade_day": 2}

    bars, cfg = two_setup_day()
    cfg.risk.blackout_windows = ["1010-1030"]
    res = backtest(bars, cfg)
    assert len(res.trades) == 1 and res.skipped == {"news_blackout": 1}


# ------------------------------------------------------------ eval rules
PROP = PropRules()


def test_eval_passes_after_min_days():
    assert run_eval([(400.0, 0.0, True)] * 10, PROP) == ("passed", 5)  # $1,600 by day 4, 5 days needed


def test_eval_fails_on_intraday_breach():
    assert run_eval([(-400.0, -400.0, True)] * 10, PROP) == ("failed", 4)


def test_eval_consistency_rule_blocks_one_big_day():
    days = [(1600.0, 0.0, True)] + [(50.0, 0.0, True)] * 30
    outcome, sessions = run_eval(days, PROP)
    # best day 1600 must be < 50% of total -> total must exceed 3200, i.e. 33 more $50 days
    assert outcome == "timeout"


def test_eval_trailing_drawdown_locks_at_start_balance():
    # Peak +$2,000 would put the line at +$500, but it stops trailing at the start balance (0).
    days = [(1000.0, 0.0, False), (1000.0, 0.0, False), (-1900.0, -1900.0, False), (0.0, -150.0, False)]
    assert run_eval(days, PROP) == ("failed", 4)
    unlocked = PropRules(drawdown_lock=1e9)
    assert run_eval(days, unlocked) == ("failed", 3)


def test_eval_stalled_account_counts_as_failed():
    days = [(-1440.0, -1440.0, True)] + [(0.0, 0.0, False)] * 5
    assert run_eval(days, PROP)[0] == "timeout"
    assert run_eval(days, PROP, min_buffer=71.0) == ("failed", 1)


def test_monte_carlo_bounds():
    daily = pd.DataFrame({"pnl": [400.0], "worst": [0.0], "trades": [1]})
    mc = prop_monte_carlo(daily, PROP, sims=50)
    assert mc["pass_rate"] == 1.0 and mc["median_sessions_to_pass"] == 5


# ------------------------------------------------------------------ data
def test_load_tradingview_unix_csv(tmp_path):
    bars = synth_bars(sessions=1)
    raw = pd.DataFrame(
        {
            "time": (bars.index.tz_convert("UTC").as_unit("s").asi8 // 1).astype("int64"),
            "open": bars.open.values,
            "high": bars.high.values,
            "low": bars.low.values,
            "close": bars.close.values,
            "Volume": 1,
        }
    )
    f = tmp_path / "CME_MINI_MNQ1!, 5.csv"
    raw.to_csv(f, index=False)
    loaded = load_csv(f)
    assert len(loaded) == len(bars)
    assert loaded.index[0] == bars.index[0]
    assert str(loaded.index.tz) == "America/New_York"


def test_load_iso_offset_and_split_date_time(tmp_path):
    f1 = tmp_path / "iso.csv"
    f1.write_text("time,open,high,low,close\n2026-03-06T09:30:00-05:00,1,2,0.5,1.5\n2026-03-09T09:30:00-04:00,1,2,0.5,1.5\n")
    a = annotate(load_csv(f1))
    assert list(a.hhmm) == [930, 930]  # across the DST change

    f2 = tmp_path / "nt.csv"
    f2.write_text("Date,Time,Open,High,Low,Close,Volume\n2026-10-14,09:30:00,1,2,0.5,1.5,10\n")
    b = annotate(load_csv(f2))
    assert b.hhmm.iloc[0] == 930 and bool(b.is_rth.iloc[0])


def test_trade_date_rolls_at_6pm():
    bars = bars_from_rows("2026-10-12 17:55", [(1, 1, 1, 1)] * 2)  # Monday 17:55 and 18:00
    assert str(bars.trade_date.iloc[0]) == "2026-10-12"
    assert str(bars.trade_date.iloc[1]) == "2026-10-13"


def test_funnel_adds_up(result):
    f = result.funnel
    assert f["sweeps"] + f["breakouts"] >= f["setups"] > 0
    assert f["setups"] == f["stop_too_tight"] + f["stop_too_wide"] + f["blocked"] + f["too_big_to_size"] + f["signals"]
    assert f["blocked"] + f["too_big_to_size"] == sum(result.skipped.values())
    assert f["signals"] == len(result.orders)
    assert f["filled"] == len(result.trades)
    assert f["signals"] - f["filled"] - f["never_filled"] in (0, 1)  # one order may still be working at the end


def test_funnel_counts_rejected_stop_sizes():
    from test_strategy import short_day

    bars = short_day()  # one setup with a 17-point stop
    cfg = BotConfig()
    cfg.strategy.use_swings = False
    cfg.strategy.use_orb = False
    cfg.strategy.max_stop_points = 15.0
    f = backtest(bars, cfg).funnel
    assert (f["sweeps"], f["setups"], f["stop_too_wide"], f["signals"]) == (1, 1, 1, 0)
    assert f["stop_points_avg"] == f["stop_points_max"] == 17.0
