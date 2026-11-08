# The ONYX account's live trades, Oct 30 - Nov 6, 2026 (analysis)

Source: the user's Tradovate export `completed_trades_2026-11-08T21-18-35.csv` (account TAKEPROFIT113061309, MNQ),
and screenshots of ONYX's Displacement Fill (archived v2), Sweep Reversal (v3, live) and Trend Follow (v2, sim).
Partial fills of one entry (same time, side and price) are counted as one position. Times are New York.

## What the account did

33 positions, 1-3 MNQ: **45.5% winners, +$2,480.50 net** (after $129 in commissions).

| Entry time (New York) | Positions | Winners | Net |
|---|---:|---:|---:|
| 09:30-11:30 | 4 | 75% | +$2,142.00 |
| 11:30-16:00 | 5 | 80% | +$2,109.50 |
| 16:00-24:00 | 6 | 33% | −$1,314.00 |
| 00:00-09:30 | 18 | 33% | −$457.00 |

- **Regular hours made all the money**: 9 positions, 78% winners, +$4,251.50.
- **Overnight lost it back**: 24 positions, 33% winners, −$1,771.00. That includes the worst trade, a short at 19:14 on
  Nov 5 stopped for −$1,200, and the four losers in a row on Nov 6 before the open.
- By day: Oct 30 +$958.50, Nov 1 +$642, Nov 2 +$1,345.50, Nov 3 +$388.50, Nov 4 +$1,740, Nov 5 −$1,947, Nov 6 −$647.

## How this fits the history tests

The same split showed up in the history tests of the ONYX models (docs/RESULTS.md, "The ONYX models, tested on
history"; docs/CANDIDATE_O3.md):
- Around the clock, no variant of the displacement fill, the sweep or the trend pullback was positive on all three data
  sets. Overnight moves are small next to the costs.
- In regular hours the trend pullback (mornings, 3R) was the one that held up, PF 1.11-1.22 on held-out data.
- The sweep as described lost on every set (PF 0.72-0.86).

**Nine regular-hours trades are a small sample.** A 78% win rate on 9 trades has a 95% range of about 40-97%. But it
points the same way as 16 years of history.

## The fix

1. **Trade 09:30-16:00 New York only.** Turn off overnight and evening sessions on all three models. Over this week
   that alone turns +$2,480 into +$4,251 and removes the −$1,200 trade.
2. **Sweep Reversal**: its screenshot shows 5 stops in a row on Nov 5-6, all outside regular hours. Same fix.
3. **Trend Follow**: still in sim; 42.3% winners and a 739-point drawdown over 123 trades. Keep it off the live
   account; its history-tested version (mornings, 3R) is the only part worth a forward test.
4. Keep the per-trade loss under the day's budget: the −$1,200 trade alone was a full day's limit.

These are settings in the ONYX app, which this repository does not contain. They have not been forward-tested; the
history tests above are the evidence.
