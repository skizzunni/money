# The Pine reference and the two-loss candidate (pre-registration, October 20, 2026)

Written and committed **before any run** described here. Nothing below replaces a working version: the Pine script,
frozen B and candidate C stay as they are. The candidate is a **settings preset**, compared with its reference.

## The reference

**The user's exact Pine script:** `pine/reference/mnq_noise_momentum_v1.5_user.pine`.
- sha256 `cd44ee68d575e74019cd308f1079838a2b5cb7453d8b7c40473436c59b851975`; the bytes as pasted, CRLF line endings.
- Its content is the repo's Pine v1.5 at commit 5e092d0: 0 differing lines, ignoring line endings.
- The repo's current `pine/mnq_noise_momentum.pine` is v1.6 and is not the reference.

**Its settings (R4):**
- the script's own defaults, except 2 contracts and a $70 max loss per trade;
- that keeps the defaults' stop distance of 17.5 points a contract (the $350 over 10 contracts), and with it the lock
  trigger of 17.5 points;
- 5-minute chart; 4 losing trades a day.
- These are the settings of the independent tests the user quoted.
- **Assumption:** the user's saved TradingView inputs were not provided. If they differ, the reference runs again with
  them.

**The candidate (R2):** R4 with the daily losing-trade limit at **2 instead of 4**. Nothing else changes: not the stop
distance, size, lock, take-profit or entry filters.

## Reproduction, before any comparison

The reference runs three ways on the same bars:
- the MNQ traded-contract series (09-26 to the 9/10 roll session, then 12-26, 09-26 back-adjusted);
- aggregated to 5-minute bars, 09:30 to 16:00, warm-up from 6/29.

| | What runs | Label |
|---|---|---|
| (a) | The Pine v1.5 source itself, in the repo's Pine interpreter (`tests/pine_interpreter.py`, TradingView's fill rules as emulated there) | Pine source, emulated; not TradingView |
| (b) | The NinjaTrader strategy MnqNoiseMomentum, frozen B's code (sha256 `1fbdcea0...`, engine `e5a1ec0c...`), at R4's settings, in the NinjaTrader stand-in | NinjaTrader code, stand-in simulator |
| (c) | The Python reference `mnqbot/noise.py` | Reference model |

**R-check:** (a) and (c) must agree trade for trade. (a) against (b) is joined trade by trade, and every mismatch must
be explained by a documented platform difference.
- A true TradingView-versus-NinjaTrader join needs TradingView's own List of Trades export and the matching NinjaTrader
  run: the user's to produce. The join tool takes both files.

## Comparison R2 against R4: full strategy runs, not trades deleted from an export

**Primary evidence:**
- the NinjaTrader strategy (b) on the MNQ traded contracts, 7/20 to 10/16/2026;
- commission $0.95 a side; slippage 1 and 2 ticks.
- **This period is development data:** examined in earlier rounds. It is not untouched.

**Secondary:**
- NQ 2015-03 to 2025-06, rescaled to MNQ terms (also examined before), by calendar year;
- 2023-01 to 2025-06 shown apart, the span closest to the quoted tests.

**Reported for each:**
- **Continuous research, every eligible session counted:**
  - trades per eligible session and the share of sessions with 0 / 1 / 2 / 3+ trades;
  - net and net per session; months (MNQ) or years (NQ); long and short apart;
  - profit factor; expectancy per trade; the five largest winners' share;
  - closed and intraday drawdown (open P/L at bar extremes); losing streak; worst day;
  - the trades R4 has and R2 does not.
- **Evaluation replay, Apex $50K intraday trail:**
  - from every start, identical for both, to the first pass, breach or expiry;
  - the highest equity including open P/L, a trail that persists across days;
  - 30 calendar days; unfinished starts apart.

## Acceptance criteria (decided now): R2 replaces R4 as the reference's daily limit only if all hold

- **Q1:** R2's net after costs is positive at 1 and 2 ticks, on MNQ and on NQ.
- **Q2:** R2's net divided by its intraday drawdown is higher than R4's at 1 and 2 ticks, on MNQ and on NQ.
- **Q3:** the trades the limit removes are net negative at both slippages, on MNQ and on NQ. These are R4's trades that
  R2 does not take.
- **Q4:** in the evaluation replay, R2's chance of passing (expirations counted) is at least R4's, and its certain
  breaches are no more, at both slippages, on MNQ and on NQ.
- **Q5:** on NQ at 1 tick, R2 nets more than R4 in at least 7 of the 11 calendar years.

**Frequency** (1-2 trades per eligible session preferred) is reported but not a criterion. No entry is ever added to
meet it.

**If a criterion fails, R4 stays the reference** and the result is reported as a rejection.

## Candidate C: separate items in this round

