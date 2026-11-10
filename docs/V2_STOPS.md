# v2 stops for the Noise-Area Momentum v1.5 rules (plan of 2026-11-10)

The plan: build the v1.5 rules with eval-safe stops (daily loss limit, a lock trigger in noise units, a gap guard,
tighten-only), pre-register gates, test on NQ 2015-2025, and report the $750/day question honestly. This file records
each phase as it is done. Attachments that arrived: the Pine trade log screenshot (Nov 2-9). The Pine v1.5 script used
is the user's archived file `pine/reference/mnq_noise_momentum_v1.5_user.pine`; the C# engine is
`ninjatrader/AddOns/MnqNoiseEngine.cs`. The NinjaTrader trades 229-233 screenshot did not arrive.

## Phase 0: the firm's rules (to confirm)

From Take Profit Trader's help center as read on 2026-11-05 (docs/NINJATRADER_V38.md, "The user's firm"); the user
should confirm these against the current pages:

| Rule | Test (evaluation) | PRO (funded) |
|---|---|---|
| Trailing drawdown | $2,000, **end of day** | $2,000, **intraday, including open profit**, until the floor reaches $50,000 |
| Profit target | $3,000 | none |
| Minimum days | 3 (the plan's gates use 5, stricter) | none |
| Consistency | best day under 50% of the profit | none |
| Daily loss limit | none | none |
| Automation | **not allowed**: "Automated trading systems, bots, or algorithmic execution tools are not permitted" | **not allowed**: "All trades must be manually executed by the trader" |
| Other | positions closed by 16:55; at most 60 micros | flat 1 minute either side of FOMC 14:00, NFP and CPI |

**So on this firm the bot is alert-assisted manual trading only:** NinjaTrader runs on SIM / paper, the strategy
sends the heads-up and the bracket (entry, stop, target) before each check, and the trader places every order
themselves. Bot trades must never be passed off as manual. The NinjaTrader strategies' "Place orders" switch must stay
off on a Take Profit Trader account. Since the funded account trails intraday, every gate below is run under both
end-of-day and intraday trailing.

## Phase 1: reconciliations

**(a) Pine against NinjaTrader on Nov 2-9.** The Pine log in the screenshot is **not v1.5**. It has v3.8's "Why" column
("locked win", "max loss stop", "stop at the line", "16:00 close") and sizes from 5 to 12 contracts, which v3.8's
Funded growth mode sets. In v1.5 the size is a fixed input. Reading the log row by row:
- Nov 5 has **four** Pine trades, not one: 10:30 short 7 (+$4,303.32, target), **11:00 short 10** @ 26974.25 → 11:30
  27069.50 (−$1,917.40, max loss stop), **12:00 short 8 @ 27151.25 → 27149.00 (+$26.08, locked win)**, and 12:00 short 8
  @ 27116.00 → 15:30 26743.25 (+$5,954.08, 16:00 close). The −$1,917.40 trade entered at 11:00. The 12:00 trade at
  27151.25 is exactly NinjaTrader's #229 (short 8 @ 27151.25 → 27149.00, +$26.08). **Pine and NinjaTrader agree on Nov 5
  12:00.** The plan's "divergence" set the 11:00 trade beside the 12:00 one. No data-feed, contract or warmup difference
  shows in that row. (Trades 230-233 can be checked when that screenshot arrives.)
- **The two big losses were not gaps through a stop.** Both filled about 95 points from entry: Nov 5 11:00, 26974.25 →
  27069.50 = 95.25 points on 10 MNQ; Nov 6 10:00, 27346.25 → 27250.50 = 95.75 points on 12 MNQ. Funded growth's max loss
  is **$187.50 a contract = 93.75 points**, measured from the expected fill. Both exits are that stop plus 1.5-2 points of
  slippage and fill difference. The 14.6- and 17.5-point "intended stops" in the plan are $350 ÷ qty ÷ $2, v1.5's
  setting, which this log did not use. **The stop did its job; it was 94 points away on 10-12 contracts.** So the loss
  came from size × per-contract risk, which v1.5 at a fixed 2 MNQ and its own $350 cap would not repeat. A real gap
  (a fill far past a resting stop) is still possible at the open or on news, and the gap guard and G5 measure it.

**(b) Reversals.** v1.5 reverses **only in its "Half-hour check" exit mode**. In its default, "Resting stop at the line",
it does not reverse: `inPosStop = useStop and pos != 0` skips the reverse branch, so an open trade ends only at its
stop, lock, target or 16:00. The C# engine never reverses. The Python reference (`mnqbot/noise.py`) and every
historical backtest in this repository since the resting stop (v1.1) use the resting-stop mode: **no reversals**, the
same as the C# engine. The comparisons below use that mode.

**(c) The $34/day number.** No result in this repository is "$34 a day" exactly. The nearest are the funded measures of
the 50K bot (G372 / G409 / G415 / G421): **per account, total, starting at 1 MNQ and adding a contract per $1,500 of
profit**: U48 $30.4 a session on the 16 recent 12-month starts, G421's variant D $35.1, U58 $49.2. They are not per
contract. The Pine's long-run claim of about $28 a day a contract matches round 32 (`docs/RESULTS.md`, NQ futures
2015-25 at 1 contract and a $117 max loss: $27.94 a day). The plan is right that these are to spec, not something to
"fix".

