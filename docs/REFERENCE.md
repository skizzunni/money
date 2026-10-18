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

## 5. Not started (brief steps 5-11) - proposed

The following were not started; the brief asked for sections 1-4 first:
- the July loss analysis and any filter;
- the shared daily controls tested at preset limits;
- native evidence for the half-off exit (PartialAtR; its corrected implementation is in docs/VERIFICATION.md section
  10, and needs a native NinjaTrader check);
- the exit comparison;
- account survival;
- the forward-test freeze.
