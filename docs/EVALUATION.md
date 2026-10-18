# Frozen B in the $50K intraday-trail evaluation: 4 MNQ / $200 against 2 MNQ / $100 (October 18, 2026)

Each result is labelled **executed**, **proposed** or **unavailable**.

## 1. The account's rules - from third-party summaries; Apex's own pages unavailable from here

Apex's help center and site return a Cloudflare block (403) to this environment, so the rules could not be read at
the source. The rules below are from third-party summaries of the program rebuilt on March 1, 2026; they disagree on
three points.

| Rule | Used | Status |
|---|---|---|
| Start balance | $50,000 | agreed |
| Profit target | $3,000 (pass at $53,000) | agreed |
| Trailing drawdown | $2,000 below the highest equity so far, unrealized peaks included, moving up at once | agreed for the 2026 50K intraday evaluation (the legacy 50K was $2,500) |
| Where the trail stops | Not needed: the threshold cannot reach any stop level before the target is reached | sources conflict (profit target level for Rithmic, none for Tradovate, or start + $100 on funded accounts) |
| Time | 30 calendar days from the start | stated by several sources for the one-time-fee evaluation |
| Daily loss limit | None. Sensitivity: a $1,000 limit that closes and pauses the day without failing | **conflicting** (none, or $1,000 on the intraday variant) |
| Minimum trading days | None. Passes before the 7th session are counted separately | **conflicting** (none, or 7 in an older guide) |
| Contract limit | 6 minis / 60 micros; 4 or 2 MNQ is within it | most sources |
| Fees | $0.95 a side a contract (provisional: the rate in the user's exports); the evaluation's price is not part of the result | - |

**Before relying on any of this,** confirm on the account's own dashboard or Apex's help center:
- the trailing amount;
- the time limit;
- whether the intraday account has a daily loss limit;
- whether there is a minimum number of trading days.

## 2. What was simulated - executed (stand-in, rescaled data; not the user's MNQ bars)

**Strategy:** frozen B (UseBreakout off; every other setting at its default). Two sizes, each a complete rerun:
- 4 MNQ with a $200 max loss a trade;
- 2 MNQ with a $100 max loss a trade.

Both caps are 25 points ($200 / 4 / $2 = $100 / 2 / $2). The lock (1 cap of profit, then entry + 2.5 points), the
take-profit (1.5 noise units), the losers limit (3), and partial exits (off) are identical.

**Executed check:**
- At 1 and 2 ticks, the 2-MNQ run has the same entries, exits and prices as the 4-MNQ run, at exactly half the
  dollars.
- The size changes nothing but the dollars.

**Costs:** $0.95 a side; slippage 1 and 2 ticks on every market and stop fill. The stand-in slips every stop,
unlike NinjaTrader's setting.

**Data:**
- NQ futures 2015-03 to 2025-06 (2,662 sessions).
- The NSXUSD index 2025-07 to 2026-09 (323 sessions).
- Both rescaled each month to today's level. Sessions with missing minutes get no new trades: 91 and 52 sessions,
  a retrospective data-quality exclusion.
- **The user's MNQ bars are not here,** so this is not a native result. A native replay needs the bars (section 5).

**Warm-up:** the strategy's 14 full sessions come before the first evaluation. Evaluations start from 2015-03-20 and
2025-07-24.

**Each evaluation, chronologically from its start session:**
- Equity is followed minute by minute through every open position:
  - closed P/L;
  - plus open P/L at each bar's high and low (a stop exit's worst point is its fill, a take-profit's best is its fill,
    a market exit is its fill);
  - commission charged at each fill.
- **Breach:** equity at or below the highest equity so far less $2,000.
- **Pass:** the strategy's own evaluation-target close (on by default, live): everything closes once closed + open
  profit reaches $3,025 (filled a tick through), or a close leaves $3,000+ closed.
- **Expiry:** 30 calendar days without either.
- The evaluation stops at the first of these.

**Minute-bar sequencing:**
- A bar does not show whether its high or low came first, so every bar was taken both ways. In the "worse" order the
  high comes first, so the peak rises, then the low is tested against it. In the "better" order the low is tested
  against the earlier peak, and a pass counts first.
- **No evaluation changed outcome or day between the two orders.** Doing so needs a single minute to make a new peak
  and fall $2,000 from it, or to touch both the target and the trail: about 250 points in one minute at 4 MNQ, 500
  at 2 MNQ.
- The remaining sequencing assumption is inside the trades: when one bar reaches both a trade's stop and its
  take-profit, the stand-in fills the stop (the conservative choice).

**Windows:**
- **Overlapping:** one evaluation starting at every session. Consecutive windows share up to 29 of 30 days, so these
  are not independent trials: roughly one independent window a month.
- **Back to back:** the next evaluation starts the session after the previous one ends. These do not overlap, but
  they are few.
- Windows whose 30 days run past the data are "unresolved".

## 3. Results - executed

**NQ 2015-2025 (rescaled), 2,648 start dates (overlapping):**

| Case | Pass | Fail | Expired | Unresolved | Median days to pass / fail | Intraday DD of passes, median / max |
|---|---:|---:|---:|---:|---|---|
| 4 MNQ / $200, 1 tick | 831 (31.6%) | 1,596 (60.7%) | 203 (7.7%) | 18 | 11 / 14 | $1,288 / $1,993 |
| 4 MNQ / $200, 2 ticks | 793 (30.2%) | 1,640 (62.4%) | 196 (7.5%) | 19 | 11 / 13 | $1,307 / $1,980 |
| 2 MNQ / $100, 1 tick | 202 (7.7%) | 386 (14.7%) | 2,039 (77.6%) | 21 | 21 / 22 | $819 / $1,954 |
| 2 MNQ / $100, 2 ticks | 182 (6.9%) | 407 (15.5%) | 2,038 (77.6%) | 21 | 22 / 22 | $824 / $1,992 |

