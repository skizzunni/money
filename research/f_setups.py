"""Candidate F's setup ledger and matched entries (docs/CANDIDATE_F.md section 8), from a research/eval_d.py --f run.

    python research/f_setups.py <eval_d --f out folder>

1. The setup ledger, before affordability and portfolio gating: every sweep decision of the D + F1 and D + F2 books
   (the chain up to the decision is the same under E and F, so these are E's decisions too), with E's and F's stop, R,
   price risk (R x $2 x 2) and planned all-in risk, the budget and room tests under each stop, the decision window,
   and what the combined book did with it: taken (filled, or cancelled unfilled and why), skipped (budget, room,
   window) or displaced (a higher-priority entry on the same bar, a position or pending entry already open, the
   day's three campaigns used, the session closed).
2. Matched entries: every decision inside the decision window replayed alone, outside the portfolio and without the
   budget, once with E's stop and once with F's, by the same position manager and cancellation rules
   (mnqbot/candidate_d.py's Model, started at the decision). A diagnostic, never a filter.
3. The execution counts of each book: "Stop passed" exits (a breakeven or trail stop that could not be placed),
   contracts closed at a bar's open beyond their stop (gaps through the stop), overruns.

Writes setups_<book>.csv, isolated_<slippage>t.csv, matched.csv, execution.csv into the folder and prints the tables.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.candidate_d import PV, TICK, DConfig, Model, room_ok, sweep_prices  # noqa: E402

BOOKS = ("D+F1", "D+F2")


def outcome_of(i: int, pool: str, log_at: dict, campaigns: list, cancels: list) -> str:
    """What the combined book did with the decision of `pool` at bar i."""
    for x in log_at.get(i, []):
        if x[1] == "enter" and x[2].endswith(":" + pool):
            if any(c.signal_bar == i for c in campaigns):
                return "taken: filled"
            why = next((c[2] for c in cancels if c[0] > i), "?")
            return f"taken: unfilled ({why})"
        if x[1] == "skip" and x[2] == pool:
            if len(x) == 5:
                return "skipped: budget"
            return {"time": "skipped: decision window", "room": "skipped: room"}.get(x[3], f"displaced: {x[3]}")
    return "?"


def setup_ledger(bars: pd.DataFrame, book: str, seen: list, log: list, campaigns: list, cfg: DConfig) -> pd.DataFrame:
    log_at: dict = {}
    for x in log:
        log_at.setdefault(x[0], []).append(x)
    cancels = [x for x in log if x[1] == "cancel"]
    rows = []
    for i, scale, dec, levels in seen:
        t = bars.index[i]
        end = t.hour * 60 + t.minute + 1
        d, pool = dec["d"], dec["pool"]
        row = {"book": book, "bar": i, "time": t, "pool": pool, "d": d, "fvg_bar": dec["fvg"],
               "in window": cfg.decide_first <= end <= cfg.decide_last}
        for mode, tag in (("extreme", "E"), ("fvg", "F")):
            lim, stop, r, planned = sweep_prices(dec, scale, cfg, mode)
            row.update({"limit": lim, f"{tag} stop": stop, f"{tag} R": r, f"{tag} price risk $": r * PV * cfg.qty,
                        f"{tag} planned $": planned,
                        f"{tag} fits $125": r > 0 and planned <= cfg.budget + 1e-9,
                        f"{tag} room": room_ok(d, lim, r, levels, scale, cfg)})
        fe, ff = row["E fits $125"], row["F fits $125"]
        if not row["in window"]:
            cls = "excluded: decision window"
        else:
            cls = ("affordable under both" if fe and ff else "newly affordable under F" if ff
                   else "affordable under E only" if fe else "affordable under neither")
        row["class"] = cls
        row["E executable"] = row["in window"] and fe and row["E room"]
        row["F executable"] = row["in window"] and ff and row["F room"]
        row["book outcome"] = outcome_of(i, pool, log_at, campaigns, cancels)
        rows.append(row)
    return pd.DataFrame(rows)


def isolated(bars: pd.DataFrame, arrays, i: int, scale: float, dec: dict, mode: str, slip: int) -> dict:
    """One decision alone: the limit placed at bar i with `mode`'s stop, managed until flat or cancelled."""
    o, h, l, c, sc = arrays
    cfg = DConfig(noise=False, williams=False, slippage_ticks=slip, budget=1e12, e_stop=mode)
    m = Model(cfg)
    t = bars.index[i]
    day = (t + pd.Timedelta(hours=6)).strftime("%Y-%m-%d")
    lim, stop, r, planned = sweep_prices(dec, scale, cfg)
    m.day = day
    m._submit(i, m.prefix + dec["pool"], dec["d"], "limit", lim, stop, r, planned, day)
    be = half = False
    k = i + 1
    while k < len(o) and (m.pend or m.lots or m.camp is not None):
        m.step(k, bars.index[k], o[k], h[k], l[k], c[k], sc[k])
        be, half = be or m.be, half or m.half_filled
        k += 1
    out = {"filled": bool(m.campaigns), "R": r, "stop": stop, "price risk $": r * PV * 2, "planned $": planned}
    if not m.campaigns:
        return out
    cp = m.campaigns[0]
    d, s = cp.d, slip * TICK
    paid = sum(lt.qty * s * PV for lt in cp.lots if lt.why != "Profit target")  # limit entries: no entry slippage
    qty = sum(lt.qty for lt in cp.lots)
    out.update({"pnl $": cp.pnl, "contracts": qty, "+1R": be, "+2R (half)": half,
                "initial stop exit": all(lt.why == "Stop loss" and lt.stop == cp.stop0 for lt in cp.lots),
                "stop passed": any(lt.why == "Stop passed" for lt in cp.lots),
                "gap through stop": any(lt.why == "Stop loss" and abs(lt.exit - (o[lt.exit_bar] - d * s)) < 1e-9
                                        and d * (o[lt.exit_bar] - lt.stop) <= 1e-9 for lt in cp.lots),
                "commission $": 2 * cfg.commission * qty, "slippage paid $": paid,
                "declared cost % of risk": 100 * (planned - r * PV * 2) / (r * PV * 2),
                "realized cost % of risk": 100 * (2 * cfg.commission * qty + paid) / (r * PV * qty)})
    return out


