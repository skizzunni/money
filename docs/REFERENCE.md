# The 172-trade reference run, costs, data coverage and candidates A / B / C (October 18, 2026)

Each result is labelled **executed** (run here, files named), **proposed** (procedure given, not run) or
**unavailable** (needs NinjaTrader or data not here).

## 1. The reference, frozen and reconciled - executed

**What was run**:
- **Run:** NinjaTrader Strategy Analyzer, MNQ DEC26, 1-minute bars, requested 1/1/2026 to 10/17/2026.
- **Code:** commit 3fa7bdd, identified from the settings lines it printed (they include Diagnostics and do not
  include the later "shorts" field).
  - Strategy file sha256 `60880d49edc3463f98c52bf6595fa1f0964bfc1c6ad5182df600cb71631d523b`.
  - Engine file sha256 `8910702ebecf9cb5de92d3549d36c15cfd706cc72bbb9ddd7f54c7ee6bf8bed7`.
  - This assumes the files sent were installed unchanged. NinjaTrader does not report a hash, so this cannot be
    confirmed from the run.

**Settings as printed by the run** (`verification/reference_172/ninjascript_output.txt`, first three lines):
- account Backtest, Evaluation (set by the FUNDED switch);
- 4 MNQ, $200 max loss, 3 losers;
- Lookback 14, DailyLossLimit 0, DailyMaxLosers 0, PartialAtR 0, TightenOnly on;
- breakout on with $400 risk;
- EvalTarget and PayoutStop both off in history;
- Calculate On bar close, trading hours "CME US Index Futures ETH", platform time zone Eastern.

**Analyzer settings** (from the user's screenshot):
- order fill resolution Standard;
- fill limit orders on touch off;
- slippage 0;
- 1 entry per direction, unique entries;
- exit on session close on;
- quantity "Strategy", GTC.

Commission was $0, so commissions were not applied in that run (inferred from the export).

**Rebuilt from the run's own 344 execution lines** (`research/nt_reference.py`; trades in
`verification/reference_172/reference_172_trades.csv`, output in `reconciliation.txt`):

| Measurement | Rebuilt | NinjaTrader summary |
|---|---:|---:|
| Completed trades (= positions: no partial exits) | 172 | 172 |
| Profit (no commission, no slippage) | $10,966.50 | $10,966.50 |
| Commissions / slippage | 0 / 0 | $0.00 / 0 |
| Closed-trade drawdown | $4,649.50 | $4,649.50 |
| Longest losing streak | 10 | 10 |
| Days with trades / losing days | 62 / 38 | - |
| Round-trip contract units | 606 | - |
| Funnel: submitted / accepted / filled / completed; rejected; runtime errors | 172 / 172 / 172 / 172; 0; 0 | - |

**Against the previous 83-trade export**:
- All 83 previous trades reappear with the same entry time, entry and exit prices, contracts and profit before
  commissions.
- 82 of them also have the same exit time. The 9/21 10:01 long's take-profit fill is stamped 10:27 here and 10:25 in
  the earlier export, at the same price. **This is unresolved.** The likeliest cause is re-downloaded bars, which
  needs the bars to check.
- Those 83 trades made $9,499.00 before commissions. The earlier report showed $8,906.20 after $592.80 of commission.
- The other 89 trades made $1,467.50:
  - 88 of them traded before the previous run's first trade (June 29 to August 27): +$1,617.50.
  - One is new inside the old window: 9/16 12:31 long, −$150.
- $9,499.00 + $1,467.50 = $10,966.50.

**The headline rose because the test period was longer and commission was dropped. It is not evidence that the
strategy improved on the trades the two runs share.**

**The new 9/16 trade is a code change, not data:**
- In this version the bot's daily loser limit counts the account's fills (docs/VERIFICATION.md section 10).
- On 9/16 the engine's model had the 11:31 long as a −$207 loser. Its real fill survived and made +$20 (the stop
  sat at the minute's exact low).
- The old code saw 3 losers by 12:13 and blocked the 12:31 entry. The new code saw 2 and took it, which lost $150.