**(d) The 5-12 sizing.** In v3.8's Funded growth (Pine and NinjaTrader alike): 1 MNQ, plus one contract per $1,500 of
profit since the start date (faster above $9,000), up to 60, each trade's risk at $187.50 a contract, cut to the day's
budget and the room above the trailing floor. **On TradingView the profit is the chart's own backtest** since its start
date, so after a strong simulated history the Pine shows 10-12 contracts that no real account has earned. NinjaTrader
sizes from the smaller of the strategy's equity and the live account's (`EqEff`), so live it cannot size from
simulated profit. The plan's fixed 2 MNQ for the evaluation replaces all of this.

## Phase 3: pre-registration (written and committed 2026-11-10, before any v2 backtest)

**What is compared.** The v1.5 rules (noise lines, 14-session lookback, 12 half-hour checks, resting stop at the line
0.24 noise units past it, max loss $350 for the position, lock at 1 max loss of profit to entry + 2.5 points, 1.5-noise-
unit take-profit, 4-loser daily limit, the Fed rule, flat at 16:00, skip dates; no reversals) at a **fixed 2 MNQ**:
- **v1.5 stops:** as above.
- **v2 stops:** DailyLossLimit −$400 (a resting stop where today's closed P/L plus the open trade's P/L, after its exit
  commission, reaches −$400; then no new entries that day; also no new entries once the closed P/L is at or below
  −$400), LockTriggerNoise 0.75 (the lock arms when a bar reaches 0.75 × the current check's noise × the entry price in
  profit; the lock stop stays entry + 2.5 points), GapGuard on (a stop that fills more than 2× its intended loss distance
  from the entry ends new entries for the day), TightenOnly on (the stop only ever moves toward the price).
- **v2 grid (Phase 4):** daily limit −300 / −400 / −500 × stop buffer 0.24 / 0.35 × gap guard on / off (12 variants).

**Data and costs.** NQ futures 2015-2025, 5-minute bars, back-adjusted at the rolls and rescaled to today's price level
(`nq5m_scaled.pkl`, as every NQ result in this repository), regular hours. $0.62 a side a contract; **2 ticks** of
slippage on every market and stop fill (entry and exit sides), none on the take-profit limit.

**The evaluation replay.** Consecutive non-overlapping 30-calendar-day windows from 2015-01-05 to 2025-12-31, each a
fresh $50K evaluation at 2 MNQ under Take Profit Trader's Test rules: pass when the closed profit is at least $3,000,
the account has traded on at least 5 days and the best day is under 50% of the profit (checked at each day's end; if
the best day is too large, trading continues); fail when the balance, open trades marked at each bar's worst price,
touches the floor (the highest end-of-day balance less $2,000, at most the start); expiry when the 30 days end with
neither. **Intraday variant** (the funded account): the floor trails the highest balance *including open profit*
(bar extremes, the worst order inside a bar), stopping at the start; every gate is reported under both.

