# Candidate T1 — UNVERIFIED (pre-registration)

Written and committed on 2026-10-28, before the evaluation in `research/t1_eval.py` was run.

T1 is a candidate, not a recommendation. Nothing here promises a profit, a win rate or the absence of losses. Every
trade can lose up to its stop, and more if a stop fills past its price.

## Why this candidate

The reference is v3.6 (`pine/mnq_noise_momentum.pine`), unchanged. On the user's TradingView chart (MNQ1!,
30-minute, Jan 2 2025 to Oct 23 2026) it made +$26,106, profit factor 1.63, 55.8% winners and an $8,444 drawdown.

T1 changes one thing: how the stop moves to break-even. In the reference, the stop moves on the bar after price
reaches the trigger. In T1 it moves inside the bar where price touches the trigger, as a broker's auto-breakeven
does, and at an earlier trigger.

**This choice is not independent of the data.** An exploratory scan on the same data (`v37_broker_lock_*.csv`,
docs/RESULTS.md) showed this setting with the highest 5-minute win rate among the settings tried. So the evaluation
below confirms on data already seen; it is not an out-of-sample test. There is no unseen MNQ data left in this
repository.

## Frozen rules

**Instrument and session**
- MNQ, regular hours 09:30-16:00 New York time.
- Signals at the half-hour checks from 10:00. No new entries after the 15:00 check.
- Any position is closed at the 16:00 close.
- No trading on US market holidays or half days: the date list in the script, and the computed closures on the
  histories.

**News**
- On scheduled FOMC statement days, no shorts before the 14:00 statement.
- No other news filter. Entries start at 10:00, after the 08:30 releases.

**Entry** (the same as the reference)
- Long when a check closes above the upper noise line; short when it closes below the lower one. The noise lines are
  the day's open (or the previous close) ± the 14-session average move to that time.
- Filters:
  - the range-position rule (0.65);
  - no shorts while yesterday's close is above its 50-session average;
  - no trades in the direction of the previous day if that day's range was over 1.5x the 10-day average;
  - no entries after a calm stretch (the 10-day average range under 0.7x the 40-day average).
- A market order at the next bar's open, plus 1 tick of slippage.

**Initial stop** (the same as the reference)
- The closer of two stops:
  - the line stop, 0.24 noise units past the noise line, moved with the line at each check and only ever tightened;
  - the max loss: $187.50 per contract (93.75 points) from the fill, or $250 per contract on the trade after a loser.

**Take-profit** (the same as the reference)
- A limit 2.0 noise units from the fill.

**Break-even and trailing** (the only change)
- The trigger is 0.15 of the max-loss distance: 14.06 points on a normal trade, 18.75 after a loser.
- In the first bar where price touches the trigger, the stop moves to that bar's best price minus (trigger − 2.5
  points). It never sits below the entry + 2.5 points.
- The stop is filled in that same bar if the bar's path comes back to it. The path assumption is the high or low
  nearer the open first, as TradingView assumes.
- After that bar the stop stays at the level it reached, unless the line stop is tighter.
- The reference moves the stop to the entry + 2.5 at 0.35 of the max loss, from the next bar.

**Sizing and limits (100K account)** (the same as the reference)
- Start at 1 MNQ and add 1 contract per $1,500 of closed profit since Jan 2 2025, up to 15.
- At most $2,000 of loss a day.
- A $3,000 end-of-day trailing drawdown that stops at the starting balance.
- Each new trade's contracts are cut to fit the smaller remaining room, with the risk counted from the trade's own
  stop.
- When not even 1 contract fits, 1 contract with its stop cut to the room, if that leaves at least 20 points.

## Costs

Every execution is counted:
- $0.62 per contract per side;
- 1 tick ($0.50 per MNQ) of slippage on every market and stop fill;
- no slippage on take-profit limit fills.

## Data (identical for the reference and T1)

1. The user's own MNQ bars (`MNQ_09-26.Last.txt`, `MNQ_12-26.Last.txt`), trades from Aug 24 2026.
2. The Jan 2 2025 – Oct 2026 stand-in (`proxy_5m.pkl` / `proxy_30m.pkl`): NQ futures to Jul 2025, the Nasdaq-100
   index to Jun 2026, then the user's MNQ.
3. NQ futures 2015-2025 (scaled to today's price level).
4. The Nasdaq-100 index 2011-2026 (scaled).

Each set runs on 5-minute and on 30-minute bars.

## Measured and reported, for both

- **Participation:** sessions, sessions with an entry (count and share), trades per active day, and the share of
  regular-hours bars spent in a position.
- **Executions:** fills (entries plus exits), and the commission and slippage paid, in dollars.
- **Results:**
  - net profit;
  - net expectancy per trade, in dollars and per contract;
  - net win rate: trades with a net profit above $0 after costs;
  - profit factor: gross net profit / gross net loss.
- **Drawdowns:**
  - closed-trade drawdown;
  - marked-equity drawdown: at every bar, the closed equity plus the open position marked at the bar's worst price
    (its low for a long, its high for a short), against the highest close-marked equity before it;
  - end-of-day drawdown, and whether the $3,000 trailing floor was touched.

## Acceptance criteria

Judged on the Jan 2 2025 – Oct 2026 stand-in (set 2), the window the user tests. Each criterion is checked
separately, on both bar lengths. T1 is accepted only if all four pass.

| Criterion | Threshold |
|---|---|
| Net profit | at least $75,000 |
| Net win rate | at least 80% |
| Profit factor | at least 2.0 |
| Marked-equity drawdown | under $4,000 |

The criteria are pass/fail checks on the measured numbers. Nothing in the rules was set to meet them. If T1 fails
any of them, the report says so and T1 is not adopted.