**Back to back on NQ:**

| Case | Evaluations | Pass | Fail | Expired |
|---|---:|---:|---:|---:|
| 4 MNQ, 1 tick | 259 | 79 | 161 | 18 |
| 4 MNQ, 2 ticks | 259 | 76 | 166 | 16 |
| 2 MNQ, 1 tick | 134 | 11 | 22 | 100 |
| 2 MNQ, 2 ticks | 133 | 9 | 23 | 100 |

**Index 2025-07 to 2026-09 (rescaled), 306 start dates (overlapping):**

| Case | Pass | Fail | Expired | Unresolved | Median days to pass / fail |
|---|---:|---:|---:|---:|---|
| 4 MNQ / $200, 1 tick | 68 (22.7%) | 186 (62.0%) | 46 (15.3%) | 6 | 10 / 15 |
| 4 MNQ / $200, 2 ticks | 56 (18.7%) | 201 (67.0%) | 43 (14.3%) | 6 | 9 / 16 |
| 2 MNQ / $100, 1 tick | 10 (3.5%) | 12 (4.2%) | 264 (92.3%) | 20 | 17.5 / 28 |
| 2 MNQ / $100, 2 ticks | 10 (3.5%) | 12 (4.2%) | 264 (92.3%) | 20 | 17.5 / 28 |

Back to back on the index: 4 MNQ 5 pass / 15 fail / 4 expired (both slippages). 2 MNQ 1 / 1 / 12.

**Sensitivities:**
- **A $1,000 daily pause:** identical results in every case. B's worst day never reached −$1,000: three losers at
  4 MNQ is about −$620.
- **No minimum trading days:**
  - 315 of the 831 NQ passes at 4 MNQ, 1 tick came before the 7th session (29 of 68 on the index).
  - 21 of 202 at 2 MNQ (0 on the index).
  - If a 7-day minimum applied, those evaluations would have had to keep trading; that is not simulated here.
- **Profit while continuous** (no evaluation stops):
  - NQ: 4 MNQ $112,267 at 1 tick and $92,934 at 2; 2 MNQ $56,133 and $46,467.
  - Index 15 months: 4 MNQ $1,960 / $1,042; 2 MNQ $980 / $521.

## 4. What this shows, and what it does not

**Halving the size does not improve the odds of passing against failing.**
- At 4 MNQ, passes to failures are about 1 : 1.9 on NQ and 1 : 2.7 on the index.
- At 2 MNQ they are about 1 : 1.9 and 1 : 1.2. The latter rests on only 22 resolved windows.

**Smaller size mostly turns both outcomes into expiries.**
- Equity moves half as fast, so the $3,000 target and the $2,000 trail are both twice as far away in the strategy's
  own terms.
- In 30 days most evaluations reach neither: 78% expire on NQ, 92% on the index.

**Its time to pass roughly doubles:** a median of 21 days against 11.

**Per evaluation started, 2 MNQ passes about a quarter as often:** 7.7% against 31.6% on NQ, 3.5% against 22.7% on
the index.

So for this account (a fixed target, a fixed trail, 30 days):
- **2 MNQ / $100 is not a fix.** It fails less often only because it rarely finishes.
- Under these rules and on this data, it lowers the chance of passing any one evaluation.
- If the account had no time limit, the comparison would change. That would need re-running with the actual terms.

**At 4 MNQ the evaluation fails more often than it passes,** on both datasets and both slippages: 60-67% of start
dates fail. The continuous profit says nothing about surviving the evaluation.

**The intraday drawdown of passing evaluations reached $1,980-1,993 at its worst:** passes that came within a few
dollars of the trail.

**Not shown:**
- **The user's MNQ bars.** The native MNQ period is 77 sessions; fewer than 50 evaluations would fit, all
  overlapping.
- **The account's confirmed rules** (section 1).
- **Live fills.** Backtest slippage is an assumption; the stand-in and NinjaTrader apply it the same way (docs/MNQ_NATIVE.md).

## 5. Native replay on the user's MNQ - proposed

1. Tools → Historical Data → export MNQ DEC26 (1 Minute, Last) from 5/3/2026 to 10/16/2026.
2. Send the file.

The same simulator then replays B at both sizes on those exact bars:
- from 6/29 (warm-up before);
- with the data hole of 5/22 to 6/26 disclosed;
- checked trade by trade against the B_L1 / B_L2 runs already rebuilt from the fills.

Sources (third-party summaries; Apex's pages could not be fetched from here):
- https://fundedprogram.com/apex-trader-funding-review/
- https://traderssecondbrain.com/guides/apex-trader-funding-review
- https://il.ly/blog/apex-trader-funding-rules
- https://phidiaspropfirm.com/education/apex-trailing-drawdown
- https://quantcrawler.com/learn/apex-trader-funding-rules
- https://www.luxalgo.com/prop-firms/apex-trader-funding/
- https://support.apextraderfunding.com/hc/en-us/articles/31519769997083-Evaluation-Rules (not reachable from here)
- https://apextraderfunding.com/help-center/evaluation-accounts-ea/legacy-evaluation-rules/ (not reachable from here)
