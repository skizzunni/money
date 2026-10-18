"""Round one hundred and sixteen: the source paper's VWAP trailing stop on the bot as it trades now.

    python research/vwap_stop.py nsx1m_scaled.pkl nq1m_scaled.pkl

Zarattini, Aziz and Barbon (2024) trail the noise-area trade's stop at the tighter of the noise boundary and the
day's VWAP. It was tested once here (the second round, S2b): 3 3/4 years, the bot's first version (no max loss, lock
or take-profit), a time-weighted average for want of volume. The NQ futures data has volume. mnqbot.noise's
vwap_stop (research only): the bot's stop is also never looser than the day's VWAP, as of the last half-hour check
("checks", when the noise lines move too) or the last bar ("bars"); time-weighted on the index data (no volume).
The strategy now otherwise (bot 4 MNQ, $200, the evaluation's 3 losers / lock 1.0 +2.5, funded 2 / 0.5 +6.25; the
breakout in its gaps), on the user's intraday-trail evaluation (research/combo_more.evaluate).
Bar, fixed before running: adopted if, against now, it makes more $ a week, passes at least as many evaluations, pays
at least as much per evaluation, in all three periods (2011-18, 2019-25, NQ 2015-24); the 13 months from July 2025 are
reported too. If both pass, the one paying most in sum.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

MODES = ("", "checks", "bars")


def bot_trades(bars, losers, lock_at, lock_plus, vwap):
    """trap_reversal.bot_trades with the VWAP stop."""
    cfg = NoiseConfig(qty=1, max_loss_per_trade=T.CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus, vwap_stop=vwap)
    return run(bars, cfg, minutes=1).trades


def job(args):
    path, periods, mode = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev, pa = bot_trades(bars, 3, 1.0, 2.5, mode), bot_trades(bars, 2, 0.5, 6.25, mode)
    return M.evaluate(bars, sess, ev, pa, cands, False, periods, mode or "now")


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
             ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, m) for path, per in ((nsx, idx_p), (nq, nq_p)) for m in MODES]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 230)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    wins = []
    for name in MODES[1:]:
        ok = all(key.loc[(name, p)]["$/week"] > key.loc[("now", p)]["$/week"] and
                 key.loc[(name, p)]["eval pass %"] >= key.loc[("now", p)]["eval pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        print(f"VWAP {name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in ("2011-2018", "2019-2025",
                                                                               "NQ 2015-2024")), name))
    print(f"ADOPT VWAP {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
