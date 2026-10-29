# Candidate H1 — UNVERIFIED (pre-registration)

Written and committed on 2026-10-29, before `research/h1_dip.py` was run on any data.

H1 is a research candidate, not a recommendation. Nothing here promises a profit, a win rate or the absence of losses.
Every trade can lose up to its stop, and more when price gaps or slips through it.

## What stays fixed

- **The targets are unchanged:** at least $75,000 net, at least 80% net winning trades, profit factor at least 2.0 and
  marked-equity drawdown under $4,000, on the Jan 2 2025 – Oct 2026 MNQ stand-in. They are pass/fail checks. No rule
  below was chosen to meet them.
- **The failed results stay on record:**
  - v3.6, the reference: +$26,106, PF 1.63, 55.8% winners, $8,444 drawdown on the user's TradingView run.
  - T1: not accepted (docs/CANDIDATE_T1.md).
  - The families listed in docs/RESULTS.md: none had an edge.
- **No more tuning of the rejected branches:** the noise-area momentum settings, T1's lock, and the families already
  rejected.
- **Nothing in this repository claims** a backtest "score", a zero-loss rule, a guaranteed outcome or an assumed
  average winner. H1 uses none of them.

## The hypothesis

When the Nasdaq-100 is in an uptrend, a short sharp pullback over a few sessions tends to partly reverse over the next
session or two.

This is distinct from everything tested before:
- the reference buys strength inside the day; H1 buys weakness measured over days;
- the signal comes from daily closes, not intraday bars;
- the RSI(2) family tested before (`v38_intraday.py`) used 5-minute bars inside a single day.

## Frozen rules

**Signal** (known after the 16:00 close of day t; long only)
- The daily close is the Nasdaq-100 index's regular-hours close, its last 5-minute bar. After the index data ends
  (Sep 30 2026), the stand-in's close is used, ratio-spliced on the last common day.
- **Trend:** day t's close is above its 200-session simple average.
- **Pullback:** the 2-session RSI of the daily closes (Wilder smoothing) on day t is below L.

**Trade on day t+1** (regular hours 09:30-16:00 New York; no trades on closures, half days or sessions with missing
bars)
- **Entry:** a market buy at the open of the entry bar, plus 1 tick.
- **Stop:** k × ATR14 below the fill. ATR14 is the average regular-hours high-low range of the instrument's last 14
  sessions, fixed at entry. A bar that opens past the stop fills at its open, less 1 tick.
- **Target** (when used): a limit 0.5 × ATR14 above the fill, with no slippage. In a bar that reaches both the stop
  and the target, the stop counts.
- **Exit:**
  - "day": out at the 15:55 bar's close, less 1 tick;
  - "swing": out at the first regular-hours close above the 5-session average of daily closes, at the 15:55 bar's
    close less 1 tick, or after 5 sessions at the latest. The stop rests overnight.
- One position at a time; no new signal while a swing trade is open.
- **Prop-firm note:** "swing" holds overnight. Many evaluation accounts forbid that, so a swing setting can win the
  development stage and still be unusable on such an account. This is reported, not hidden.

## Development grid (development data only)

| Setting | Values |
|---|---|
| L | 10, 20, 30 |
| Entry bar | 09:30, 10:00 |
| k | 0.5, 1.0, 2.0 |
| Exit | day, swing |
| Target | none, 0.5 ATR |

That makes 72 settings, all reported.

**Selection rule:**
- Keep the settings with at least 25 trades a year and a positive mean net per trade on both development sets.
- Of those, pick the one with the highest t-statistic of net dollars per trade, pooled over both sets.
- If none qualifies, H1 is rejected at this stage.

## Data

| Set | Development | Holdout |
|---|---|---|
| NQ futures, raw 1-minute bars to 5-minute (roll weeks skipped) | 2015-2019 | 2020 – Jul 2025 |
| Nasdaq-100 index, HistData 1-minute bars to 5-minute | 2011-2018 | 2019 – Sep 2026 |
| The MNQ stand-in (NQ to Jul 2025, the index to Jun 2026, then the user's MNQ) | — | Jan 2 2025 – Oct 2026 |

- NQ and the index trade at their own raw prices. Each trade's points are scaled by 30,000 ÷ the entry price, so
  dollars are comparable across years at today's price level.
- The stand-in uses its own prices, unscaled.
- The holdout is run once, with the frozen setting only.

## Accounting (1 MNQ, every executed trade counted)

**Costs**
- $0.62 per contract per side;
- 1 tick ($0.50) on every market and stop fill;
- no slippage on target limits.

**Cost-aware breakeven accounting**
- A trade is a win only if its net result after all costs is above $0.
- A stop at the entry price is a loss, by the costs.
- Reported:
  - gross and net expectancy per trade, and the cost per trade;
  - the net win rate;
  - the breakeven win rate the trade sizes need: average net loss ÷ (average net win + average net loss);
  - the number of trades within ±$5 net.

**Drawdowns**
- Closed-trade drawdown.
- Marked-equity drawdown, validated separately: at every 5-minute bar, the closed equity plus the open position marked
  at the bar's low, against the highest close-marked equity before it. For a swing trade this includes the overnight
  gap at the next open.

## Gate before any increase in frequency or size

H1 moves on to frequency or size work only if, on the holdout with 1 MNQ:
- the mean net per trade is above $0 on every holdout set; and
- the pooled t-statistic is at least 2.0.

Otherwise H1 is rejected, and no larger size or added frequency is tested on it.

## Acceptance

The four targets above, on the stand-in. At 1 MNQ they are reported as measured. They are not used to pick settings.
Success is claimed only if all four pass.

## Development results (2026-10-29, before any holdout run)

All 72 settings are in `verification/noise_v2/h1_dev.csv`. Five settings met the frequency and positive-mean rule.

**Frequency:** no setting reached many trades.
- The most frequent made about 33 trades a year (L 30).
- At L 10, settings made 10-17 a year.

**Selected by the frozen rule: H1** = L 30, 09:30 entry, k 1.0, swing exit, no target. Pooled development t-statistic
1.59.

| Development set | Trades/yr | Net $/trade | t | Net win % | Breakeven win % | PF | Marked DD |
|---|---|---|---|---|---|---|---|
| NQ 2015-2019 | 33.3 | $41.68 | 0.62 | 50.8 | 47.6 | 1.133 | $12,617 |
| Index 2011-2018 | 31.2 | $75.87 | 1.53 | 52.7 | 47.0 | 1.257 | $7,413 |

**A second frozen setting, H1b, added now, before the holdout.**
- H1b = L 10, 09:30 entry, k 2.0, swing exit, 0.5 ATR target.
- It had the highest pooled development t (3.37) and the highest net win rate: 86.3% on NQ and 89.7% on the index.
  Its breakeven win rates were 79.8% and 77.6%.
- **It fails the pre-registered frequency rule:** 12.8-12.9 trades a year. So it is not the selected candidate.
- It is tested once on the holdout only because its win rate is near the 80% target. The result is reported whatever
  it shows.
- Two settings now go to the holdout, not one. Any pass will be weighed with that in mind.