**Components** (before costs):

| Component | Trades | Contracts | Profit |
|---|---:|---:|---:|
| Momentum long | 52 | 208 | +$7,540.00 |
| Momentum short | 68 | 272 | +$6,340.00 |
| Breakout long | 25 | 66 | +$866.50 |
| Breakout short | 27 | 60 | −$3,780.00 |

**Concentration:**
- The five largest winners made $10,984.00; the other 167 trades together lost $17.50.
- 43 momentum trades made exactly +$20. All 43 exited at the stop after the lock moved it to entry + 2.5 points
  (4 MNQ × 2.5 points × $2).
- By month, July lost $3,987.50 (momentum −$1,852).
- Before the September 11 roll, while DEC26 was not the front month: 106 trades, −$147.00. After it: 66 trades,
  +$11,113.50. **Almost all the profit came in the last five weeks.** Whether the cause is the contract or the market
  period cannot be told apart without front-month bars for June to September.

## 2. Costs - arithmetic executed; full reruns proposed (NinjaTrader) and executed on the stand-in (section 4)

$0.95 a side ($1.90 a round trip per contract) is a **provisional** assumption: it is what the earlier exports
charged. Apply it to the same 172 trades: arithmetic only, no rerun.

| Commission | Commission $ | Net | Closed-trade drawdown |
|---|---:|---:|---:|
| none (the reference) | $0.00 | $10,966.50 | $4,649.50 |
| $0.62 a side | $751.44 | $10,215.06 | $4,845.42 |
| $0.95 a side | $1,151.40 | $9,815.10 | $4,949.70 |

These are adjustments to fixed trades. They are not reruns.

**The reruns in NinjaTrader - proposed (the user runs them; not done here):**
- Same run, then:
  1. Check that commission is on. In the Analyzer settings look for **Include commission**, and check that the
     account's commission template gives $0.95 a side; the earlier export's "Commission" column showed it did.
  2. Run three times with Slippage 0, 1 and 2, keeping everything else identical.
- **Checks:**
  - At Slippage 0 the trades must equal the reference's.
  - The Commission column should read $1.90 × contracts on every trade, never twice.
- **Where NinjaTrader applies slippage** (its documentation; confirm on the export):
  - On market and stop orders: the entries, the stop losses, and the 16:00 and other market exits.
  - Not on limit orders: the take-profits.
  - The filled price is not expected to fall outside the bar's high/low. A trade at a bar's extreme will show that.
- Each run is complete. A changed fill can move the stop, a trade's survival, its exit and the next trades.

## 3. Data coverage - executed from the run's Output; the bars themselves are unavailable here

**Instrument and settings:**

| Item | Value |
|---|---|
| Instrument | MNQ DEC26: one contract, not a merged series (the instrument shows as "MNQ DEC26") |
| Merge / roll policy | Not shown in the Output: check Tools → Options → Market Data → Merge policy |
| Data source | The user's connection's historical data |
| Trading hours | CME US Index Futures ETH |
| Platform time zone | Eastern |
| Requested | 1/1/2026 00:00 to 10/17/2026 00:00 |

**What was loaded:**
- First bar: 2026-05-03 18:01 New York, the Sunday evening open. Last bar: 2026-10-16 16:59.
- 129,751 bars.
- No bars before May 3, although January 1 was asked for. The local data for MNQ DEC26 starts there. Tools →
  Historical Data shows the dates stored; a screenshot of that would confirm it.

**Session completeness:**
- 116 sessions were scheduled from May 4 to Oct 16, with the closed holidays (5/25, 6/19, 7/3, 9/7) taken out.
  No early close falls in this range.
- 94 of them have a 09:30 bar; the strategy prints its daily line at that bar.
- 24 do not, and they are consecutive weekdays: **May 22 to June 26.**

**Why the gap is missing data, not quiet logging:**
- 129,751 bars is about 94 full sessions of 1,380 minutes each (18:00 to 17:00). That leaves no room for bars in the
  24 missing sessions.
- So those sessions have no bars at all, not just a missing 09:30 bar. This is inferred from the counts. The bars
  export would prove it per session.

