"""Every session of a candidate C NinjaTrader run, classified from its NinjaScript Output (docs/FREQUENCY.md).

    python research/session_audit.py <NinjaScript_Output.txt> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out.csv>
        [--no-open yyyy-mm-dd,...] [--hole yyyy-mm-dd:yyyy-mm-dd] [--warmup yyyy-mm-dd:yyyy-mm-dd]
    python research/session_audit.py <NinjaScript_Output.txt> <out.csv>   (an Output with "C session" lines)

The calendar (sessions with 09:30-16:00 data) comes from the user's MNQ exports; --no-open lists sessions the run's own
data lacks the 09:30 bar for, --hole a range with no bars at all, --warmup the engine's warm-up sessions (all from the
run's own Output and the native Outputs, see the report). Each weekday is one of:
- holiday / skip date: an exchange holiday or a skip date (7/3, 9/7 half days);
- warm-up: before the engine's 14 full sessions;
- missing data: no bars, or no 09:30 bar (no checks possible);
- active: at least one entry;
- no qualifying setup: no check closed past a line;
- refused: qualifying checks, all refused; the reasons are listed (open position, losing positions today, daily
  backstop, account reserve room, evaluation passed, pending entry order, an order problem).
A persistent lockout is a run of eligible sessions, from some date to the end, with no entry while every qualifying
check is refused for the same reason.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402

LINE = re.compile(r"C check (\d{4}-\d\d-\d\d) (\d\d:\d\d) (long|short): (.*)")


def calendar(sep_path, dec_path):
    days = set()
    for p in (sep_path, dec_path):
        b = K.rth(M.load(p))
        m = b.index.tz_convert(K.NY)
        days |= set(m[(m.hour * 60 + m.minute >= 570) & (m.hour * 60 + m.minute < 960)].normalize().tz_localize(None))
    return days


SESSION = re.compile(r"C session (\d{4}-\d\d-\d\d): ([^;]+); (\d+) minutes.*?entries (\d+), not taken (.*)")


def from_session_lines(text, out_path):
    """A run whose Output has candidate C's per-session lines (C2 onward): classified by the strategy itself."""
    rows = [{"session": m.group(1), "status": m.group(2), "minutes": int(m.group(3)), "entries": int(m.group(4)),
             "not taken": m.group(5)} for m in (SESSION.search(x) for x in text) if m]
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    elig = df[~df.status.isin(["warm-up", "skip date"])]
    print(df.status.str.split(":").str[0].value_counts().to_string())
    n = len(elig)
    print(f"eligible sessions {n}; entries {elig.entries.sum()}: {elig.entries.sum() / n:.2f} per session; "
          f"zero-entry sessions {(elig.entries == 0).mean():.0%}")


def main():
    args = sys.argv[1:]
    if len(args) == 2:  # <Output> <out.csv>: the Output's own session lines
        from_session_lines(Path(args[0]).read_text(errors="replace").splitlines(), Path(args[1]))
        return
    opts = {k: v for k, v in zip(args[4::2], args[5::2], strict=False)}
    out_path, text = Path(args[3]), Path(args[0]).read_text(errors="replace").splitlines()
    data_days = calendar(args[1], args[2])
    no_open = {pd.Timestamp(d) for d in opts.get("--no-open", "").split(",") if d}
    hole = [pd.Timestamp(x) for x in opts["--hole"].split(":")] if "--hole" in opts else None
    warm = [pd.Timestamp(x) for x in opts["--warmup"].split(":")] if "--warmup" in opts else None
    skip = {pd.Timestamp(d) for d in K.DEFAULT_SKIP.split(",")}
    checks = {}
    for x in text:
        m = LINE.search(x)
        if m:
            what = m.group(4)
            why = "taken" if what.startswith("entry sent") else what.split("not taken: ", 1)[1].split(" [")[0]
            checks.setdefault(pd.Timestamp(m.group(1)), []).append((m.group(2), m.group(3), why))
    first = min([warm[0]] if warm else [min(data_days)])
    days = pd.bdate_range(first, max(data_days))
    rows = []
    for d in days:
        c = checks.get(d, [])
        taken = sum(w == "taken" for _, _, w in c)
        refused = Counter(w for _, _, w in c if w != "taken")
        if warm and warm[0] <= d <= warm[1]:
            status = "warm-up"
        elif d in skip:
            status = "holiday / skip date"
        elif hole and hole[0] <= d <= hole[1] and d not in data_days:
            status = "missing data (no bars)"
        elif d not in data_days:
            status = "holiday / skip date"
        elif d in no_open:
            status = "missing data (no 09:30 bar)"
        elif taken:
            status = "active"
        elif not c:
            status = "no qualifying setup"
        else:
            status = "refused: " + ", ".join(sorted(refused))
        rows.append({"session": d.date(), "status": status, "qualifying checks": len(c), "entries": taken,
                     **{f"refused: {k}": v for k, v in refused.items()}})
    df = pd.DataFrame(rows).fillna(0)
    eligible = df[~df.status.isin(["warm-up", "holiday / skip date", "missing data (no bars)"])]
    # a persistent lockout: from the first session after the last entry whose refusals are all the same reason
    last_entry = eligible[eligible.entries > 0].session.max() if (eligible.entries > 0).any() else None
    after = eligible[eligible.session > last_entry] if last_entry else eligible
    reasons = {s.split(": ", 1)[1] for s in after.status if s.startswith("refused: ")}
    lock = None
    if len(reasons) == 1:
        lock_reason = reasons.pop()
        lines = [(d, t, w) for d, v in checks.items() for t, _, w in v]
        since = pd.Timestamp(last_entry) if last_entry else pd.Timestamp.min
        refusals = sorted((d, t) for d, t, w in lines if w == lock_reason and d >= since)
        lock = (refusals[0], lock_reason, len(after)) if refusals else None
    df.to_csv(out_path, index=False)
    n = len(eligible)
    per_day = eligible.entries
    print(f"weekdays {days[0].date()}..{days[-1].date()}: {len(df)}")
    print(df.status.str.split(":").str[0].value_counts().to_string())
    print(f"eligible sessions (after warm-up, with data or with only the 09:30 bar missing, not skip dates): {n}")
    print(f"entries {int(per_day.sum())}: {per_day.sum() / n:.2f} per eligible session; sessions with 0 / 1 / 2 / 3+ "
          f"entries: {(per_day == 0).mean():.0%} / {(per_day == 1).mean():.0%} / {(per_day == 2).mean():.0%} / "
          f"{(per_day >= 3).mean():.0%}")
    print("eligible sessions by status:")
    print(eligible.status.value_counts().to_string())
    if lock:
        (d, t), why, k = lock
        print(f"persistent lockout: from {d.date()} {t} ({why}), {k} eligible sessions to the end with no entry")


if __name__ == "__main__":
    main()
