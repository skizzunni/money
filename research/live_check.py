"""Live against the backtest after a session (docs section 175): the NinjaTrader trade export, trade by trade.

    python research/live_check.py trades.csv                       # the rule checks (no bars needed)
    python research/live_check.py trades.csv --bars MNQ_12-26.Last.txt   # + each day against the reference

trades.csv: NinjaTrader 8 > Account Performance (or Strategy Performance) > Trades tab > right-click > Export (CSV).
The columns used: Instrument, Market pos., Qty, Entry price, Exit price, Entry time, Exit time, Entry name, Exit name,
Profit. Times are read in --tz (NinjaTrader's Tools > Options > General > Time zone; default New York). The account
column is never read or printed.

1. The rule checks, from the export alone: entry names (Long / Short / GapLong / GapShort for MNQ, CarryLong /
   CarryShort for gold), MNQ entry times (the gap trade at 09:35, the band at a check: 10:00, 10:30, ... 14:00), at
   most 3 contracts, no MNQ trade losing more than the $200 hard stop (100 points) plus 4 points of slippage, the gap
   trade's stop at most 30 points, out by 15:55 (MNQ) / 14:15 (gold) and never overnight, at most 9 MNQ trades a day,
   no entry once the day's closed MNQ P/L is down $600, and the exit names (a "No stop" or "Exit retry" is the
   safety net working: worth a look, see docs sections 166 and 168).
2. With --bars (NinjaTrader > Tools > Historical Data > Export, MNQ 1 Minute, Last; the same file as
   research/mnq_bars.py reads, with 60+ sessions before the day): the reference trades for each day in the export
   (research/zoo/strats.py: the gap trade and the band with the shipped settings, no trades on FOMC days, the news
   rule from the 08:20-08:34 volume), matched to the live trades by side and entry bar. Points, not dollars (the
   size comes from the account).
   The cushion guard (under $1,000 over the floor: only band breaks 1.5 sigma past the band) is not known from the
   export, so each reference band trade shows its stretch; under the guard only those at 1.5 or more are taken.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
NY = "America/New_York"
MNQ_NAMES = {"Long", "Short", "GapLong", "GapShort"}
GOLD_NAMES = {"CarryLong", "CarryShort"}
KNOWN_EXITS = {"Stop loss", "Profit target", "Session end", "Gap exit", "Back inside", "Time exit",
               "Exit on session close", "No stop", "Exit retry"}
WHY = {"stop": "Stop loss", "target": "Profit target", "time": "Session end", "exit": "Back inside"}
HARD_PTS, SLIP_PTS, GAP_CAP, DAY_STOP, MAX_Q, MAX_TRADES = 100.0, 4.0, 30.0, 600.0, 3, 9


@dataclass
class Trade:
    inst: str
    side: int
    qty: int
    entry: float
    exit: float
    t_in: pd.Timestamp
    t_out: pd.Timestamp
    name_in: str
    name_out: str
    profit: float
    flags: list = field(default_factory=list)

    @property
    def mnq(self) -> bool:
        return self.inst.upper().startswith("MNQ")

    @property
    def points(self) -> float:
        return (self.exit - self.entry) * self.side


def _num(x) -> float:
    """'$1,234.50', '($12.50)', '-$12.50', '1234,5' (a comma decimal), 12.5 -> float."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip()
    neg = s.startswith("(") and s.endswith(")") or "-" in s
    s = re.sub(r"[^0-9.,]", "", s)
    if "," in s and "." not in s and re.fullmatch(r"\d+,\d{1,2}", s):
        s = s.replace(",", ".")
    s = s.replace(",", "")
    return -float(s) if neg else float(s)


def _col(df: pd.DataFrame, *names: str) -> str:
    norm = {re.sub(r"[^a-z]", "", c.lower()): c for c in df.columns}
    for n in names:
        if re.sub(r"[^a-z]", "", n.lower()) in norm:
            return norm[re.sub(r"[^a-z]", "", n.lower())]
    raise SystemExit(f"the export has no '{names[0]}' column (columns: {', '.join(map(str, df.columns))})")


def read_trades(path: str, tz: str = NY) -> list[Trade]:
    df = pd.read_csv(path, sep=None, engine="python")
    df = df.dropna(how="all")
    c = {k: _col(df, *v) for k, v in {
        "inst": ("Instrument",), "pos": ("Market pos.", "Market position"), "qty": ("Qty", "Quantity"),
        "e": ("Entry price",), "x": ("Exit price",), "ti": ("Entry time",), "to": ("Exit time",),
        "ni": ("Entry name",), "no": ("Exit name",), "p": ("Profit",)}.items()}
    out = []
    for _, r in df.iterrows():
        if pd.isna(r[c["inst"]]) or pd.isna(r[c["ti"]]):
            continue

        def t(v):
            return pd.Timestamp(pd.to_datetime(str(v))).tz_localize(tz).tz_convert(NY)
        side = 1 if str(r[c["pos"]]).strip().lower().startswith("l") else -1
        out.append(Trade(str(r[c["inst"]]).strip(), side, int(_num(r[c["qty"]])), _num(r[c["e"]]), _num(r[c["x"]]),
                         t(r[c["ti"]]), t(r[c["to"]]), str(r[c["ni"]]).strip(), str(r[c["no"]]).strip(),
                         _num(r[c["p"]])))
    return sorted(out, key=lambda x: x.t_in)