**Warm-up and the first trade:**
- The 14 warm-up sessions are May 4 to May 21.
- The engine was ready from **2026-05-21 16:00**: 14 full sessions, first ready bar at May 21's close.
- **Trading began June 29 because the next session with data is June 29.** The first trade was a breakout short
  signalled 10:11, filled 10:12 at 29,745.50.

**Contamination by the gap:**
- On June 29, "yesterday" for both setups was May 21: the bot's previous close and its 14-session noise, and the
  breakout's previous range.
- The four June 29 trades (−$373) ran on a five-week-old reference. A real feed would not do this, so these trades
  are an artifact of the data hole.
- **Retrospective exclusion, not a live rule:** treat sessions right after a data hole as unrepresentative in analysis.
  The strategy's own skip-date rule must not be fed knowledge from later in the day.

**Contract month:**
- Until about September 10 (the roll eight days before the September 18 expiry), DEC26 was the deferred contract.
  The account would have traded SEP26.
- 106 of the 172 trades fall in that stretch.
- For the primary comparisons, the bars should be the contract actually traded: SEP26 until the roll, then DEC26.
  NinjaTrader's merged "MNQ ##-##" series with a merge policy is the alternative; disclose which is used.

## 4. Candidates A / B / C - executed on the stand-in (rescaled data); native NinjaTrader runs proposed

