# ruff: noqa
"""Research round (2026-11-24): a second gap check. When the 09:30 bar does not qualify (against the gap, or its body
under min_body x the 14-day average range), look again at the 09:35 bar's close: the gap's way from the 09:30 open by
at least `body2` x the average range -> in at the 09:40 open, the stop at the 09:30 open (4 ticks to 30 points from the
expected fill), out at 09:55 as the first check's trade."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import bench as B, strats as S
def gap_go2(days, i, tick, k=0.5, n=14, exit_m=590, cap=30.0, min_body=0.03, body2=0.03, need_with=False, **_):
    if i < n + 1:
        return []
    first = S.gap_go(days, i, tick, k=k, n=n, exit_m=exit_m, cap=cap, min_body=min_body)
    if first:
        return first
    d = days[i]
    pc = S.prev(days, i, "c")
    gap = d["o"][0] - pc
    avg = np.mean([abs(days[j]["o"][0] - S.prev(days, j, "c")) * d["s"] / days[j]["s"] for j in range(i - n, i)])
    side = 1 if gap > 0 else -1
    if abs(gap) < k * avg or len(d["c"]) < 4:
        return []
    if need_with and side * (d["c"][0] - d["o"][0]) <= 0:  # variant: the 09:30 bar its way but too small
        return []
    rng = np.mean([(days[j]["h"].max() - days[j]["l"].min()) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
    if side * (d["c"][1] - d["o"][0]) < body2 * rng:
        return []
    e = d["c"][1] + side * tick
    dist = min(max(abs(e - d["o"][0]), 4 * tick), cap)
    px, x, xb, why = S.walk(d, 2, side, e - side * dist, np.nan, exit_m, tick, at_open=True)
    return [(side, 2, px, x, why, xb)]
S.gap_go2 = gap_go2
base = B.run()
print("shipped:        " + B.line("", base), flush=True)
for kw in (dict(body2=0.03), dict(body2=0.06), dict(body2=0.10), dict(body2=0.03, need_with=True), dict(body2=0.06, need_with=True)):
    r = B.run(legs_fn=lambda g, b, kw=kw: (("gap_go2", {**g, **kw}), ("noise", b)))
    print(f"second check {kw}: " + B.line("", r), flush=True)