def _mins(t: pd.Timestamp) -> float:
    return t.hour * 60 + t.minute + t.second / 60


def _half_day(t: pd.Timestamp) -> bool:  # as the strategies: the Friday after Thanksgiving, Christmas Eve
    return (t.month == 11 and t.dayofweek == 4 and 23 <= t.day <= 29) or (t.month == 12 and t.day == 24)


def check_rules(trades: list[Trade]) -> list[Trade]:
    """Flags each trade that breaks a rule the strategies keep (module docstring, item 1)."""
    by_day: dict = {}
    for tr in trades:
        m_in, m_out = _mins(tr.t_in), _mins(tr.t_out)
        if tr.t_out.date() != tr.t_in.date():
            tr.flags.append("held overnight")
        if tr.qty > MAX_Q:
            tr.flags.append(f"{tr.qty} contracts (most is {MAX_Q})")
        if tr.name_out and tr.name_out not in KNOWN_EXITS:
            tr.flags.append(f"exit '{tr.name_out}' is not one of the strategy's (a manual close?)")
        elif tr.name_out in ("No stop", "Exit retry"):
            tr.flags.append(f"'{tr.name_out}': the safety net closed it (sections 166/168) - check the Log tab")
        if tr.mnq:
            if tr.name_in not in MNQ_NAMES:
                tr.flags.append(f"entry '{tr.name_in}' is not MnqCleanBand's (a manual or another strategy's trade?)")
            gap = tr.name_in.startswith("Gap")
            if gap and not 575 <= m_in < 580.5:
                tr.flags.append(f"gap entry at {tr.t_in:%H:%M:%S} (expected 09:35)")
            if not gap and tr.name_in in MNQ_NAMES and not (600 <= m_in < 845 and (m_in - 600) % 30 < 5):
                tr.flags.append(f"band entry at {tr.t_in:%H:%M:%S} (expected at a check: 10:00, 10:30, ... 14:00)")
            if tr.points < -(GAP_CAP if gap else HARD_PTS) - SLIP_PTS:
                tr.flags.append(f"lost {-tr.points:.2f} points a contract (the stop is at most "
                                f"{GAP_CAP if gap else HARD_PTS:.0f}): a stop that did not hold?")
            if m_out > (790 if _half_day(tr.t_in) else 955) + 1.5:
                tr.flags.append(f"out at {tr.t_out:%H:%M:%S} (the strategy is out by 15:55; 13:10 on half days)")
            if gap and m_out > 595 + 1.5 and tr.name_out == "Gap exit":
                tr.flags.append(f"gap exit at {tr.t_out:%H:%M:%S} (expected 09:55)")
            day = by_day.setdefault(tr.t_in.date(), {"n": 0, "closed": []})
            done = sum(p for t_out, p in day["closed"] if t_out <= tr.t_in)
            if done <= -DAY_STOP:
                tr.flags.append(f"entered with the day already down ${-done:,.0f} (the day stop is ${DAY_STOP:,.0f})")
            day["n"] += 1
            if day["n"] > MAX_TRADES:
                tr.flags.append(f"trade {day['n']} of the day (most is {MAX_TRADES})")
            day["closed"].append((tr.t_out, tr.profit))
        elif tr.name_in in GOLD_NAMES and m_out > 855 + 1.5:
            tr.flags.append(f"gold out at {tr.t_out:%H:%M:%S} (expected by 14:15)")
    return trades


# ---------------------------------------------------------------- the reference (item 2)
def days_from_bars(path: str) -> list[dict]:
    sys.path[:0] = [HERE, os.path.join(HERE, "zoo")]
    import harness as H
    import mnq_bars as M
    import news as N
    bars = M.load(path)
    days = H.rth5(bars)
    nm = N.news_map(bars, 1)
    for d in days:
        d["news"] = nm.get(d["d"], (np.nan, np.nan, np.nan))
    return days