**Candidates:**
- **A:** the current combined strategy (the reference's settings).
- **B:** momentum only (UseBreakout off).
- **C:** momentum plus breakout longs (new **BreakoutShorts** switch off, default on). The rule was fixed before any
  run: a day whose short level is reached first has no breakout trade. C therefore only removes trades.
- A test proves C equals A minus A's breakout shorts, exactly (`test_breakout_shorts_off_removes_only_the_breakout_shorts`).

**Held fixed in all three:**
- sizing and parameters, warm-up and session handling;
- commission $0.95 a side; slippage 0, 1 and 2 ticks;
- sessions with missing minutes given no new trades;
- every run complete (`research/components_nt.py`).

**Data:** not the user's MNQ bars, which are not here.
- NQ futures 2015 to 2025, 1-minute (Hugging Face mdelcristo/NQ-F_1min).
- The NSXUSD index, July 2025 to September 2026 (HistData).
- Both are rescaled each month to today's price level.

**NQ, 2015-03 to 2025-06** (124 months; `verification/candidates_abc_nq_2015-2025.csv`):

| Candidate | Slip | Net after $0.95/side | Positions | PF | $/position | Closed DD | Intraday DD | Streak | Worst day | Months + | Top-5 share | Eval pass / fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 0 | $202,634 | 6,578 | 1.3 | $30.8 | $12,122 | $12,536 | 10 | −$1,059 | 82/124 | 9% | 34.7% / 63.3% |
| A | 1 | $173,746 | 6,566 | 1.2 | $26.5 | $12,782 | $13,196 | 10 | −$1,066 | 78/124 | 11% | 33.3% / 64.7% |
| A | 2 | $148,632 | 6,543 | 1.2 | $22.7 | $13,253 | $13,666 | 10 | −$1,072 | 78/124 | 13% | 32.0% / 66.0% |
| B | 0 | $138,300 | 4,970 | 1.3 | $27.8 | $12,020 | $12,774 | 11 | −$623 | 79/124 | 14% | 32.9% / 59.3% |
| B | 1 | $112,267 | 4,957 | 1.2 | $22.6 | $13,171 | $13,444 | 11 | −$629 | 75/124 | 17% | 31.9% / 60.4% |
| B | 2 | $92,934 | 4,934 | 1.2 | $18.8 | $14,871 | $15,146 | 11 | −$635 | 73/124 | 20% | 30.3% / 62.3% |
| C | 0 | $183,390 | 5,739 | 1.3 | $32.0 | $12,930 | $13,574 | 11 | −$1,059 | 85/124 | 10% | 34.2% / 60.1% |
| C | 1 | $155,826 | 5,726 | 1.3 | $27.2 | $13,566 | $14,210 | 11 | −$1,066 | 81/124 | 12% | 32.7% / 62.6% |
| C | 2 | $135,007 | 5,703 | 1.2 | $23.7 | $14,015 | $14,656 | 11 | −$1,072 | 77/124 | 14% | 31.7% / 64.3% |

**Index, 2025-07 to 2026-09** (15 months; `verification/candidates_abc_index_2025-2026.csv`):

| Candidate | Slip | Net | Positions | Closed DD | Intraday DD | Worst 3 months | Eval pass / fail |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0 / 1 / 2 | $8,936 / $3,404 / $2,207 | 632 | $7,953 / $9,605 / $10,043 | $9,307 / $9,910 / $10,351 | −$6,659 / −$7,759 / −$8,127 | 16.6% / 77.8% (0 ticks) |
| B | 0 / 1 / 2 | $7,050 / $1,960 / $1,042 | 461 | $5,845 / $9,335 / $9,756 | $6,121 / $9,509 / $9,930 | −$4,704 / −$6,004 / −$6,310 | 18.9% / 60.3% |
| C | 0 / 1 / 2 | $8,197 / $2,806 / $1,750 | 543 | $7,604 / $9,482 / $9,967 | $8,621 / $9,656 / $10,141 | −$5,624 / −$6,428 / −$6,761 | 13.9% / 71.2% |

**What it shows:**
- **The breakout never changes a momentum trade.** The bot's dollars are identical in A, B and C at every
  slippage, because the bot always comes first. So it does not interfere with momentum entries. It adds its own
  trades and its own risk.
- **Breakout shorts helped over the longer history:**
  - NQ: A beats C by $19,244 / $17,920 / $13,625 over ten years at 0 / 1 / 2 ticks, with a closed drawdown lower by
    $808 / $784 / $762.
  - Index: they added $739 / $598 / $457.
- **They lost $3,780 in the reference.** That is 27 trades in about four months, mostly before the roll, so the
  reference's loss is not supported as a pattern by the longer data.
- **The whole breakout over NQ** added $64,334 / $61,479 / $55,699. Its closed drawdown was about the same at 0
  ticks ($102 more than B) and smaller at 1 and 2 ticks ($389 / $1,618 less).
- **On the index's 15 months,** B had the smallest drawdown at 0 ticks ($5,845 vs $7,953). At 1 and 2 ticks the
  three are within $400 of each other. These 15 months are thin profit for every candidate: about $2,000-3,400 after
  1 tick for the strategy at its full size, over 15 months.
- **Slippage is the largest single cost.** Each tick costs A $25,000-29,000 over NQ's ten years (about $4.40 a
  position). On the index's 15 months the first tick costs more than half the profit.
- **Account rules:** the evaluation replay (Apex 50K intraday trail, $3,000 target, $2,000 trailing loss, 30
  calendar days, from every session, overlapping) fails more often than it passes for all three. Section 9 of the
  brief (account survival) is not done yet.

**Conclusions on this evidence:**
- **A: retain for further testing.** It is the reference, and it beats B and C on NQ net at every slippage and on
  NQ drawdown at 1 and 2 ticks.
- **B: reject.** It has less profit everywhere and no consistent drawdown advantage. It is smaller only at 0 ticks
  on the index's 15 months.
- **C: insufficient evidence to adopt; the longer data argues against it.** The reference's breakout-short loss is
  not an untouched test and does not repeat over ten years of NQ.
- All three conclusions rest on rescaled data in the stand-in. The native MNQ runs below decide.

**Native NinjaTrader A / B / C - proposed (the user runs them):**
- The same analyzer run as the reference, commission on (section 2).
- A: as is. B: "Breakout in the bot's gaps" off. C: "Breakout shorts" off (this commit).
- Each at Slippage 0, 1 and 2, with Diagnostics on.
- Send each run's Output text, its Trades export, and the 1-minute bars (Tools → Historical Data → Export):
  - SEP26 for June 29 to September 10;
  - DEC26 for September 11 to October 16;
  - so the stand-in can be reconciled on the same bars.

