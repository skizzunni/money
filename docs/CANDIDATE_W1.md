# Candidate W1 — UNVERIFIED (pre-registration)

Written and committed on 2026-10-30, before `research/w1_video.py` was run.

W1 is the trade in the user's screen recording ("Winter Trades", NQ, 10/29/26), turned into rules a computer can
follow. Nothing here promises a profit or a win rate.

## What the recording shows

- 15 NQ short at about 29,543, with a buy stop about 20 points above. It was stopped.
- A second short at 29,671, with the stop 11 points above, at the top of a spike, around 11:00.
- That short was held to about 15:00, when NQ fell about 500 points; the screen shows +$157,725.
- The level came from a chat alert ("monitor 29555-29585"). The "insider" caption names no rule.

## Frozen rules (1 MNQ; both directions, mirrored)

- **Level:** the previous session's regular-hours high (for shorts) or low (for longs). This is the objective stand-in
  for the alert's zone.
- **Signal:** a 5-minute bar whose high is above the previous high and whose close is back below it. Checked from
  09:35 to 15:00.
- **Entry:** a market short at the next bar's open, less 1 tick.
- **Stop:** 2 ticks above the highest high since the level was first crossed that day. That is the spike's high, as in
  the recording.
- **No target.** The trade is held to the 15:55 bar's close, as in the recording.
- **Re-entry:** if stopped, one more attempt that day on the same side, on a new signal at the same level, as in the
  recording.
- Longs mirror this at the previous low.
- One position at a time.

## Data, costs and measures

**Data:**
- the Jan 2 2025 – Oct 2026 MNQ stand-in, at its own prices;
- NQ futures 2015 – Jul 2025;
- the Nasdaq-100 index 2011 – Sep 2026.

The histories are scaled to a 30,000 price level.

**Costs:**
- $0.62 a side;
- 1 tick on every market and stop fill.

**Reported:**
- trades;
- net win % (a win means above $0 after costs) and the breakeven win %;
- net $ a trade and t;
- profit factor;
- net $;
- closed and marked-equity drawdown;
- the largest winner;
- the share of trades stopped out;
- the longest run of losing trades.

## Acceptance

The user's targets on the stand-in: net at least $75,000, net win at least 80%, PF at least 2.0 and marked DD under
$4,000.
- They are checked at 1 MNQ as measured.
- Size is not raised unless the net expectancy is positive on every data set.

## Results (2026-10-30; one run, 1 MNQ; `verification/noise_v2/w1_video.csv`)

| | Stand-in Jan 2025 – Oct 2026 | NQ 2015 – Jul 2025 | Index 2011 – Sep 2026 |
|---|---|---|---|
| Trades (per yr) | 332 (205) | 1,740 (207) | 3,012 (213) |
| Stopped out | 57.8% | 57.5% | 58.4% |
| Net win % / breakeven win % | 28.3 / 33.2 | 30.1 / 28.5 | 30.4 / 29.7 |
| Gross / net $ a trade (cost $2.24) | −$18.25 / **−$20.49** | $10.91 / $8.67 | $5.89 / $3.65 |
| t | −1.42 | 0.97 | 0.58 |
| Profit factor | **0.794** | 1.077 | 1.034 |
| Net $ | **−$6,802** | +$15,081 | +$10,993 |
| Closed / marked DD | $9,459 / **$9,523** | $8,686 / $9,397 | $11,511 / $12,243 |
| Largest winner | $1,610 | $2,582 | $3,495 |
| Longest losing run | 11 | 19 | 19 |

**Acceptance on the stand-in: fails all four.**
- Net −$6,802, against $75,000.
- Net win 28.3%, against 80%.
- PF 0.794, against 2.0.
- Marked DD $9,523, against $4,000.

**What the video shows, and what the rules show:**
- The recording shows the rare day that pays. Hold-to-close winners do reach many times the risk.
- But about 58% of the trades are stopped, and about 70% lose after costs.
- Over 10-16 years the result is roughly zero after costs, and over the user's window it loses.
- At the recording's size of 15 NQ (150 MNQ), the stand-in's −$6,802 would be about −$1.0 million. Its $9,523 marked
  drawdown would be about $1.4 million.

**Decision:** W1 is rejected. No size is added.
