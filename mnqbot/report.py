"""Turn a BacktestResult into numbers a skeptic would ask for."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import PropRules
from .engine import BacktestResult, min_tradable_buffer


def _max_drawdown(series: np.ndarray) -> float:
    if len(series) == 0:
        return 0.0
    peak = np.maximum.accumulate(series)
    return float(np.max(peak - series))


def _max_streak(flags: list[bool]) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def summarize(res: BacktestResult, mc_sims: int = 5000, mc_sessions: int = 60, seed: int = 7) -> dict:
    cfg, bars = res.config, res.bars
    pv = cfg.instrument.point_value
    tf = res.trades_frame()
    daily = res.daily
    out: dict = {
        "period": {
            "first_bar": str(bars.index[0]),
            "last_bar": str(bars.index[-1]),
            "sessions": int(len(daily)),
            "bars": int(len(bars)),
        }
    }

    n = len(tf)
    if n:
        wins, losses = tf[tf.pnl > 0], tf[tf.pnl <= 0]
        gross_win, gross_loss = wins.pnl.sum(), -losses.pnl.sum()
        out["trades"] = {
            "count": n,
            "win_rate": len(wins) / n,
            "avg_win": float(wins.pnl.mean()) if len(wins) else 0.0,
            "avg_loss": float(losses.pnl.mean()) if len(losses) else 0.0,
            "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else math.inf,
            "expectancy_per_trade": float(tf.pnl.mean()),
            "avg_r": float(tf.r.mean()),
            "net_pnl": float(tf.pnl.sum()),
            "costs_paid": float(tf.costs.sum()),
            "max_losing_streak": _max_streak(list(tf.pnl <= 0)),
            "avg_contracts": float(tf.qty.mean()),
            "exit_reasons": tf.reason.value_counts().to_dict(),
            "by_side": _group(tf, "side"),
            "by_level": _group(tf, "level"),
        }
    else:
        out["trades"] = {"count": 0, "net_pnl": 0.0}

    eq = res.equity.to_numpy()
    out["risk"] = {
        "max_drawdown": _max_drawdown(eq),
        "best_day": float(daily.pnl.max()),
        "worst_day": float(daily.pnl.min()),
        "worst_intraday_dip": float(daily.worst.min()),
        "green_days": int((daily.pnl > 0).sum()),
        "red_days": int((daily.pnl < 0).sum()),
        "flat_days": int((daily.pnl == 0).sum()),
        "loss_limit_days": int(daily.hit_loss_limit.sum()),
        "profit_lock_days": int(daily.hit_profit_lock.sum()),
        "daily_sharpe": _sharpe(daily.pnl.to_numpy()),
    }

    # Benchmark: hold one contract the whole time. Not allowed at most prop firms
    # (you must be flat daily), but it is the honest "did I beat the market" yardstick.
    first, last = float(bars.open.iloc[0]), float(bars.close.iloc[-1])
    hold_curve = (bars.close.to_numpy() - first) * pv
    out["benchmark_buy_hold_1_contract"] = {
        "net_pnl": (last - first) * pv,
        "max_drawdown": _max_drawdown(np.concatenate(([0.0], hold_curve))),
        "index_change_pct": (last / first - 1) * 100,
    }

    att = res.attempts
    passed = [a for a in att if a.outcome == "passed"]
    failed = [a for a in att if a.outcome == "failed"]
    out["prop_attempts_sequential"] = {
        "passed": len(passed),
        "failed": len(failed),
        "failed_stalled": len([a for a in failed if a.note == "stalled"]),
        "still_open": len([a for a in att if a.outcome == "open"]),
        "median_sessions_to_pass": float(np.median([a.sessions for a in passed])) if passed else None,
    }
    out["prop_monte_carlo"] = prop_monte_carlo(
        daily, cfg.prop, mc_sims, mc_sessions, seed, min_buffer=min_tradable_buffer(cfg)
    )
    out["skipped_setups"] = dict(sorted(res.skipped.items()))
    return out


def _group(tf: pd.DataFrame, col: str) -> dict:
    g = tf.groupby(col).agg(count=("pnl", "size"), net=("pnl", "sum"), win_rate=("pnl", lambda s: (s > 0).mean()))
    return {k: {kk: float(vv) for kk, vv in v.items()} for k, v in g.to_dict("index").items()}


def _sharpe(daily_pnl: np.ndarray) -> float | None:
    if len(daily_pnl) < 2 or np.std(daily_pnl, ddof=1) == 0:
        return None
    return float(np.mean(daily_pnl) / np.std(daily_pnl, ddof=1) * math.sqrt(252))


def run_eval(days: list[tuple[float, float, bool]], prop: PropRules, min_buffer: float = 0.0) -> tuple[str, int]:
    """Walk (day_pnl, worst_intraday_dip, traded) tuples through the eval rules.

    Returns ("passed" | "failed" | "timeout", sessions used). Ending a day
    within ``min_buffer`` of the drawdown line counts as failed (stalled).
    """
    lock_rel = prop.lock_level - prop.start_balance
    frac = prop.consistency_max_day_frac
    rel = peak = 0.0
    tdays = 0
    best = -math.inf
    for s, (pnl, worst, traded) in enumerate(days, start=1):
        if rel + worst <= min(peak - prop.max_drawdown, lock_rel):
            return "failed", s
        rel += pnl
        if traded:
            tdays += 1
            best = max(best, pnl)
        peak = max(peak, rel)
        if rel >= prop.profit_target and tdays >= prop.min_trading_days and (frac <= 0 or best < frac * rel):
            return "passed", s
        if rel - min(peak - prop.max_drawdown, lock_rel) < min_buffer:
            return "failed", s
    return "timeout", len(days)


def prop_monte_carlo(
    daily: pd.DataFrame,
    prop: PropRules,
    sims: int = 5000,
    max_sessions: int = 60,
    seed: int = 7,
    min_buffer: float = 0.0,
) -> dict:
    """Replay random orderings of the backtest's own days through the eval rules.

    Days are sampled with replacement, so streaks (bad weeks clustering) are
    understated. Treat the pass rate as an upper-ish estimate.
    """
    if sims <= 0 or daily.empty:
        return {}
    rng = np.random.default_rng(seed)
    days = list(zip(daily.pnl.astype(float), daily.worst.astype(float), daily.trades.astype(int) > 0, strict=True))
    outcomes = {"passed": 0, "failed": 0, "timeout": 0}
    days_to_pass = []

    for _ in range(sims):
        picks = rng.integers(0, len(days), max_sessions)
        result, sessions = run_eval([days[k] for k in picks], prop, min_buffer)
        outcomes[result] += 1
        if result == "passed":
            days_to_pass.append(sessions)

    return {
        "sims": sims,
        "max_sessions": max_sessions,
        "pass_rate": outcomes["passed"] / sims,
        "fail_rate": outcomes["failed"] / sims,
        "timeout_rate": outcomes["timeout"] / sims,
        "median_sessions_to_pass": float(np.median(days_to_pass)) if days_to_pass else None,
    }


def _money(x: float | None) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{'-' if x < 0 else ''}${abs(x):,.2f}"


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def format_report(s: dict) -> str:
    p, t, r = s["period"], s["trades"], s["risk"]
    bh, seq, mc = s["benchmark_buy_hold_1_contract"], s["prop_attempts_sequential"], s["prop_monte_carlo"]
    lines = [
        "=" * 64,
        f"MNQ liquidity-sweep bot backtest  {p['first_bar'][:10]} -> {p['last_bar'][:10]}",
        f"{p['sessions']} sessions, {p['bars']} bars",
        "=" * 64,
    ]
    if t["count"]:
        lines += [
            f"Trades            {t['count']}  (avg {t['avg_contracts']:.1f} contracts)",
            f"Win rate          {_pct(t['win_rate'])}",
            f"Avg win / loss    {_money(t['avg_win'])} / {_money(t['avg_loss'])}",
            f"Profit factor     {t['profit_factor']:.2f}",
            f"Expectancy        {_money(t['expectancy_per_trade'])} per trade ({t['avg_r']:+.2f}R)",
            f"Net P/L           {_money(t['net_pnl'])}  (after {_money(t['costs_paid'])} costs)",
            f"Max losing streak {t['max_losing_streak']}",
            f"Exits             {t['exit_reasons']}",
        ]
    else:
        lines.append("No trades. Loosen settings or use more data.")
    lines += [
        "-" * 64,
        f"Max drawdown      {_money(r['max_drawdown'])}",
        f"Best / worst day  {_money(r['best_day'])} / {_money(r['worst_day'])}",
        f"Worst intraday    {_money(r['worst_intraday_dip'])}",
        f"Green/red/flat    {r['green_days']} / {r['red_days']} / {r['flat_days']}",
        f"Loss-limit days   {r['loss_limit_days']}    profit-lock days {r['profit_lock_days']}",
        "-" * 64,
        "Benchmark: hold 1 MNQ the whole period (not allowed at most prop firms)",
        f"  P/L {_money(bh['net_pnl'])}, max drawdown {_money(bh['max_drawdown'])},"
        f" index {bh['index_change_pct']:+.2f}%",
        f"  Bot beat buy-and-hold: {'YES' if t['net_pnl'] > bh['net_pnl'] else 'NO'}",
        "-" * 64,
        "Prop evaluations, back to back on this data:",
        f"  passed {seq['passed']}, failed {seq['failed']} ({seq['failed_stalled']} stalled near the line),"
        f" still open {seq['still_open']}"
        + (f", median {seq['median_sessions_to_pass']:.0f} sessions to pass" if seq["median_sessions_to_pass"] else ""),
    ]
    if mc:
        lines += [
            f"Monte Carlo ({mc['sims']} shuffled runs, {mc['max_sessions']} sessions max):",
            f"  pass {_pct(mc['pass_rate'])}, fail {_pct(mc['fail_rate'])}, ran out of time {_pct(mc['timeout_rate'])}",
        ]
    if s["skipped_setups"]:
        lines.append(f"Setups skipped by risk rails: {s['skipped_setups']}")
    lines.append("=" * 64)
    lines.append("Past results on historical data do not predict future results.")
    return "\n".join(lines)