## 4b. Native cost runs, 9/11 to 10/17 - executed by the user in NinjaTrader; reconciled here

**What was run:** four Strategy Analyzer runs on MNQ DEC26, 9/11/2026 to 10/17/2026, commission on, slippage 0 / 1 /
1 / 2 (the 1-tick run appears twice in the Output). The code is this commit's: the settings line shows "shorts True".
Files are in `verification/native_costs_sep11/`.

**The window:**
- Every run loaded bars from 9/10 18:01. The engine was ready only at **9/30 16:00**: the first 14 sessions (9/11 to
  9/30) went to warm-up.
- So all four runs trade **10/1 to 10/16 only**: 12 sessions, 28 trades, 103 contracts.
- To trade from 9/11, the run must start 14 sessions earlier: **8/21/2026**. Count only the trades from 9/11.

**Reconciled:**
- At 0 ticks the 28 trades are **exactly the reference's October trades**: same entries, exits, contracts, and $2,678.50
  before costs.
- The October noise uses the same 14 sessions (9/11 to 9/30) in both runs. A short run started at the roll date
  reproduces the long one.

| Slippage | Gross | Commission | Net | Max drawdown (NT) |
|---|---:|---:|---:|---:|
| 0 | $2,678.50 | $195.70 | $2,482.80 | $2,675.20 |
| 1 tick | $2,629.50 | $195.70 | $2,433.80 | $2,709.20 |
| 2 ticks | $2,579.50 | $195.70 | $2,383.80 | $2,744.20 |

- **Commission:** $195.70 = 103 contracts × $1.90, charged once.

**Where NinjaTrader put the slippage** (per-fill comparison, 1 tick against 0):
- **Market entries:** slipped, 27 of 28. One was not; it is presumably bounded by its bar.
- **16:00 market exits:** slipped, 3 of 3.
- **Stop-loss exits:** 18 of 21 at an unchanged price.
- **Take-profits:** never slipped. They move only because they are set in ticks from the slipped fill.

**CORRECTED (docs/MNQ_NATIVE.md).** The earlier reading here was wrong. The first stop is set in ticks from the
slipped fill, so it moves a tick with the entry, and an unchanged exit price means the stop *was* slipped. On
identical MNQ bars the stand-in, which slips every market and stop fill, reproduces NinjaTrader's 1- and 2-tick runs
to the cent. So NinjaTrader's slippage setting covers stops too, and its slippage results do not understate costs on
that account.

**Where the reference's after-roll profit came from:**
- 9/11 to 9/30: 38 trades, +$8,435 before costs. This window is not covered by these four runs.
- 10/1 to 10/16: 28 trades, +$2,678.50.

## 4c. Native A / B / C, 9 runs - executed by the user in NinjaTrader; COMPLETED (for the period traded)

**Files:** the nine summaries are in `verification/native_abc_sep11/`. The A runs' Output is in
`verification/native_costs_sep11/`. The B and C runs' Output and the Trades exports of all nine were not received.

**The period traded:**
- Every summary reads **Start 9/11/2026**, End 10/17/2026. The runs were started on 9/11, not on 8/20 as in
  docs/NATIVE_RUNS.md.
- Warm-up therefore took 9/11 to 9/30. The A runs' Output says "engine ready ... from 2026-09-30 16:00".
- **The comparison covers 10/1 to 10/16:**
  - 12 sessions;
  - trades on 9 of them;
  - first entry 10/1 10:02, last exit 10/16 13:34 (A runs).
- B and C started the same day with the same data, so they have the same warm-up. Confirming it from their own Output
  needs those files.