**The gates** (on the windows, 2 MNQ):
- **G1** pass rate ≥ 60%;
- **G2** expiry ≤ 15%;
- **G3** the worst window's drawdown ≤ $1,500 (largest fall of the end-of-day balance from its high within a window);
- **G4** profit factor ≥ 1.35 (all trades 2015-2025, run continuously at 2 MNQ);
- **G5** largest single-trade loss ≤ $500 (all trades 2015-2025; the gap audit lists every trade whose stop filled
  more than 2× its intended distance);
- **G6** NinjaTrader ↔ Python trade-for-trade parity of the engine, before any of the above counts.
MNQ (the user's 2026 bars) is reported separately as an execution check, not a gate.

**Selection.** At most one variant: among v1.5 and the 12 v2 variants, those passing G1-G6 under end-of-day trailing
(the evaluation's rule), the highest pass rate (ties: the smaller G3). Intraday results are reported beside it.
**Kill criteria:** if the selected v2 variant does not beat v1.5's pass rate (G1), or v2 fails G5, the v2 stops are
rejected and the answer is "size + daily limit only", with no further stop tuning on this data.

**The tight-stop grid** (reported, not selected on): max loss cap $100 / $200 / $350 × line buffer 0.10 / 0.24 / 0.35 at
2 MNQ with v1.5's lock (1 max loss): $ a day a contract, max drawdown a contract (end-of-day), profit / drawdown, win
rate, profit factor, 2015-2025. **Separation:** (i) cap $100 / $200 / $350 with the lock trigger fixed at 0.75 noise
units; (ii) cap fixed at $350 with the lock trigger at the points the $100 / $200 / $350 caps imply under v1.5 (25 /
50 / 87.5 points at 2 MNQ). If the long run refutes the $100 cap, $350 stays.

**Phase 4b.** For the selected variant (v2 defaults if none is selected): $ a day and max drawdown at 1, 2, 3, 5 and 8
MNQ, and whether any size reaches $750 a day with max drawdown under $2,000. Then the noise + Williams combination
(both sleeves, one shared risk budget): $ a day, drawdown and profit / drawdown against noise-only v2; if it does not
beat noise-only's ratio, no sizing up.

## Phase 2: the engine (done)

`ninjatrader/AddOns/MnqNoiseEngine.cs` `NoiseSettings`: **DailyLossLimit** −400 (0 = off), **LockTriggerNoise** 0.75
(0 = LockAt in max losses), **GapGuard** true, **TightenOnly** true, as the plan's defaults. The Python reference
(`mnqbot/noise.py`): `dll_v2`, `lock_noise`, `gap_guard`, `tighten_only` (off by default, as every other research
setting). The strategies built on the engine before v2 (Runner, C, D) keep v1.5's stops explicitly (`V15Stops()`).
`MnqNoiseMomentum.cs` runs the engine with v1.5's stops: its own order management does not place the daily limit's
stop, so after the rejection the v2 settings were taken off it rather than left half working (see the MNQ check). On the fill bar the
daily limit's stop is measured from the expected fill, as the max-loss stop's is (a bracket sent with the entry).
**G6, parity: passed.** The engine and the Python model agree trade for trade (`tests/test_ninjatrader.py`: the v2
settings on random and gapped sessions, a tighter daily limit at 6 MNQ, a $100 cap; every v2 stop shown to act); all
152 NinjaTrader tests pass. **Pine v1.6 is not built:** the v2 stops were rejected (below), so it would carry rules
that lost on the gates; it can be written on request.

## Phase 4: results (NQ 2015-01 to 2025-07, 127 windows of 30 days, 2 MNQ, run once)

`research/v2_stops_eval.py`; files `verification/noise_v2/v2_stops_*.csv`. Closures, half days and sessions with
missing data are skipped, as in every NQ result here (a first run without them held a Black Friday trade over the
weekend into the monthly rescaling, −$5,518; that run was discarded before any comparison).

**v2 against v1.5, the gates** (end-of-day trailing; intraday in brackets):

| Variant | G1 pass ≥60% | G2 expiry ≤15% | fail | G3 worst window DD ≤$1,500 | G4 PF ≥1.35 | G5 largest loss ≤$500 |
|---|---|---|---|---|---|---|
| **v1.5 stops** | **13.4%** (11.8%) | 67.7% | 18.9% (37.0%) | $2,648 | 1.267 | −$397 |
| v2 −300 / 0.24 / gap on | 6.3% (5.5%) | 79.5% | 14.2% (29.1%) | $2,121 | 1.246 | −$377 |
| v2 −300 / 0.35 / gap on | 6.3% (6.3%) | 80.3% | 13.4% (24.4%) | $2,127 | 1.252 | −$377 |
| v2 −400 / 0.24 / gap on (defaults) | 7.1% (6.3%) | 74.0% | 18.9% (31.5%) | $2,218 | 1.278 | −$377 |
| v2 −400 / 0.35 / gap on | 8.7% (7.9%) | 72.4% | 18.9% (31.5%) | $2,269 | 1.274 | −$377 |
| v2 −500 / 0.24 / gap on | 12.6% (9.4%) | 70.9% | 16.5% (37.0%) | $2,366 | 1.283 | −$382 |
| v2 −500 / 0.35 / gap on | 11.8% (9.4%) | 68.5% | 19.7% (34.6%) | $2,174 | 1.275 | −$377 |

The gap guard off changes one or two trades in ten years in every pair (same pass rates): real gaps past a stop are
rare in regular hours. **No variant passes G1, G2, G3 or G4; all pass G5 and G6.** At 2 MNQ the rules make about $41-48
a day, about $1,000 in 30 days, so two windows in three expire short of $3,000.

**Selection: none. Kill criteria met:** the best v2 variant (12.6%) does not beat v1.5 (13.4%) on G1, so **the v2 stops
are rejected**; the answer is size + a daily limit, with no further stop tuning on this data.

**Context, not pre-registered:** Take Profit Trader's Test has no time limit. Run from the same starts until pass or
fail (116 starts to mid-2024): v1.5 passes **53.4%** end-of-day (38.8% intraday), v2 −400 41.4% (33.6%), v2 −500
50.9% (33.6%). The v2 stops lower the pass rate there too.

**The tight-stop grid** (2 MNQ, v1.5 lock, per contract, 2015-2025):

| Cap / buffer | $/day/contract | max DD/contract | profit/DD | win | PF | worst day/contract |
|---|---|---|---|---|---|---|
| $100 / 0.10 | 8.23 | 3,106 | 7.2 | 42.5% | 1.150 | −228 |
| $100 / 0.24 | 8.38 | 3,023 | 7.5 | 43.6% | 1.152 | −228 |
| $100 / 0.35 | 8.30 | 3,026 | 7.5 | 43.7% | 1.150 | −228 |
| $200 / 0.10 | 16.48 | 3,933 | 11.4 | 46.7% | 1.223 | −413 |
| $200 / 0.24 | 19.07 | 4,318 | 12.0 | 50.0% | 1.256 | −413 |
| $200 / 0.35 | 19.47 | 3,858 | 13.7 | 50.8% | 1.258 | −413 |
| $350 / 0.10 | 21.54 | 3,123 | 18.8 | 42.6% | 1.248 | −740 |
| **$350 / 0.24 (v1.5)** | **23.88** | 3,349 | **19.4** | 47.6% | 1.267 | −740 |
| $350 / 0.35 | 23.40 | 3,486 | 18.3 | 49.2% | 1.256 | −740 |

**The long run refutes the $100 cap:** a third of the money ($8.38 against $23.88 a day a contract) and less than half
the profit / drawdown (7.5 against 19.4). Idris's 20-day result (cap $100 best, ratio 3.80) does not hold over ten
years; **$350 stays**. The tight line (0.10) is worst at every cap, as in his sample.

**Separating the two effects:**

| Held fixed | Varied | $/day/contract | max DD/contract | profit/DD | win |
|---|---|---|---|---|---|
| lock 0.75 noise | cap $100 | 9.86 | 2,773 | 9.7 | 24.1% |
| lock 0.75 noise | cap $200 | 19.07 | 5,239 | 9.9 | 36.9% |
| lock 0.75 noise | cap $350 | 23.73 | 4,165 | 15.5 | 45.4% |
| cap $350 | lock at 25 points (the $100 cap's) | 18.82 | 2,958 | 17.3 | 64.9% |
| cap $350 | lock at 50 points (the $200 cap's) | 22.26 | 3,837 | 15.8 | 58.3% |
| cap $350 | lock at 87.5 points (v1.5's) | 23.88 | 3,349 | 19.4 | 47.6% |

(The run's labels for the last three say 50 / 100 / 175 points, a label slip; the triggers run were 25 / 50 / 87.5 as
registered.) **The $100 cap's loss comes from the tighter stop:** with the lock held fixed, the $100 cap still makes
under half. The earlier lock raises the win rate (47.6% → 64.9%) but lowers $/day; neither effect pays on ten years.

## Phase 4b: $750 a day

**$ a day and max drawdown by size** (2015-2025, end-of-day, the whole history; the $350 cap and the −$400 limit are
for the whole position, as the rules define them):

| Size | v1.5 stops: $/day | max DD | worst day | v2 defaults: $/day | max DD | worst day |
|---|---|---|---|---|---|---|
| 1 MNQ | 29.34 | 3,069 | −1,052 | 26.74 | 3,108 | −408 |
| 2 MNQ | 47.76 | 6,698 | −1,479 | 41.23 | 7,763 | −445 |
| 3 MNQ | 59.07 | 10,003 | −1,439 | 44.75 | 11,509 | −468 |
| 5 MNQ | 59.21 | 17,631 | −1,519 | 35.06 | 13,182 | −513 |
| 8 MNQ | 65.94 | 23,091 | −1,628 | 40.99 | 17,697 | −524 |

**No size reaches $750 a day, and none keeps the drawdown under $2,000** (even 1 MNQ's ten-year drawdown is about
$3,100). With a whole-position cap, more contracts mean a tighter stop for each, so $/day stops growing. With the cap
scaled per contract ($175 each), $/day grows in proportion (about $24 a contract) and so does the drawdown (about
$3,350 a contract): $750 a day needs about 31 contracts and a drawdown near $105,000. The plan's arithmetic holds: the
profit / drawdown this needs is far beyond the strategy's.

**Noise + Williams on one account** (`research/v2_combo.py`; one position at a time, a shared −$400 daily limit,
Williams at $200 risk, 1-10 MNQ, on the same 5-minute bars):

| | $/day | max DD | profit/DD | PF | worst day |
|---|---|---|---|---|---|
| noise-only v2, 2 MNQ | 41.23 | 7,763 | 14.4 | 1.278 | −445 |
| Williams only | 21.62 | 3,599 | 16.3 | 1.375 | −577 |
| **noise v2 + Williams** | **43.23** | **5,990** | **19.6** | 1.291 | −695 |

The combination beats noise-only's ratio (19.6 against 14.4): a little more money, a smaller drawdown. It does not
change the $750 answer: at its ratio $750 a day needs about 17 times the size and a drawdown of about $100,000. (The
shared limit gates new trades; a Williams trade open when the day passes −$400 runs to its own stop, so its worst day
is −$695.)

## What this means

- **The v2 stops are rejected** under the kill criteria. Keep v1.5's stops: the $350 cap at 2 MNQ, the line at 0.24,
  the lock at 1 max loss.
- **Size: 2 MNQ**, fixed. A daily loss limit caps the worst day (−$1,479 → about −$445 at −$400) but costs pass rate in
  every measure here, so on the Test it is a choice of steadier days over passing sooner, not a free improvement.
- **Do not let the Pine's growth sizing set live size.** The −$2,313 and −$1,917 days were 94-point stops on 10-12
  contracts.
- **$750 a day is not reachable** with these rules on one $50K account at any size that survives the $2,000 drawdown.
- Phase 5 (native NinjaTrader on SIM, two weeks of alert-assisted paper trading before any funded attempt) applies to
  v1.5 at 2 MNQ: `MnqNoiseMomentum.cs` with Qty 2, MaxLoss 350 and the v2 settings at 0, in alerts-only mode on a
  Take Profit Trader account.

## Phase 5: the MNQ execution check and NinjaTrader

On the user's MNQ bars (6/29-10/16/2026, 1-minute, traded from 7/20, 65 sessions; `MnqNoiseMomentum.cs` on the
simulator against the Python model, 2 MNQ, $350, 4 losers, $0.62 a side, 2 ticks):
- **v1.5 stops:** 65 Python trades, 64 NinjaTrader. Two fill-bar stops exit a tick apart ($1 each), and on 9/16 (a Fed
  day, three losing longs) NinjaTrader skips the third long at 12:30 (−$80.48 in the model). +$5,758.80 in the model,
  **$44.30 a day a contract**, worst day −$987, largest loss −$354. Not trade-for-trade at these settings (the repository's
  parity test, frozen B at 4 MNQ and $200, is exact); an open item for Phase 5 before any funded attempt.
- **v2 defaults:** the strategy did not place the daily limit's stop (trades ran to −$354 where the model's limit closed
  them), so its v2 settings were removed; the engine keeps them with its parity.

**What runs:** v1.5 at 2 MNQ, `MnqNoiseMomentum.cs`, in alerts-only mode on a Take Profit Trader account (the firm bans
automation), on SIM for at least two weeks first. The 1-tick and Fed-day differences above should be closed before
it is trusted trade for trade.

# v3 (plan of 2026-11-10, second): parity fixes, the no-time-limit gates, the combination, PRO

**Rules confirmed against this file before anything ran:** the user's list (Test: $2,000 end-of-day trail, $3,000 target,
at least 3 days, best day under 50%, no daily limit; PRO: intraday trail including open profit; automation banned)
matches Phase 0 above. No conflict, so the gates below stand.

## v3 pre-registration (written and committed 2026-11-10, before any v3 result)

**Rules:** v1.5 (Phase 3's list) at a fixed size, its stops ($350 for the position, line 0.24, lock 1 max loss, take-profit
1.5, 4 losers). NQ Jan 2015 - Jul 2025, 5-minute, the closures and holes skipped, $0.62 a side, 2 ticks on market and stop
fills (`research/v2_stops_eval.py`'s data and costs).

**The evaluation replay, no expiry:** a fresh $50K Test started every 30 calendar days from 2015-02-02 to 2024-07-22 (one
year before the data ends), each run until it passes or fails: pass at the first day's end with closed profit ≥ $3,000,
at least 3 trading days and the best day under 50% of the profit; fail when the balance, open trades marked at each bar's
worst price, touches the floor (the highest end-of-day balance less $2,000, at most the start). A start still open when
the data ends counts as not passed (reported).

**Gates (1, 2 and 3 MNQ each):** **G1** pass rate ≥ 60% (v1.5 at 2 MNQ measured 53% with 5 minimum days); **G2** median
trading days to pass, reported (target ≤ 75); **G3** worst end-of-day drawdown inside an evaluation, reported; **G4**
profit factor ≥ 1.35 (all trades, run continuously); **G5** largest single-trade loss ≤ $500; **G6** NinjaTrader ↔
Python trade-for-trade parity first (Fix 1, on the user's 2026 MNQ bars at 2 MNQ).

**The v3 candidate, noise + Williams** (`research/v2_combo.py`'s Williams: levels at the open ± half of yesterday's
range, first side only, stop a quarter of the range from the fill, out at the close, entries to 15:00) **at 2 MNQ, the
same size as noise**, one position at a time (the first entry owns the account until flat), and the day's 4-loser limit
counting both sleeves' losers (one shared risk budget). Run through the same replay against noise-only.
**Selection:** the combination is adopted only if it passes G1, G4, G5 (and G6 for its NinjaTrader build) at a size where
noise-only does not pass, or makes a higher G1 than noise-only at the same size with G4 and G5 passing. Otherwise it is
rejected and v1.5 stays. Pine v1.6 is built only if it is adopted.

**PRO (reported, no default changes):** from the same starts, 12 months (252 sessions) on a funded account with the
intraday trail including open profit (bar extremes, the worst order: the bar's best mark raises the floor first), the
floor stopping at the start: the share of starts that survive, and the median balance gain at 12 months, for v1.5 at
2 MNQ and with the daily loss limit (the engine's guard: a stop where today's P/L reaches it, then no entries) at
−$300 / −$400 / −$500.

**The expected path at 2 MNQ (V3.4):** $ a day and the median days to $3,000 from the replay; no further sizes.

## v3 Fix 1: NinjaTrader ↔ model parity on the 2026 MNQ bars, 65 of 65

v1.5 at 2 MNQ ($350, 4 losers, no tighten-only, $0.62 a side, 2 ticks), 1-minute bars 7/20-10/16/2026. Before: 62 of 65.
- **(a) The Fed-day trade (9/16 12:30): NinjaTrader was wrong.** Not a Fed-rule difference (it was a long; longs are allowed
  before 14:00). The 11:00 long's stop filled at the broker at 12:22 (29467.00, its order on the tick grid). The
  strategy's engine models the stop at the unrounded line (29465.76) and so kept "holding" the trade until 13:01; at the
  12:30 check it reported "in a trade" and the entry was skipped, though the account was flat. The model (the account's
  view) was right. **Fix:** the engine follows the account. When the account is flat and the engine still holds the
  bot's trade, the account's exit price (its last closed trade) closes the engine's trade before the next bar's stops
  and check (`NoiseEngine.ExternalFlat`).
- **(b) The two exits a tick apart: a rule difference, not rounding or order timing.** Both were fill-bar stops set by
  the line. The bracket sent with the entry is a distance from the *expected* fill (the signal close ± slippage). The
  strategy never set the engine's slippage, so it used its default 1 tick while the platform and the model used 2; the
  bracket came out a tick short of the model's whenever the line set it. (Under frozen B the $200 cap, a fixed 25 points,
  always set the bracket, which hid this.) **Fix:** the engine takes NinjaTrader's own `Slippage` setting (at least a
  tick), the one its fills use.
- **G6 re-run: 65 of 65 trades identical** (direction, entry and exit bar, prices, P/L), kept as
  `tests/test_parity_mnq.py::test_v15_two_mnq_trade_for_trade`; the frozen-B parity and all NinjaTrader tests still pass.

## v3 Fix 2: the stop-placement check

`MnqNoiseMomentum.cs` now logs every stop it sends ("MNQ stop placed: ...") and at every bar close checks the open
position: it must have a live stop (the platform's own report of the stop order when it gives one; else the stop the
strategy sent), and no stop the engine defines may be tighter than that order (beyond two ticks and the fill
difference). A failure prints and alerts "STOP CHECK FAILED ... Put a stop in by hand now." The run's audit line counts
placements and flags.

| Run | Stop placements | Flagged |
|---|---|---|
| v1.5 at 2 MNQ, the 2026 MNQ bars (as shipped) | 5,330 | **0** |
| synthetic sessions, bot and breakout, evaluation and funded | logged for every trade | **0** |
| the broker cancels a stop mid-trade (test) | | 1 (that bar) |
| **the v2 daily limit switched back on in a throwaway build** (the bug found in v2) | 5,140 | **153**: "the engine's stop 28686.51 (Day guard) is tighter than the live order 28749.00: a defined stop was not placed" |

So the check finds exactly the v2 bug, and finds nothing in the shipped strategy. (A first version of the check flagged
3 trades in 106 for a lock reached on the fill bar; that was the check's own ordering, which overwrote the moved stop
with the entry bracket. Fixed before these numbers.)

## v3 results (run once, 2026-11-10; `research/v3_eval.py`, `verification/noise_v2/v3_*.csv`)

**The Test, no time limit** (116 starts every 30 days, Feb 2015 - Jul 2024; none left open when the data ended):

| | Size | G1 pass ≥60% | fail | G2 median days to pass | G3 worst DD | G4 PF ≥1.35 | G5 largest loss ≤$500 | $/day |
|---|---|---|---|---|---|---|---|---|
| noise-only | 1 MNQ | **87.1%** | 12.9% | 100 | $2,685 | 1.315 | −$366 | 29.34 |
| noise-only | **2 MNQ** | **53.4%** | 46.6% | **39** | $3,665 | 1.267 | −$397 | **47.76** |
| noise-only | 3 MNQ | 39.7% | 60.3% | 28.5 | $5,791 | 1.249 | −$421 | 59.07 |
| noise + Williams | 1 MNQ | 75.0% | 25.0% | 69 | $2,346 | 1.346 | −$577 | 37.72 |
| noise + Williams | 2 MNQ | 50.9% | 49.1% | 33 | $7,497 | 1.315 | −$1,154 | 66.17 |
| noise + Williams | 3 MNQ | 34.5% | 65.5% | 21 | $5,458 | 1.312 | −$1,732 | 91.08 |

- **No row passes every gate.** G4 (profit factor 1.35) fails everywhere (noise 1.25-1.32); the strategy's edge is
  real but thin per trade.
- **The combination is rejected.** It makes a lower pass rate than noise-only at every size (75.0% vs 87.1%, 50.9% vs
  53.4%, 34.5% vs 39.7%) and fails G5 at every size: a Williams stop is a quarter of yesterday's range, often 50-90
  points, so a 2-MNQ Williams loser reaches −$1,154. **v1.5 stays; Pine v1.6 is not built.**
- **Size decides the Test.** 1 MNQ passes 87% of starts but takes a median 100 trading days; 2 MNQ passes 53% in a
  median 39; 3 MNQ 40% in 28.5. With no deadline, the smaller size is much more likely to pass.

**PRO, 12 months at 2 MNQ** (intraday trail including open profit, stopping at the start; 116 starts):

| Daily limit | Survived 12 months | Median 12-month gain, all | Median gain, survivors | Worst day |
|---|---|---|---|---|
| none (v1.5) | **35.3%** | −$72 | $12,269 | −$1,479 |
| −$300 | 31.0% | −$83 | $13,610 | −$345 |
| −$400 | 31.9% | −$72 | $12,079 | −$421 |
| −$500 | 31.0% | −$119 | $12,069 | −$541 |

PRO's intraday trail is much harder than the Test's: at 2 MNQ about one funded account in three lasts a year. A daily
limit caps the worst day but lowers survival at every level, so it is not added.

**The expected path at 2 MNQ (V3.4):** $47.76 a day on average (all sessions, 2015-2025); $3,000 at that rate is about
63 trading days. Among the evaluations that pass, the median is 39 trading days (the ones that pass are the ones that
start well).

## The selected configuration

**v1.5's rules and stops, fixed size, no daily limit, no Williams**, in `MnqNoiseMomentum.cs` with Fix 1 and Fix 2,
alerts-only on Take Profit Trader. On size: the gates were registered at 1, 2 and 3 MNQ and none passes G4, so none is
"selected" by them; at 2 MNQ (the size asked for) the Test passes about half the time, and at 1 MNQ about 87% of the
time, more slowly. That choice is the user's.