- **Shutdown:** outcomes reported as pass / breach / expired while still able to trade / unable to fund another trade
  under the internal reserve (then expired). Individual evaluations from explicit start dates.
- **Execution fixes, each with a focused test:**
  - a partially filled entry's remainder is tracked until it is filled or cancelled;
  - losing positions are counted by the entry order's identity, not by fill timestamps;
  - an unrealized peak reached in a bar where the position exits is captured.
- **Unchanged:** C's rules, settings and exits otherwise.

---

# Results (October 20, 2026; after the criteria above were committed in c875fcd)

**What ran where:**
- **NinjaTrader:** nothing new in this round. The only native runs are the earlier ones: B's, and C's 1/1 to 10/18 run.
  The latest summary sent (`162245e3-...08-56_PM.csv`) is byte-identical to that C run's summary
  (sha256 `dd47bf8d...`).
- **Everything below** is the Pine source in the repo's interpreter, the NinjaTrader code in the stand-in simulator,
  or the Python reference, as labelled.

## 1. The reference reproduced (MNQ traded contracts, 5-minute bars, 6/29 to 10/16; `verification/pine_reference/`)

| R4, 1 tick | Pine source (interpreter) | Python reference | NinjaTrader code (stand-in) |
|---|---|---|---|
| Trades, net | 111, $4,150.79 | 111, $4,150.79 | 111, $2,961.20 |
| Agreement | Identical, trade for trade | Identical | 54 identical; the other 57 explained below |

**Every Pine/NinjaTrader mismatch has a cause** (`joined_*_pine_vs_nt.csv` lists each trade with its category).

R4, 1 tick:

| Category | Trades | NinjaTrader minus Pine |
|---|---:|---:|
| A: 16:00 exit, Pine at the 15:55 close, NinjaTrader at the next bar's open | 5 | $0.00 |
| B: same price, named differently (Pine "Lock", NinjaTrader "Stop passed") | 7 | $0.00 |
| C: fill-bar max-loss stop from the expected fill (Pine) or the actual fill (NinjaTrader) | 33 | −$1,195.42 |
| D: stop or target rounded to a tick in NinjaTrader | 12 | +$5.83 |
| Unexplained | 0 | |

**Other runs:**
- **R4 at 2 ticks, and R2:** the same categories. A few "knock-on" trades follow an earlier differing exit that day.
  There are 0 unexplained.
- **Pine against Python at 2 ticks:** they differ on 49 exits. Pine's fill-bar stop uses the signal close + 1 tick
  whatever the slippage; the reference uses the slippage.
- **Category C is the material one.** Pine's chart backtest measures the first bar's max-loss stop from a price the
  live order never gets. NinjaTrader's bracket, from the actual fill, is what a live order does. Whether that helps
  or hurts either platform depends on the bars (section 1b). An earlier version of this line said it "flatters Pine
  by about $11 a trade": that was the total divided by the trades, and one trade makes almost all of it.

## 1b. Which differences are structural and which depend on the bars (`research/pine_nt_structure.py`, `structure.csv`)

"NinjaTrader better / worse" counts the trades whose P/L is higher / lower in NinjaTrader than in Pine.

| Category, R4 | 1 tick: trades; better / worse; net | 2 ticks: trades; better / worse; net | Kind |
|---|---|---|---|
| A: 16:00 exit timing | 5; 1 / 2; $0.00 | 4; 1 / 1; +$1.00 | Structural timing; the sign depends on the 16:00 bar's open |
| B: name only | 7; 0 / 0; $0.00 | 6; 0 / 0; $0.00 | Structural; no money |
| C: fill-bar stop from the expected or the actual fill | 33; **13 / 20**; −$1,195.42 | 41; **30 / 11**; −$1,307.43 | Structural rule; **the outcome depends on the bars** |
| D: tick rounding | 12; 12 / 0; +$5.83 | 13; 13 / 0; +$6.32 | Structural, always NinjaTrader's way here, cents |

**Category C in detail:**
- **One trade carries the total:** 2026-08-03 10:30, long, −$1,168.42 at 1 tick.
  - The signal bar closed at 28,962.25, so Pine expected a fill at 28,962.50 and put its stop 17.5 points below, at
    28,945.00.
  - The next bar opened a tick higher, at 28,962.75. With a tick of slippage NinjaTrader filled at 28,963.00, so its
    stop sat at 28,945.50.
  - The fill bar's low was **exactly 28,945.50**. NinjaTrader was stopped (−$74.80). Pine's stop, two ticks lower,
    was not touched, and its trade ran to the target (+$1,093.62).
- **Without that trade, category C nets −$27.00 at 1 tick and −$138.00 at 2 ticks** across 32 and 40 trades.
- **By month, at 1 tick:** July +$6, August −$1,201, September $0, October $0.
- **At 2 ticks most C trades go NinjaTrader's way** (30 of 41): the further the fill from Pine's expected fill, the
  further away NinjaTrader's stop.