| Run | Positions | Net after commission | Commission | Max drawdown (NT, closed) | Longest losing streak | Long / short net |
|---|---:|---:|---:|---:|---:|---|
| A_S0 | 28 | $2,482.80 | $195.70 | $2,675.20 | 7 | −$1,330.50 / $3,813.30 |
| A_S1 | 28 | $2,433.80 | $195.70 | $2,709.20 | 7 | −$1,340.00 / $3,773.80 |
| A_S2 | 28 | $2,383.80 | $195.70 | $2,744.20 | 7 | −$1,350.50 / $3,734.30 |
| B_S0 | 20 | $4,684.00 | $152.00 | $818.00 | 3 | −$622.80 / $5,306.80 |
| B_S1 | 20 | $4,646.00 | $152.00 | $828.00 | 3 | −$628.80 / $5,274.80 |
| B_S2 | 20 | $4,608.00 | $152.00 | $838.00 | 3 | −$634.80 / $5,242.80 |
| C_S0 | 24 | $3,976.30 | $167.20 | $1,390.60 | 5 | −$1,330.50 / $5,306.80 |
| C_S1 | 24 | $3,934.80 | $167.20 | $1,401.60 | 5 | −$1,340.00 / $5,274.80 |
| C_S2 | 24 | $3,892.30 | $167.20 | $1,413.60 | 5 | −$1,350.50 / $5,242.80 |

**The switches did what they should** (checked from the summaries; trade by trade needs the Trades exports):
- **B equals A's momentum trades:**
  - A's 20 momentum trades have the same count and net as B's: 3 long at −$622.80 and 17 short at $5,306.80, at
    0 ticks.
  - B's drawdown, $818.00, is exactly the drawdown of A's momentum trades alone, recomputed from A's trades.
- **C equals A without its 4 breakout shorts:**
  - 28 − 4 = 24 positions.
  - A_S0 − C_S0 = −$1,493.50, which is those 4 trades' −$1,465.00 plus $28.50 commission.
- **No entry opportunity changed between configurations.** Removing the breakout did not add or move any momentum
  trade, as the stand-in predicted: the momentum bot always comes first.

**Why B leads here:**
- Eight breakout trades (4 long, 4 short, 23 contracts) lost $2,157.50 before costs, $2,201.20 after, in 12 sessions.
- B is A without them. Nothing else differs.

**Slippage:** each tick costs A $49, B $38 and C $41.50 here. NinjaTrader slips the market entries and exits but
the stops too (section 4b, corrected), as the stand-in does. They are not extrapolated beyond these 28
trades.

**Status:**
- **B is the leading candidate from this sample, not an established strategy.**
- **B is frozen.** Same code and settings as A, with "Breakout in the bot's gaps" off; nothing else changed.
  docs/NATIVE_RUNS.md section 6.
- **What the longer evidence says so far:**
  - Over the 172-trade run (6/29 to 10/16, no costs), the breakout lost $2,913.50 before costs, which agrees with B.
  - Over ten years of NQ on the stand-in (section 4), the breakout added $55,700-64,300, which disagrees.
  - The longer native comparison (docs/NATIVE_RUNS.md section 7) decides between them.

## 4d. Native A vs B over the longest MNQ history - executed by the user; summaries only so far

**Runs:** Start 1/1/2026, End 10/17/2026, commission on. The data loads from 5/3 and the engine is ready 5/21. The
5/22 to 6/26 hole means **trading runs 6/29 to 10/16**, the 77 sessions with data (docs/NATIVE_RUNS.md section 7).
Summaries are in `verification/native_long/`.

**Missing:** all Trades exports and Outputs.

| Run | Positions | Net after commission | Commission | Profit factor | Max drawdown (NT, closed) | Longest losing streak | Long / short net |
|---|---:|---:|---:|---:|---:|---:|---|
| A_L0 | 171 | $10,022.70 | $1,143.80 | 1.48 | $4,742.10 | 10 | $7,885.90 / $2,136.80 |
| A_L1 | 170 | $9,656.80 | $1,136.20 | 1.46 | $4,829.60 | 10 | $7,693.00 / $1,963.80 |
| A_L2 | 170 | $9,350.80 | $1,136.20 | 1.44 | $4,918.60 | 10 | $7,560.00 / $1,790.80 |
| B_L0 | 119 | $13,175.60 | $904.40 | 2.27 | $2,736.80 | 6 | $7,144.80 / $6,030.80 |
| B_L1 | 118 | $12,889.20 | $896.80 | 2.23 | $2,808.80 | 6 | $6,992.40 / $5,896.80 |
| B_L2 | 118 | $12,663.20 | $896.80 | 2.19 | $2,882.80 | 6 | $6,900.40 / $5,762.80 |

