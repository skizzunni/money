# Checklist: nine native NinjaTrader runs, A / B / C × slippage 0 / 1 / 2

Purpose: isolate the breakout's components on the user's own MNQ data. Only the breakout switches and the slippage
change between runs. Nothing is tuned between runs. No filter or exit change is made until this comparison is done.

## 0. Before the first run (once)

1. **Freeze the code.** The two files in NinjaTrader must be this repository's at commit 3090622 (the latest sent):
   - `Strategies/MnqNoiseMomentum.cs`, sha256 `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3`
   - `AddOns/MnqNoiseEngine.cs`, sha256 `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7`

   To check on Windows: PowerShell, `Get-FileHash <file>`. Compile once (F5). Do not edit or recompile again until
   all nine runs are done.
2. **Make a folder** for the files, e.g. `Documents\MNQ_ABC_runs\`.
3. **Check the data.** Tools → Historical Data, instrument MNQ DEC26, Minute: data present from 8/20/2026 to
   10/16/2026. This is the same data source as the 172-trade run. Already known from that run's Output:
   - 8/31 has no 09:30 bar (missing data);
   - 9/7 (Labor Day) closes early;
   - neither counts as a full session.

## 1. Settings for all nine runs (Strategy Analyzer)

| Setting | Value |
|---|---|
| Strategy | MnqNoiseMomentum |
| Instrument | MNQ DEC26 (the same as the reference) |
| Data series | 1 Minute, trading hours "CME US Index Futures ETH" |
| **Start date / End date** | **8/20/2026 / 10/17/2026** (see "Why 8/20" below) |
| Order fill resolution | Standard (Fastest) |
| Fill limit orders on touch | Off |
| Slippage | **0, 1 or 2: the only Analyzer setting that changes** |
| Include commission | **On**: the commission template that charged $0.95 a side ($1.90 a round trip a contract) in the 9/11 runs |
| Entries per direction / Entry handling | 1 / Unique entries |
| Exit on session close | On |
| Set order quantity / Time in force | Strategy / GTC |
| Calculate | On bar close |
| Strategy parameters | All at their defaults, except the switches in section 2 and Diagnostics on |
| FUNDED ACCOUNT | Off (Evaluation; account "Backtest") |
| Contracts in an evaluation | 4 |
| Evaluation max loss, $ | 200 |
| Evaluation losers per day | 3 |
| Lock / take-profit | Defaults |
| Stop only ever tightens | On |
| Daily gate (DailyMaxLosers, DailyLossLimit) | 0, 0 (off) |
| PartialAtR | 0 (off) |
| Breakout risk in the evaluation, $ | 400 |
| Breakout most contracts / take-profit | 10 / 8 |
| Diagnostics (group 6) | **On** |

**Why 8/20, not 8/21 as proposed earlier:**
- The strategy needs 14 full sessions before it trades. 8/31 and 9/7 don't count.
- From 8/21 the 14th full session would be 9/11, so testing would start only 9/14.
- From 8/20 it is 9/10, so **the first tested session is 9/11**: 26 sessions, 9/11 to 10/16.
- My earlier 8/21 count missed those two days.
- The actual end of warm-up is whatever each run's Output says (step 4). The comparison uses the latest of the nine.

## 2. The nine runs

| Run name | "Breakout in the bot's gaps" (UseBreakout) | "Breakout shorts" | Slippage |
|---|---|---|---|
| A_S0 | On | On | 0 |
| A_S1 | On | On | 1 |
| A_S2 | On | On | 2 |
| B_S0 | **Off** | On (unused) | 0 |
| B_S1 | **Off** | On (unused) | 1 |
| B_S2 | **Off** | On (unused) | 2 |
| C_S0 | On | **Off** | 0 |
| C_S1 | On | **Off** | 1 |
| C_S2 | On | **Off** | 2 |

## 3. For each run, in this order

1. Open the NinjaScript Output window and **clear it** (right-click → Clear), so its file holds this run only.
2. Set the run's three values (table above) and check the rest against section 1.
3. Run.
4. **Output:** right-click → Save as → `<run>_output.txt`. It starts with the three "MNQ settings:" lines and ends
   with "MNQ funnel, end of run". Look at these lines:
   - "2 engine ready: ... (from <date time>)" is when warm-up finished; expected 2026-09-10 16:00;
   - "rejected 0" and "runtime errors 0".
5. **Summary:** display Summary → right-click → Export → `<run>_summary.csv`.
6. **Trades:** display Trades → right-click → Export → `<run>_trades.csv`. Every trade, with the Commission and MAE
   columns.
7. **Settings:** a screenshot of the Analyzer's settings panel, scrolled so all of it shows (two screenshots if
   needed) → `<run>_settings.png`. Or, if offered, save the settings as a template named `<run>`.
8. Check before moving on:
   - the Summary's Commission is not $0;
   - its Start date reads 8/20/2026;
   - the run name matches the switches.

Send all 36 files: 9 runs × output, summary, trades, settings. A zip of the folder is fine.

## 4. What is compared (`research/native_abc.py <folder>`), once the files arrive

**Checks first:**
- the same frozen settings in every run (apart from the switches);
- commission on every trade at $1.90 a contract;
- no rejection or runtime error;
- the end of warm-up per run.

**Eligible period:** from the first session after the latest warm-up end. Trades before it are listed and not counted.
None is expected, because nothing trades before the engine is ready.

**Per run, eligible period, after commission:**
- net and gross, commission;
- positions and contracts;
- profit factor, $ per position, average win and loss;
- closed-trade drawdown;
- an intraday estimate: closed equity before each trade less its MAE, NinjaTrader's own worst point for the trade;
- losing streak, worst day, losing days;
- each component's dollars;
- the largest five winners' share.

**Between runs:**
- **Slippage cost per configuration:** S1 − S0 and S2 − S0.
- **Changed entry opportunities:**
  - B must hold exactly A's momentum trades;
  - C must hold exactly A's trades without its breakout shorts.

  The stand-in predicts both, because the momentum bot always comes first and the breakout only trades in its gaps.
  Any difference natively is listed and explained trade by trade.

**What this comparison cannot show:**
- **These are 26 sessions, about 5 weeks.** They show how the components behaved on this stretch of MNQ, with costs.
  They do not establish an edge, and the 9/11 to 10/17 cost findings (28 trades) are not extrapolated to the full
  history or to live trading.
- **NinjaTrader's slippage setting left most stop exits unslipped in the 9/11 runs.** So these runs understate stop
  slippage. That is reported, not corrected silently.

## 5. Kept separate: the zero-trade run (8/9 to 10/17, `5feac8dc-...04-54_AM.csv`)

**Unresolved.**
- Only its summary exists: no Output, no settings, no trades.
- The code it ran is not recorded. By the times it is probably commit 5c7626a, pushed 15 minutes before the run;
  that is inferred, not confirmed.
- A run of newer code says nothing about what made the old one fail.

**To resolve it** (proposed, not started):
1. Build commit 5c7626a's two files with the diagnostics added and no other change (a separate build, not the frozen
   one above).
2. Rerun 8/9 to 10/17 with that run's settings. Those settings must come from the user: a screenshot or template, if
   one survives.
3. Send its Output and Log tab.

## 6. Status of the nine runs, and B frozen

**The nine runs are completed** (docs/REFERENCE.md section 4c), but they were started on 9/11, not 8/20, so they
cover 10/1 to 10/16 (12 sessions).

**B leads at every slippage:**

| Slippage | B net | A net | B drawdown | A drawdown | B / A longest losing streak |
|---|---:|---:|---:|---:|---|
| 1 tick | $4,646.00 | $2,433.80 | $828.00 | $2,709.20 | 3 / 7 |

The whole difference is eight breakout trades.

**B, frozen as a candidate** (no filter, exit, size or momentum-long change on this sample):
- **Code:** the two files at the sha256 in section 0.
- **Settings:** section 1's, with "Breakout in the bot's gaps" off ("Breakout shorts" is then unused).

**Still to collect for these nine runs:**
- each run's Trades export;
- the B and C runs' Output;
- the settings screenshots.

These confirm the switches and the warm-up trade by trade. The summaries already agree with them (section 4c).

## 7. Next: A and B over the longest native MNQ history (proposed; the user runs)

**Runs:** A_L1 and B_L1 (1 tick), then A_L0, B_L0, A_L2, B_L2. Section 1's settings, except Start and End.
- **Start 1/1/2026, End 10/17/2026:** the same request as the 172-trade reference.
- **Commission on.**

**What that loads** (known from the reference's Output; each run's own Output confirms it):

| Item | Value |
|---|---|
| First bar | 5/3/2026 18:01 New York (no MNQ DEC26 data before) |
| Warm-up | 5/4 to 5/21 (14 sessions); engine ready 5/21 16:00 |
| Data holes | 5/22 to 6/26 (24 sessions, no bars at all); 8/31 (no 09:30 bar) |
| Short sessions | 9/7 (Labor Day, early close; also on the skip list) |
| First tested session | 6/29 |
| Tested period | 6/29 to 10/16, about 74 sessions, July included |

**6/29 is the first session after the hole:** its "yesterday" is 5/21. Results are reported with it and, separately
and retrospectively, without it (`native_abc.py <folder> - 2026-06-29`).

**Contract:** MNQ DEC26 throughout, as in the reference. Before the 9/10 roll that is the deferred contract, not the
one an account would have traded. To check that this does not drive the result, add one more A/B pair (L1 only) on
NinjaTrader's merged series (Tools → Options → Market Data → Merge policy "Merge back adjusted", same instrument).
Report which is which.

**Files per run:** as in section 3 (output, summary, trades, settings). Name them A_L1_output.txt etc.

**Reported** (`native_abc.py`), A beside B:
- net after costs;
- monthly results, July included;
- losing streaks;
- closed-trade drawdown;
- intraday risk, estimated from each trade's MAE;
- worst day;
- components;
- slippage sensitivity.

Then the Apex 50K evaluation replay: $3,000 target, $2,000 intraday trailing loss, 30 calendar days, every start
date, overlapping and so not independent. Passes, fails and expirations are reported separately from the continuous
profit.

**If B's advantage disappears over this period, that is reported plainly, and B is not adopted.**

## 8. Then: a forward simulation, defined now (starts only after section 7)

**Accounts and code:**
- **Arms:** A and B as frozen, each on its own simulation account: "SimA" and "SimB", created in the Control Center
  under Accounts.
- **Start balance:** $50,000 each.
- **Commission:** a template of $0.95 a side assigned to both accounts.
- **Code:** the section 0 files. No edit, recompile or setting change during the test.

**Settings:** section 1's, plus:
- **Place orders on.**
- **EvalTarget 0 in both arms.** The test measures continuous performance; the evaluation's target would stop an arm
  partway.
- **FUNDED off.**
- **1-minute MNQ front-month chart per arm, same data connection.** At the December roll, both arms switch to MAR27
  after the same session's close.

**Duration:**
- **Pilot: 20 sessions.** Checks operation only: fills, stops present, flat by 16:00, Output and executions
  reconciling.
- **Decision review: after 40 sessions, and at least 60 completed positions in A.**

**Daily reconciliation:**
- each arm's Executions export and Output;
- every position has a stop from its fill;
- the account and strategy positions agree;
- every execution is explained by an Output line.

**Stop the test only for an operational fault:**
- a position without a stop;
- an execution the Output does not explain;
- a runtime error or a disabled strategy;
- an account/strategy mismatch.

It is never stopped because one arm looks better.

**Decided now:**
- **B is retained over A** only if, after 40 sessions, B's net after costs is at least A's **and** B's closed-trade
  drawdown is no larger.
- Otherwise the result is insufficient evidence, and A stays the reference.
- Either way it is a small sample. It is an operational and directional check, not proof of a live edge.