**So the Pine-vs-NinjaTrader gap is not "Pine is optimistic":**
- The rule difference is structural and always present.
- Its direction on a given trade depends on where the fill bar's low or high falls against two stop levels a few ticks
  apart. On these 111 trades it hinged on one bar.
- R2's runs show the same pattern (`structure.csv`): one trade gives −$1,168.42 of C's −$1,198.42, and knock-on
  trades follow from it.

**Not done:** a TradingView-run List of Trades joined to a native NinjaTrader run of the same preset. It needs the
user's two exports (requested once below).

## 2. R2 (two losses) against R4 (four) - full NinjaTrader-strategy runs, stand-in

**Data:**
- **MNQ:** 64 eligible sessions, 7/20 to 10/16/2026 (development data, examined before).
- **NQ:** 2015-03 to 2025-06, rescaled (examined before), 2,571 eligible sessions.
- $0.95 a side.

| | MNQ R4, 1 t / 2 t | MNQ R2, 1 t / 2 t | NQ R4, 1 t / 2 t | NQ R2, 1 t / 2 t |
|---|---|---|---|---|
| Trades per eligible session | 1.73 / 1.70 | 1.09 / 1.06 | 2.10 / 2.08 | 1.43 / 1.41 |
| Sessions with 0 / 1 / 2 / 3+ trades | 58 / 5 / 3 / 34 % | 58 / 5 / 17 / 20 % | 42 / 13 / 9 / 36 % | 42 / 13 / 24 / 22 % |
| Net; per eligible session | $2,961, $46 / $3,042, $48 | $562, $9 / $1,122, $18 | $45,153, $17.56 / $34,018, $13.23 | $34,068, $13.25 / $25,818, $10.04 |
| Profit factor; expectancy a trade | 1.64, $26.68 / 1.63 | 1.19, $8.03 / 1.37 | 1.19, $8.37 / 1.14 | 1.21, $9.27 / 1.16 |
| Largest 5 winners' share of net | 147% / 143% | 552% / 295% | 21% / 28% | 27% / 35% |
| Intraday drawdown; net ÷ it | $1,684, 1.76 / $1,877, 1.62 | $1,936, 0.29 / $1,981, 0.57 | $5,973, 7.56 / $6,070, 5.60 | $4,975, 6.85 / $5,364, 4.81 |
| Losing streak; worst day | 11, −$299 / 12, −$303 | 12, −$150 / 13, −$152 | 23, −$299 / 23, −$303 | 15, −$150 / 17, −$152 |
| Long; short (1 tick) | $216 (PF 1.08); $2,745 (2.35) | −$822 (0.44); $1,384 (1.91) | $24,939 (1.22); $20,213 (1.16) | $22,549 (1.29); $11,519 (1.14) |
| Evaluation: pass / breach / expired | 1 / 0 / 43 (both) | 0 / 0 / 44 (both) | 221 / 344 / 1,977; 205 / 401 / 1,924 | 74 / 63 / 2,489; 65 / 69 / 2,490 |
| Chance of passing | 2.3% | 0% | 8.4% / 7.8% | 2.8% / 2.5% |
| Trades the 2-loss limit removes | | 41: **+$2,399** / +$1,920 | | 1,717: **+$11,084** / +$8,200 |

**Periods:**
- **MNQ months, R4 at 1 tick:** Jul −$640, Aug +$335, Sep +$1,350, Oct +$1,916.
- **MNQ months, R2 at 1 tick:** Jul −$431, Aug −$565, Sep +$726, Oct +$833.
- **NQ years:** R2 beats R4 in 4 of 11 years at both slippages (2017, 2019, 2024, 2025).
- **2023 to 2025-06** (the span of the quoted tests): R2 $5,804 (PF 1.16) against R4 $4,845 (PF 1.09).
- **2025 to June:** R2 +$141, R4 −$128.
- So the quoted tests' result does show here for 2023-2025, but not over the whole decade, and not on MNQ in 2026.

**The evaluation at these settings:** 2 MNQ with $70 risked a trade rarely makes $3,000 in 30 days, so almost every
start expires. Path-dependent NQ windows (99 R4 and 15 R2 at 1 tick) are counted apart.

## 3. Against the criteria

| Criterion | Result |
|---|---|
| Q1: R2 net positive at 1 and 2 ticks, MNQ and NQ | Pass |
| Q2: R2 net ÷ intraday drawdown higher than R4's | **Fail** (MNQ 0.29 vs 1.76, 0.57 vs 1.62; NQ 6.85 vs 7.56, 4.81 vs 5.60) |
| Q3: the trades the limit removes are net negative | **Fail**: they made +$2,399 / +$1,920 (MNQ) and +$11,084 / +$8,200 (NQ) |
| Q4: R2's chance of passing ≥ R4's, breaches no more | **Fail** on passes (MNQ 0 vs 1; NQ 2.8% vs 8.4%, 2.5% vs 7.8%); breaches are fewer |
| Q5: R2 ahead in ≥ 7 of 11 NQ years | **Fail** (4) |