def matched_table(iso: pd.DataFrame, setups: pd.DataFrame) -> pd.DataFrame:
    e = iso[iso["mode"] == "extreme"].set_index("bar_pool")
    f = iso[iso["mode"] == "fvg"].set_index("bar_pool")
    both = e.index[e.filled & f.reindex(e.index).filled.fillna(False).astype(bool)]
    fits = setups.drop_duplicates("bar_pool").set_index("bar_pool")
    sub = fits.reindex(both)
    subsets = {"all matched": both,
               "matched, affordable under both": both[sub["class"].eq("affordable under both").to_numpy()],
               "matched, F executable": both[sub["F executable"].to_numpy(dtype=bool)]}
    rows = []
    for name, keys in subsets.items():
        for tag, x in (("E stop", e.loc[keys]), ("F stop", f.loc[keys])):
            n = len(x)
            rows.append({"set": name, "stop": tag, "positions": n,
                         "initial-stop exits %": 100 * x["initial stop exit"].mean() if n else math.nan,
                         "+1R reached %": 100 * x["+1R"].mean() if n else math.nan,
                         "+2R (half) %": 100 * x["+2R (half)"].mean() if n else math.nan,
                         "win rate %": 100 * (x["pnl $"] > 0).mean() if n else math.nan,
                         "net $": x["pnl $"].sum(), "expectancy $": x["pnl $"].mean() if n else math.nan,
                         "median R": x["R"].median() if n else math.nan,
                         "declared cost % of risk (median)": x["declared cost % of risk"].median() if n else math.nan,
                         "realized cost % of risk (median)": x["realized cost % of risk"].median() if n else math.nan,
                         "stop passed": int(x["stop passed"].sum()),
                         "gap through stop": int(x["gap through stop"].sum())})
        fe, ff = e.loc[keys], f.loc[keys]
        rows.append({"set": name, "stop": "F stopped out, E succeeded (diagnostic)",
                     "positions": int((ff["initial stop exit"].to_numpy() & (fe["pnl $"].to_numpy() > 0)).sum())})
    return pd.DataFrame(rows)


