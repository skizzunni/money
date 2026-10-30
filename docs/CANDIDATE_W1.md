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