def reference(days: list[dict], i: int) -> list[dict]:
    """The day's reference trades (points; the gap trade first, the band, the news rule, the $600 day stop at 1
    contract as a stand-in for the size)."""
    sys.path[:0] = [os.path.join(HERE, "zoo")]
    import bench as B
    import strats as S
    if i < max(21, B.BAND["trend"] + 1):
        return []
    fomc = set(pd.to_datetime(pd.read_csv(os.path.join(HERE, "fomc_dates.csv")).date).dt.date)
    if days[i]["d"] in fomc:  # docs 180: no trades on an FOMC statement day
        return [{"fomc": True}]
    sp = days[i]["news"][0]
    if sp == sp and B.NEWS[0] <= sp < B.NEWS[1]:
        return [{"news_skip": True, "spike": sp}]
    out, day = [], 0.0
    gap = S.gap_go(days, i, 0.25, **B.GAP)
    band = S.noise(days, i, 0.25, stop_slip=1, nt=True, **B.BAND)
    for n, (side, eb, e, x, why, *_) in enumerate(gap + band):
        if day <= -DAY_STOP:
            break
        is_gap = n < len(gap)
        st = np.nan if is_gap else S.band_stretch(days, i, side, eb, B.BAND["k"], B.BAND.get("sig_min", 0))
        name = ("Gap" if is_gap else "") + ("Long" if side > 0 else "Short")
        out.append({"side": side, "mm": int(days[i]["mm"][eb]), "entry": e, "exit": x, "name": name,
                    "why": "Gap exit" if is_gap and why == "time" else WHY.get(why, why), "stretch": st})
        day += ((x - e) * side * 2.0 - 1.24)
    return out


def compare(trades: list[Trade], days: list[dict]) -> list[str]:
    lines, idx = [], {d["d"]: i for i, d in enumerate(days)}
    mnq = [t for t in trades if t.mnq]
    for day in sorted({t.t_in.date() for t in mnq}):
        live = [t for t in mnq if t.t_in.date() == day]
        if day not in idx:
            lines.append(f"{day}: not in the bars file (or a short session) - no reference")
            continue
        ref = reference(days, idx[day])
        if ref and ref[0].get("fomc"):
            lines.append(f"{day}: an FOMC day (the 14:00 Fed statement): the reference has no trades, live has "
                         f"{len(live)}" + (" - is FomcSkip on and the date in FomcDates?" if live else ""))
            continue
        if ref and ref[0].get("news_skip"):
            lines.append(f"{day}: a mild-news day (08:30 spike {ref[0]['spike']:.1f}x): the reference has no trades, "
                         f"live has {len(live)} - is NinjaTrader's chart on extended hours (ETH)?")
            continue
        lines.append(f"{day}: reference {len(ref)} trade(s), live {len(live)}")
        used = set()
        for r in ref:
            hit = next((t for t in live if id(t) not in used and t.side == r["side"]
                        and r["mm"] - 1 <= _mins(t.t_in) < r["mm"] + 5.5), None)
            st = "" if np.isnan(r["stretch"]) else f", stretch {r['stretch']:.2f}"
            desc = (f"{r['mm'] // 60:02d}:{r['mm'] % 60:02d} {r['name']:<8} {r['entry']:.2f} -> {r['exit']:.2f} "
                    f"({r['why']}{st})")
            if hit is None:
                lines.append(f"  reference only: {desc}" + (" - skipped by the cushion guard if under $1,000 and the "
                                                             "stretch is under 1.5" if st else ""))
                continue
            used.add(id(hit))
            de, dx = (hit.entry - r["entry"]) * r["side"], (hit.exit - r["exit"]) * r["side"]
            lines.append(f"  matched: {desc} | live {hit.entry:.2f} -> {hit.exit:.2f} ({hit.name_out}), entry "
                         f"{de:+.2f} pts, exit {dx:+.2f} pts")
        for t in live:
            if id(t) not in used:
                lines.append(f"  live only: {t.t_in:%H:%M:%S} {t.name_in} {t.entry:.2f} -> {t.exit:.2f} "
                             f"({t.name_out}) - not in the reference")
    return lines


def report(trades: list[Trade], days: list[dict] | None = None) -> str:
    check_rules(trades)
    out = [f"{len(trades)} trade(s): {sum(t.mnq for t in trades)} MNQ, {sum(not t.mnq for t in trades)} other"]
    for t in trades:
        out.append(f"{t.t_in:%Y-%m-%d %H:%M:%S} {t.inst} {t.name_in} x{t.qty} {t.entry:.2f} -> {t.exit:.2f} "
                   f"{t.t_out:%H:%M:%S} {t.name_out}: {t.points:+.2f} pts, ${t.profit:+,.2f}"
                   + ("" if not t.flags else "\n    CHECK: " + "\n    CHECK: ".join(t.flags)))
    n = sum(bool(t.flags) for t in trades)
    out.append("All trades keep the rules." if n == 0 else f"{n} trade(s) to look at (CHECK above).")
    if days is not None:
        out += ["", "Against the reference (points; contracts come from the account):"] + compare(trades, days)
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("trades")
    ap.add_argument("--bars", help="NinjaTrader 1-minute MNQ export (yyyyMMdd HHmmss;o;h;l;c;v), 60+ sessions")
    ap.add_argument("--tz", default=NY, help="NinjaTrader's time zone for the export's times (default New York)")
    a = ap.parse_args(argv)
    print(report(read_trades(a.trades, a.tz), days_from_bars(a.bars) if a.bars else None))


if __name__ == "__main__":
    main()
