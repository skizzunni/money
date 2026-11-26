"""research/live_check.py (docs 175): a synthetic NinjaTrader trade export and 1-minute bars export; the rule checks
flag what they should and nothing else, and the trades match the reference they were made from."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from test_ninjatrader_clean import synthetic_days

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "zoo")]
import live_check as L  # noqa: E402

HEADER = ("Trade number,Instrument,Account,Strategy,Market pos.,Qty,Entry price,Exit price,Entry time,Exit time,"
          "Entry name,Exit name,Profit,Cum. net profit,Commission,MAE,MFE,ETD,Bars")


def write_bars(days: list, path: Path, news_day=None, spike=2.5) -> None:
    """Each 5-minute bar as one 1-minute bar at its start (rth5 rebuilds the same 5-minute bars), NinjaTrader's
    format (UTC, the bar's end); news_day gets 08:20-08:34 bars with the 08:30 volume `spike` x the 08:20 volume."""
    rows = []
    for d in days:
        base = pd.Timestamp(d["d"]).tz_localize("America/New_York")
        if d["d"] == news_day:
            px = d["o"][0]
            for m in list(range(500, 515)) + [569]:
                rows.append((base + pd.Timedelta(minutes=m), px, px + 1, px - 1, px, 250.0 * spike if 510 <= m < 515
                             else 250.0))
        for k in range(len(d["o"])):
            rows.append((base + pd.Timedelta(minutes=int(d["mm"][k])), d["o"][k], d["h"][k], d["l"][k], d["c"][k],
                         d["v"][k]))
    with open(path, "w") as f:
        for t, o, h, lo, c, v in rows:
            end = (t + pd.Timedelta(minutes=1)).tz_convert("UTC")
            f.write(f"{end:%Y%m%d %H%M%S};{o};{h};{lo};{c};{int(v)}\n")


def row(n, side, qty, e, x, t_in, t_out, name_in, name_out, inst="MNQ 12-26"):
    pts = (x - e) * (1 if side > 0 else -1)
    p = pts * 2 * qty - 1.24 * qty
    money = f"${p:,.2f}" if p >= 0 else f"(${-p:,.2f})"
    return (f"{n},{inst},SIM,MnqCleanBand,{'Long' if side > 0 else 'Short'},{qty},{e},{x},"
            f"{t_in:%m/%d/%Y %I:%M:%S %p},{t_out:%m/%d/%Y %I:%M:%S %p},{name_in},{name_out},\"{money}\",\"$0.00\","
            f"$1.24,$0.00,$0.00,$0.00,1")


def test_parse_money_and_numbers():
    assert L._num("$1,234.50") == 1234.5
    assert L._num("($12.50)") == -12.5
    assert L._num("-$12.50") == -12.5
    assert L._num("12,5") == 12.5
    assert L._num(3) == 3.0


def test_live_check_rules_and_reference(tmp_path):
    days = synthetic_days()
    bars = tmp_path / "MNQ.Last.txt"
    # a news day: the first ready day with reference trades
    write_bars(days, bars)
    ref_days = L.days_from_bars(str(bars))
    assert len(ref_days) == len(days)
    with_ref = [i for i in range(len(ref_days)) if L.reference(ref_days, i)]
    assert len(with_ref) > 20
    news_i, clean_i, edit_i = with_ref[-1], with_ref[-3], with_ref[-5]
    write_bars(days, bars, news_day=days[news_i]["d"])
    ref_days = L.days_from_bars(str(bars))
    assert L.reference(ref_days, news_i)[0].get("news_skip")

    lines, n = [HEADER], 0

    def at(i, mm, sec=2):
        return pd.Timestamp(ref_days[i]["d"]) + pd.Timedelta(minutes=mm, seconds=sec)

    def exit_name(r):
        return r["why"]

    clean = L.reference(ref_days, clean_i)
    for r in clean:  # a clean day: every reference trade, as NinjaTrader would book it
        n += 1
        lines.append(row(n, r["side"], 2, r["entry"], r["exit"], at(clean_i, r["mm"]), at(clean_i, r["mm"] + 25),
                         r["name"], exit_name(r)))
    edit = L.reference(ref_days, edit_i)
    r0 = edit[0]
    n += 1  # the first trade lost 120 points: a stop that did not hold
    lines.append(row(n, r0["side"], 1, r0["entry"], r0["entry"] - r0["side"] * 120, at(edit_i, r0["mm"]),
                     at(edit_i, 958), r0["name"], "Exit on session close"))
    n += 1  # a manual trade at 11:17
    lines.append(row(n, 1, 1, 21000.0, 21010.0, at(edit_i, 677), at(edit_i, 690), "Buy", "Close"))
    n += 1  # a trade on the news day
    lines.append(row(n, 1, 1, 21000.0, 21010.0, at(news_i, 600), at(news_i, 610), "Long", "Stop loss"))
    path = tmp_path / "trades.csv"
    path.write_text("\n".join(lines) + "\n")

    trades = L.read_trades(str(path))
    assert len(trades) == n
    out = L.report(trades, ref_days)
    flagged = [t for t in trades if t.flags]
    assert all(not t.flags for t in trades if t.t_in.date() == ref_days[clean_i]["d"])
    by = {t.name_in: t for t in flagged}
    bad = next(t for t in trades if t.name_out == "Exit on session close")
    assert any("lost 120.00 points" in f for f in bad.flags)
    assert any("out at 15:58" in f for f in bad.flags)
    assert any("not MnqCleanBand's" in f for f in by["Buy"].flags)
    assert any("not one of the strategy's" in f for f in by["Buy"].flags)
    assert len(flagged) == 2
    assert f"{ref_days[clean_i]['d']}: reference {len(clean)} trade(s), live {len(clean)}" in out
    assert out.count("matched:") == len(clean) + 1
    sec = out.split(f"{ref_days[clean_i]['d']}: reference")[1].split("\n2026")[0]
    assert sec.count("matched:") == len(clean) and sec.count("entry +0.00 pts, exit +0.00 pts") == len(clean)
    assert "only:" not in sec
    assert "live only:" in out and "Buy" in out
    assert f"{ref_days[news_i]['d']}: a mild-news day" in out
    if len(edit) > 1:
        assert "reference only:" in out


def test_live_check_cli(tmp_path, capsys):
    path = tmp_path / "t.csv"
    t0 = pd.Timestamp("2026-11-30 09:35:01")
    path.write_text(HEADER + "\n" + row(1, -1, 3, 21000.0, 20990.0, t0, t0 + pd.Timedelta(minutes=20), "GapShort",
                                        "Gap exit") + "\n")
    L.main([str(path)])
    out = capsys.readouterr().out
    assert "1 trade(s): 1 MNQ" in out and "All trades keep the rules." in out and "+10.00 pts" in out
