# O3 — the ONYX models from the user's latest screenshots (analysis and pre-registration)

Written and committed on 2026-10-30, before `sweep3` was run.

## What the screenshots show (paper model, points, MNQ, 24-hour trading)

| Model | Net points | Win % | Trades | Max DD (pts) | Points a trade | Return / DD |
|---|---|---|---|---|---|---|
| Trend Follow (sim) | +239.76 | 44.6 | 83 | 668.94 | +2.9 | 0.36 |
| Displacement Fill (live) | +956.77 | 55.9 | 34 | 303.32 | +28.1 | 3.2 |
| Sweep Reversal v3 (live, "testing 23/30") | +616.93 | 65.2 | 23 | 94.12 | +26.8 | 6.6 |

**Reading them honestly:**
- **These are points before costs.** Many entries are mid-tick prices, such as 29087.13 and 29454.44, which no order
  fills at. So they are model prices, not fills.
  - At 1 MNQ, $1.24 in fees and a tick a side cost about 1 point a trade.
- **The samples are small, from about two weeks.** With 23 trades, a 65.2% win rate has a 95% range of about 43-84%.
- **Two of these numbers were already seen on Oct 23:**
  - Trend Follow's 668.94-point drawdown is the same figure. That history has now reached +240 points over 83
    trades, about 3 points a trade.
  - Sweep Reversal v3 then stood at −71 points over 3 trades.

**Already tested on history** (docs/RESULTS.md, "The ONYX models, tested on history"):
- Displacement Fill (`fvg`) and Trend Follow (`trendpb`) as described, around the clock and in regular hours.
- Around the clock, no variant was positive on all three data sets.
- In regular hours, Trend Follow (mornings, 3R) was slightly positive, with PF 1.11-1.22 on the held-out sets.

**New in these screenshots, about Sweep Reversal v3:**
- Its "rejected" message: "Price reclaimed a target-only or non-structural level; it cannot prove a sweep entry",
  with "ROUND_NUMBER, Level 28700.0".
- So entries come only from structural levels, and round numbers serve as targets.
- Its targets, such as 29198.00, 29498.00 and 29502.00, and its R multiples of 1.15-4.50 fit a target at the next
  round level.
- The earlier `sweep` used only yesterday's high and low, a 2R target and regular hours.

## Rules for `sweep3`, frozen now (`research/patterns.py`, around the clock, `PATTERNS_ETH=1`)

**Session:** 18:00-17:00 New York, 5-minute bars.

**Structural levels at bar i:**
- the previous session's high and low;
- every swing high and low (3 bars each side) from the last 12 hours that price has not traded through since.

**Entry**
- Short when bar i's high trades above a level and the bar closes back below it. Longs are mirrored.
- The trade is a market order at the next bar's open. Each level is used once.

**Stop:** 1 tick past bar i's extreme.

**Target:** the nearest multiple of 100 points in the trade's direction that is at least 1R from the fill.
- No trade if that target is more than 5R away.

**Execution, unchanged from `patterns.py`:**
- risk about $500, 1-10 MNQ;
- $0.62 a side and a tick on market and stop fills;
- a bar that reaches both the stop and the target counts as the stop;
- one trade at a time, flat at the session's end.

**Data:**
- raw NQ futures 2015-2019 (development) and 2020-2025;
- the user's MNQ Jul-Oct 2026.

**The test (one run):** the as-taught variant, with no trend filter, no breakeven and all hours.
- **It passes** if PF ≥ 1.2 and the net is positive on all three sets.
- The other execution variants that `patterns.py` prints are descriptive only.

## Results (2026-10-30; one run; `verification/noise_v2/o3_sweep3.csv`)

**As taught** (no filters, round-number target; 1-10 MNQ at about $500 risk):

| | NQ 2015-2019 (development) | NQ 2020-2025 | MNQ Jul-Oct 2026 |
|---|---|---|---|
| Trades a year | 463 | 1,277 | 1,922 |
| Winners | 28.7% | 27.9% | 24.5% |
| PF | **0.76** | **0.86** | **0.72** |
| Average R | −0.31 | −0.16 | −0.24 |
| Net a year | −$11,375 | −$37,605 | −$142,808 (annualized from about 3.5 months) |

**Fails.** It lost on all three sets.

**Every one of the 40 execution variants** (day's-direction filter, breakeven at 1R, mornings, 1-3R targets) also
lost on development. The best development PF was 0.78. So no improvement can be chosen honestly on development, and
none is adopted.

**Why the screenshots look better than history:**
- About two weeks of trades.
- Points before costs, at model prices.
- Versions changed in between: v2 then v3, with an optimizer and grades.
- A run of 23 trades with 65% winners happens by chance about once in a few dozen tries, even for a breakeven rule.

**The other two ONYX models were tested on Oct 23** (docs/RESULTS.md):
- Displacement Fill: about breakeven.
- Trend Follow: slightly positive only in regular-hours mornings with a 3R target, PF 1.11-1.22 on held-out data.