**B against A, both executed, same costs:**

| Slippage | Net (B − A) | Drawdown (B against A) | Losing streak (B / A) |
|---|---:|---|---|
| 0 ticks | +$3,152.90 | $2,005 lower | 6 / 10 |
| 1 tick | +$3,232.40 | $2,021 lower | 6 / 10 |
| 2 ticks | +$3,312.40 | $2,036 lower | 6 / 10 |

**B's lead held over the longer native period.**

**B is A's momentum trades, here too** (from the summaries; the Trades exports confirm it trade by trade):
- B_L0's longs are A_L0's momentum longs: 52 trades, $7,540.00 before costs.
- A_L0's 77 longs are those 52 plus the reference's 25 breakout longs (+$866.50). Their total, $8,406.50 before
  costs, equals A_L0's long side.
- B_L0's shorts, 67 trades and $6,540.00 before costs, are A_L0's shorts without the 27 breakout shorts (−$3,780.00).
  Again they equal A_L0's short side, $2,760.00.

**Why A_L0 is not the 172-trade reference less commission:**
- The reference ran without commission. A_L0 has 171 trades, one momentum short of −$200 fewer.
- The bot's daily loser limit counts its positions after commission (the account's actual result). With commission on,
  a near-zero trade became a loser, the day reached its 3-loser limit sooner, and one later short (−$200) was not
  taken.
- B, also with commission, has the same 67 momentum shorts.

An earlier version of this section read the difference as the breakout changing a momentum trade. That was wrong: it
compared B, with commission, against the reference, without it.

**Slippage:**
- A loses $366 from 0 to 1 tick and $306 more to 2 ticks.
- B loses $286 and then $226.
- At 1 tick B_L1 has one trade fewer than B_L0: a changed fill changed a later opportunity.
- NinjaTrader slips stops as well (section 4b, corrected).

**Not yet possible without the Trades exports:**
- monthly results, July included;
- the 6/29 view (with and without);
- the intraday risk estimate;
- worst day;
- the evaluation replay.

**What still argues against B:**
- Over ten years of NQ on the stand-in (rescaled, section 4) the breakout added money.
- These 77 sessions are one stretch of one year.
- **B leads on all native MNQ evidence so far. It is still a candidate, not an established strategy.**

## 4e. A vs B, 6/29 to 10/16, rebuilt from the fills - executed (user's NinjaTrader runs; analysis here)

**Source:** the Output the user saved at 3:53 PM. It holds every run of the day in sequence
(`verification/native_long/ninjascript_output_all_runs.txt`).
- Each longer run was rebuilt from its own execution lines (`research/native_long.py`, output in
  `verification/native_long/analysis.txt`, trades in `*_trades_from_output.csv`).
- Each was matched to its summary to the cent, at $1.90 a contract.

**Switches and warm-up, confirmed from each run's own settings and funnel lines:**
- A: UseBreakout True. B: UseBreakout False.
- All six: engine ready 5/21 16:00.
- First entry 6/29 10:12 (A) and 13:31 (B); last exit 10/16 13:34.
- No rejection, no runtime error.

**B is exactly A's momentum trades, trade by trade:**
- 119 of 119 at 0 ticks, and 118 of 118 at 1 and 2 ticks.
- Same entry and exit times, prices and contracts.
- Removing the breakout changed no momentum trade in this period. B − A is exactly the breakout's own result.