def execution_counts(name: str, slip: int, campaigns: list, o: np.ndarray) -> dict:
    s = slip * TICK
    lots = [(c, lt) for c in campaigns for lt in c.lots]
    return {"book": name, "slippage": slip, "positions": len(campaigns),
            "sweep positions": sum(c.sleeve[:2] in ("E:", "F:") for c in campaigns),
            "stop passed (positions)": sum(any(lt.why == "Stop passed" for lt in c.lots) for c in campaigns),
            "stop passed net $": sum(c.pnl for c in campaigns if any(lt.why == "Stop passed" for lt in c.lots)),
            "contracts closed at an open beyond their stop": sum(
                lt.why == "Stop loss" and abs(lt.exit - (o[lt.exit_bar] - c.d * s)) < 1e-9
                and c.d * (o[lt.exit_bar] - lt.stop) <= 1e-9 for c, lt in lots),
            "one contract of two": sum(len(c.lots) == 1 for c in campaigns),
            "overruns": sum(c.pnl < -c.planned - 1e-9 for c in campaigns)}


def main() -> None:
    out = Path(sys.argv[1])
    bars = pd.read_pickle(out / "bars.pkl")
    runs = pd.read_pickle(out / "runs.pkl")
    arrays = tuple(bars[x].to_numpy(float) for x in ("open", "high", "low", "close", "scale"))
    cfg = DConfig()
    by = {(n, s): (camps, log, seen) for n, s, camps, log, seen in runs["results"]}
    ledgers = []
    for book in BOOKS:
        camps, log, seen = by[(book, 2)]
        led = setup_ledger(bars, book, seen, log, camps, cfg)
        led.to_csv(out / f"setups_{book}.csv", index=False)
        ledgers.append(led)
    setups = pd.concat(ledgers)
    setups["bar_pool"] = setups.bar.astype(str) + ":" + setups.pool
    # every decision of the widest book (F2's pools include F1's), inside the window, alone under both stops
    dec_by = {f"{i}:{dec['pool']}": (i, scale, dec) for i, scale, dec, _ in by[("D+F2", 2)][2]}
    win = setups[(setups.book == "D+F2") & setups["in window"]].bar_pool
    iso_all = []
    for slip in (2, 3):
        rows = []
        for key in win:
            i, scale, dec = dec_by[key]
            for mode in ("extreme", "fvg"):
                rows.append({"bar_pool": key, "mode": mode, **isolated(bars, arrays, i, scale, dec, mode, slip)})
        iso = pd.DataFrame(rows)
        iso.to_csv(out / f"isolated_{slip}t.csv", index=False)
        m = matched_table(iso, setups[setups.book == "D+F2"]).assign(slippage=slip)
        iso_all.append(m)
    matched = pd.concat(iso_all)
    matched.to_csv(out / "matched.csv", index=False)
    ex = pd.DataFrame([execution_counts(n, s, camps, arrays[0]) for (n, s), (camps, _, _) in sorted(by.items())])
    ex.to_csv(out / "execution.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    for led in ledgers:
        b = led.book.iloc[0] if len(led) else "?"
        print(f"\n{b}: {len(led)} sweep decisions")
        print(led["class"].value_counts().to_string())
        print("executable under E:", int(led["E executable"].sum()), " under F:", int(led["F executable"].sum()))
        print(pd.crosstab(led["class"], led["book outcome"]).to_string())
        w = led[led["in window"]]
        print("median R, in window: E", w["E R"].median(), " F", w["F R"].median())
    print("\nmatched entries (isolated replays)")
    print(matched.to_string(index=False))
    print("\nexecution counts")
    print(ex.to_string(index=False))


if __name__ == "__main__":
    main()