## 4. Candidate C's shutdown, as separate outcomes (MNQ, 44 fully observed starts; `outcomes_by_start.csv`)

| | Passed | Breached | Expired, still able to trade | Unable to fund another trade under the reserve, then expired |
|---|---:|---:|---:|---:|
| Frozen B, 1 and 2 ticks | 24 | 6 | 14 | 0 |
| C, 1 and 2 ticks | 18 | 0 | 20 | 6 |

**How the outcomes line up:**
- The six starts B breached (7/20 to 7/27) are the six in which C became unable to fund a trade.
- The real trailing threshold was kept: highest equity including open P/L, never reset.
- On NQ (earlier round), C had 1,202 accounts unable to fund a trade out of 2,641 starts; B breached 1,602.

**C's execution fixes** (each with a test that fails without it):
- a partly filled entry's remainder stays tracked and is cancelled if the position closes first;
- losing positions are counted by entry order, so a position filled in two parts counts once;
- a peak reached inside the bar in which a position exits at its stop or target is captured.

They changed no outcome in the MNQ replay.

## 5. Historical fill assumptions and what stays uncertain

- **Stand-in simulator (NinjaTrader code):**
  - Market orders fill at the next bar's open ± slippage.
  - Stops fill at the stop ± slippage, or at the open if the bar opens past it.
  - Take-profits fill when the bar trades a tick through. When a bar reaches both, the stop comes first.
  - A bracket sent with the entry can fill on the fill bar.
  - On MNQ 12-26 it reproduced native NinjaTrader for B: 20 of 20 trades at 0 ticks, 19 of 20 at 1-2 ticks, totals to
    the cent.
- **Pine interpreter (the .pine source):**
  - Market orders fill at the next bar's open ± slippage.
  - On the fill bar only the stop is checked (worst case).
  - Limits fill a tick through (`backtest_fill_limits_assumption = 1`). No bar magnifier.
- **Evaluation replay:**
  - Each bar is tried in four intrabar orders. A window whose outcome depends on the order is reported apart.
- **Unresolved:**
  - The order of the high and the low inside a 1- or 5-minute bar is unknown.
  - The stand-in takes the stop first.
  - C counts a bar's best price as reached before an exit in that bar. That is the cautious choice for the trailing
    threshold, and it can overstate the threshold's rise.
  - No native NinjaTrader run of the 5-minute reference exists yet, so its fills are the stand-in's until one does.

## 6. Verdict

**The two-loss limit is rejected; R4 stays the Pine reference.**
- **Improved:**
  - the worst day ($150 against $300);
  - the NQ losing streak (15 against 23);
  - fewer evaluation breaches;
  - a slightly higher profit factor on NQ;
  - better results in 2023 to 2025.
- **Deteriorated:**
  - net profit (MNQ −81% at 1 tick, NQ −25%);
  - net relative to intraday drawdown (on both data sets);
  - the chance of passing (NQ 8.4% → 2.8%);
  - frequency (1.73 → 1.09 trades per eligible session on MNQ).
  - The trades it removes were winners on balance.

**Against the user's requirements:**
- **R4 (the reference):**
  - It has positive expectancy after costs: $26.68 a trade on MNQ (development data), $8.37 on NQ.
  - It averages 1.7-2.1 trades per eligible session, slightly above the preferred 1-2, but in bursts: 42-58% of
    sessions have none and about a third have 3 or more.
  - At 2 MNQ it is not an evaluation strategy: 1 pass in 44 MNQ starts, 8.4% on NQ, most expiring.
- **Frozen B** (4 MNQ, $200, 1-minute) remains the stronger NinjaTrader version for the evaluation: 24 of 44 MNQ starts
  passed, 31.6% on NQ, but 61% of its NQ evaluations breach.
- **Nothing here meets all the requirements.** The references are kept unchanged; no weaker replacement is offered.

## 7. Needed from the user (once)

For the TradingView-to-NinjaTrader trade-by-trade reconciliation:
1. **TradingView:** the Strategy Tester's **List of Trades** export, with a screenshot of the inputs and properties.
   - Pine v1.5 on MNQ1! (or MNQZ2026), 5 minutes, preset R4 (`release/PineReference_v1.5/PRESETS.md`), 7/1 to
     10/17/2026.
   - If your saved inputs differ from R4, export with your saved inputs instead.
2. **NinjaTrader:** the Strategy Analyzer **Trades** export and the NinjaScript Output for the same dates, preset
   PINE-REF-4L, slippage 1.