| After $1.90 / contract | A_L0 | A_L1 | A_L2 | B_L0 | B_L1 | B_L2 |
|---|---:|---:|---:|---:|---:|---:|
| Positions / contracts | 171 / 602 | 170 / 598 | 170 / 598 | 119 / 476 | 118 / 472 | 118 / 472 |
| Net | $10,022.70 | $9,656.80 | $9,350.80 | $13,175.60 | $12,889.20 | $12,663.20 |
| Profit factor | 1.5 | 1.5 | 1.4 | 2.3 | 2.2 | 2.2 |
| Avg win / avg loss | $368 / −$240 | $370 / −$242 | $368 / −$244 | $351 / −$199 | $355 / −$202 | $353 / −$204 |
| Closed-trade drawdown | $4,742.10 | $4,829.60 | $4,918.60 | $2,736.80 | $2,808.80 | $2,882.80 |
| Longest losing streak | 10 | 10 | 10 | 6 | 6 | 6 |
| Worst day | −$920.60 | −$927.60 | −$934.60 | −$622.80 | −$628.80 | −$634.80 |
| Losing days / days traded | 38 / 62 | 38 / 62 | 38 / 62 | 15 / 35 | 16 / 35 | 16 / 35 |
| Largest 5 winners' share of net | 109% | 113% | 117% | 75% | 76% | 77% |
| Without 6/29 (retrospective): net | $10,420.40 | $10,059.00 | $9,759.50 | $13,358.40 | $13,076.00 | $12,856.00 |

**Monthly** (net, 0 ticks; the 1- and 2-tick runs move each month by under $180):

| Month | A | B | B − A (= −breakout) |
|---|---:|---:|---:|
| June (6/29-30) | $1,135.50 | $1,350.40 | +$214.90 |
| July | −$4,101.00 | −$1,918.00 | +$2,183.00 |
| August | $4,003.80 | $3,360.40 | −$643.40 |
| September | $6,501.60 | $5,698.80 | −$802.80 |
| October (1-16) | $2,482.80 | $4,684.00 | +$2,201.20 |

**What the breakout did over these 77 sessions:**
- Components (0 ticks, net): breakout longs +$741.10 over 25 trades; breakout shorts −$3,894.00 over 27.
- Net −$3,152.90 over 52 trades.
- **It helped in August and September and lost in July and October.** B's lead comes from two months, not every
  month.
- It did not interfere with momentum entries.
- It added drawdown: A's drawdown is $2,005 larger, its losing streak 4 longer, its worst day $298 worse.

**July** (net, 0 ticks):
- A lost $4,101.00: momentum shorts −$1,918.80, momentum longs +$0.80, breakout longs −$811.30, breakout shorts
  −$1,371.70.
- B lost $1,918.00: the momentum shorts.
- **July's momentum loss is in B too.** Removing the breakout halves July's loss; it does not remove it.

**Concentration:** B's five largest winners are 75% of its net. A's are 109%: the rest of A's trades together lost
money. B is less dependent on a few trades, but still depends on them.

**Not available from these files:**
- **Intraday account risk.** Each trade's MAE (the Trades export) or the bars are needed; the Output has fills only.
- **The evaluation replay at intraday resolution,** for the same reason. A replay on closed trades only would
  understate failures of an intraday-trailing evaluation, so it is not offered as the answer.

**Status:**
- **B leads A over all native MNQ evidence** (10/1-16 and 6/29-10/16), at 0, 1 and 2 ticks, on net, drawdown,
  losing streak and worst day.
- **It remains the leading candidate, not an established strategy:**
  - one stretch of 77 sessions;
  - B's lead comes from two of five months;
  - on ten years of rescaled NQ in the stand-in the breakout added money.
- Next: the forward simulation (docs/NATIVE_RUNS.md section 8). The Trades exports, if available, add the intraday
  view first.

**Also in the Output, outside this comparison:** one C run (shorts off) that loaded 57,719 bars (from about 8/20). It
was ready 9/9 16:00 and made 58 trades from 9/10, net $12,369.80. It has no summary file and is not used here.

## 5. Not started (brief steps 5-11) - proposed

The following were not started; the brief asked for sections 1-4 first:
- the July loss analysis and any filter;
- the shared daily controls tested at preset limits;
- native evidence for the half-off exit (PartialAtR; its corrected implementation is in docs/VERIFICATION.md section
  10, and needs a native NinjaTrader check);
- the exit comparison;
- account survival;
- the forward-test freeze.
