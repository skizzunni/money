"""G281 (docs/NINJATRADER_V38.md): one bracket a day on the bot's first entry, for TPT's 50K Test in two weeks.

Each session, the bot's first entry (U53's signal settings, k317, no gap trade; NQ 2015-25, 5-minute bars) opens one
MNQ bracket: the stop S points away, the target R x S; walked on 1-minute bars (a minute reaching both counts the
stop; open at 16:00 closes at the 15:59 close). Size: the contracts that make about TARGET dollars at the target, cut
so a full stop stays above the floor less $100. Costs $1.24 commission and 1 tick each way per MNQ. No other trades.
TPT's Test over 10 sessions from every Monday: +$3,000 with the best day under half the profit and 3+ trading days
passes; the $2,000 trailing floor from the highest end-of-day balance (stopping at the start), touched by a loss,
fails. Grid: S 25 / 50 points, R 1.0 / 1.25 / 1.5, TARGET $800 / $1,000 / $1,200 a day. Development: Mondays
2015-2019; unseen: Mondays 2020-2025.

    python research/g281_daily_bracket.py <data dir> <MNQ 09-26> <MNQ 12-26>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
K317 = {"lookback": 18, "entry_k": 0.7, "range_pos_min": 0.7, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2,
        "skip_checks": "", "max_losers": 3, "time_stop": 30, "trend_n": 0, "big_day_k": 0.0, "stop_buffer": 0.24,
        "lock_plus": 2.5, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go": False}
S_FROZEN = 1  # G281c: fewer than one contract's full stop left above the floor less $100
PV, COST = 2.0, 0.62 * 2 + 0.25 * 2 * 2.0  # $ a point; commission and a tick each way per MNQ


def outcomes(first, groups, s_pts, ratio):
    """Per session: points won (+R*S), lost (-S) or closed at 16:00, for the bot's first entry."""
    out = {}
    for day, r in first.iterrows():
        g = groups.get(day)
        if g is None:
            continue
        g = g[g.index >= r.entry_time]
        op, hi, lo, cl = g.open.to_numpy(), g.high.to_numpy(), g.low.to_numpy(), g.close.to_numpy()
        sgn = r.direction
        tp, sl = r.entry + sgn * ratio * s_pts, r.entry - sgn * s_pts
        hit_s = (lo <= sl) if sgn > 0 else (hi >= sl)
        hit_t = (hi >= tp) if sgn > 0 else (lo <= tp)
        i_s = int(np.argmax(hit_s)) if hit_s.any() else 10 ** 9
        i_t = int(np.argmax(hit_t)) if hit_t.any() else 10 ** 9
        if i_s == i_t == 10 ** 9:
            out[day] = sgn * (cl[-1] - r.entry)
        else:
            if i_t < i_s:
                out[day] = ratio * s_pts
            else:  # G281b: the stop fills at the stop or at the minute's open past it, less a tick more
                fill = min(op[i_s], sl) if sgn > 0 else max(op[i_s], sl)
                out[day] = sgn * (fill - r.entry) - 0.25
    return out


def test(days, pts, s_pts, ratio, target):
    eq, peak, best, traded = 0.0, 0.0, 0.0, 0
    for d in days:
        floor = min(peak - 2000.0, 0.0)
        p = pts.get(d)
        day_pnl = 0.0
        if p is not None:
            q = int(target // (ratio * s_pts * PV))
            q = min(q, int((eq - floor - 100.0) // (s_pts * PV + COST)))
            if q >= 1:
                if eq - q * (s_pts * PV + COST) <= floor:
                    return "failed"
                day_pnl = q * (p * PV - COST)
                traded += 1
        eq += day_pnl
        if eq <= floor:
            return "failed"
        best = max(best, day_pnl)
        peak = max(peak, eq)
        if eq >= 3000.0 and best < 0.5 * eq and traded >= 3:
            return "passed"
    floor = min(peak - 2000.0, 0.0)
    return "frozen" if eq - floor - 100.0 < S_FROZEN * (s_pts * PV + COST) else "open"


def main() -> None:
    S.init({}, *sys.argv[1:4])
    bars, _, skip = S.D["nq"]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 0.0, "trail_dd": 0.0, "qty": 1, **K317})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    tf["day"] = tf.entry_time.dt.tz_convert(NY).dt.date
    first = tf.sort_values("entry_time").groupby("day").first()
    m1 = pd.read_pickle(f"{sys.argv[1]}/nq1m_scaled.pkl")[["open", "high", "low", "close"]]
    t = m1.index.tz_convert(NY)
    mins = t.hour * 60 + t.minute
    m1 = m1[(mins >= 570) & (mins < 960)]
    dates = m1.index.tz_convert(NY).date
    groups = {d: g for d, g in m1.groupby(dates)}
    sessions = sorted(groups)
    rows = []
    for s_pts in (25.0,):
        for ratio in (1.0, 1.25):
            pts = outcomes(first, groups, s_pts, ratio)
            for target in (1200.0,):
                for i, d in enumerate(sessions):
                    if d.weekday() != 0 or i + 10 > len(sessions):
                        continue
                    res = test(sessions[i:i + 10], pts, s_pts, ratio, target)
                    rows.append({"stop": s_pts, "ratio": ratio, "target": target,
                                 "set": "development 2015-19" if d.year < 2020 else "unseen 2020-25", "res": res})
    df = pd.DataFrame(rows)
    df.to_csv("verification/noise_v2/g281c_frozen.csv", index=False)
    out = df.groupby(["set", "stop", "ratio", "target"]).res.value_counts(normalize=True).unstack().fillna(0).round(3)
    print(out.to_string(), flush=True)


if __name__ == "__main__":
    main()
