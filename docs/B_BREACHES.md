# Frozen B's evaluation breaches, and one candidate from them (October 20, 2026)

**Labels.**
- **MNQ, primary:** the user's MNQ bars (traded contracts), frozen B on the simulator. The simulator reproduces native
  NinjaTrader's B trades over this period (docs/B_NATIVE.md).
- **NQ, supplementary:** rescaled NQ futures 2015-03 to 2025-06, priced at MNQ's $2 a point. It is a robustness check
  only. Its dollars are not MNQ results.
- **Settings:** 4 MNQ, $200 max loss, $0.95 a side, 1 tick, the evaluation replay's worst-mix path
  (`research/eval_sim.py`). Script: `research/b_breaches.py`; per-trade sequences in `verification/b_breaches/`.

## 1. Diagnosis (executed)

### MNQ: 44 fully observed starts (7/20 to 9/17): 24 pass, 6 breach, 14 expire

**The six breaches are two overlapping episodes inside one stretch, 7/23 to 7/30.**

| Starts | Highest equity, where set | Fall to the breach | Give-back in that trade | Losers after it | Winners after it | Breach trade's open loss |
|---|---|---:|---:|---|---:|---:|
| 7/20, 7/21, 7/22, 7/23 | $1,310.20: 7/23 11:00 short, 1.46 noise units in its favour (164 of its 169-point target), closed at the line for +$30.40 | $2,038.40 | $1,279.80 (63%) | 5, −$1,048.00 | +$495.20 | −$205.80 |
| 7/24, 7/27 | $978.20 / $755.00: 7/27 11:30 short, 0.70 noise units in its favour, closed at the lock for +$10.40 | $2,145.60 | $723.80 (34%) | 6, −$1,257.60 | +$41.60 | −$205.80 |

**Over the six starts:**
- give-back is 53% of the fall;
- losers closed after the peak are 54%, each a full −$209.60 at the max-loss stop;
- the open loss in the breach trade is 10%;
- winners after the peak offset 17%.

**Every loser after the peak was stopped within one minute of its entry.** That is not unusual for B: 48% of all its
MNQ losers are, and all of them exit at the max-loss stop. The noise was not unusual either: the July median noise
unit was 132 points, against 167 in August, a profitable month.

### NQ (supplementary): 2,641 fully observed starts: 835 pass, 1,603 breach, 203 expire

- The breaches come from 373 distinct episodes.
- The fall splits into:
  - give-back 34%;
  - losers after the peak 62%;
  - the breach trade 7%;
  - winners after the peak −7%.
- The trade that set the peak had a median best of 0.75 noise units. Only 32% reached 1.0 or more.
- 44% of the losers after the peak were stopped within a minute.

**So the MNQ episode is not typical of NQ's breaches.** On MNQ, half of the fall is open profit the account gave
back. On NQ, most of it is ordinary full-size losers. One episode is all the MNQ data holds.

### What has been tried against each component before, on substitute data (docs/RESULTS.md, docs/DEVELOPMENT.md)

- **Give-back:**
  - trailing stops instead of the lock (round 85);
  - a 1R trail (round 138);
  - B2, a second lock at 2R → entry + 1R, pre-registered on frozen B (DEVELOPMENT.md).
  - All were rejected: they cut the large winners. B2 cut NQ validation net by a third and passes from 33% to 25%.
- **Losers in clusters:**
  - sitting out after losing days, and trading only after good recent results (round 78);
  - half size on a thin cushion (round 115).
  - All were rejected: busts fell, but evaluations then ran out of time, and fewer passed.
- **None of them was run on MNQ,** and only B2 on frozen B's current code.

## 2. Pre-registration (committed before the candidate is built or run)

**Control:** frozen B, unchanged (preset B-NATIVE-v1, docs/B_NATIVE.md), on the simulator.

**The one change, candidate B3 ("noise lock"):**
- **Trigger:** a position's best price reaches **1.0 noise unit** from its fill. This is two thirds of the way to its
  1.5-unit take-profit.
- **Effect:** from the next bar, its stop is at least **the fill + 0.5 noise unit**, a third of the target distance
  kept.
- **The noise unit** is the one the take-profit uses at that bar: the engine's Sigma × the fill price.
- **Arming:** the same as the existing lock, from a bar's high or low. Tighten-only applies as before.
- **Everything else is B's.** The parameters (1.0, 0.5) are in the take-profit's own units and chosen as round
  fractions of it. No other values will be run.
- **Code:** a patch on a copy of B's two files (`verification/candidate_b3.patch`). The frozen files stay unchanged.

**Mechanism:**
- On an intraday trailing threshold, open profit raises the threshold whether or not it is kept.
- Of the account peaks behind B's MNQ breaches, 4 of 6 were set by a trade 1.46 noise units in profit that closed at
  +$30.
- Keeping half a unit of such a trade raises equity without raising the peak.

**Expected cost:**
- Trades that reach 1.0 unit, fall back past 0.5 and then go on to the take-profit (or to a larger 16:00 exit) are
  cut.
- These are the large winners that earlier give-back rules lost.

**Expected reach:**
- It cannot touch the 7/24 and 7/27 breaches: their peak trade reached 0.70 units.
- On NQ, only 32% of breach peaks reached 1.0 unit.

### Data and chronology

**MNQ, primary:**
- 7/20 to 10/16 (64 eligible sessions), in two parts:
  - **7/20 to 8/31**, development: it contains the episode the candidate comes from;
  - **9/1 to 10/16**, later: not used in this diagnosis, but seen in earlier rounds.
- Evaluation: the 44 fully observed starts (7/20 to 9/17), paired start by start, and among them the 12 later starts
  (9/1 to 9/17).

**NQ, supplementary:** 2015-03 to 2025-06, year by year. It is labelled; no NQ dollar is quoted as MNQ.

**Costs:** $0.95 a side; 1 and 2 ticks. Both arms are complete reruns with the same data, warm-up and settings.

### Acceptance criteria (all must hold; otherwise B3 is rejected and B stays as it is)

1. **MNQ profit:** net after costs at least B's at 1 and 2 ticks, over 7/20 to 10/16 **and** over 9/1 to 10/16.
2. **MNQ profit against risk:** net ÷ maximum intraday drawdown (continuous equity with open P/L, worst-mix path)
   higher than B's at 1 and 2 ticks.
3. **MNQ evaluation** (44 paired starts):
   - fewer breaches **and** at least as many passes, at both slippages;
   - no start goes from pass to breach;
   - on the 12 later starts, no fewer passes and no more breaches.
4. **Frequency:** trades per eligible session at least 95% of B's.
5. **NQ must not contradict** (supplementary), at 1 and 2 ticks:
   - net ÷ intraday drawdown higher over the whole period, and in at least 6 of the 11 years at 1 tick;
   - evaluation pass rate no lower and breach rate lower.

**Reported whatever the verdict:**
- **Each trade whose exit changed:** B's and B3's P/L, split into
  - winners sacrificed (B3 made less: count and $);
  - losses prevented or profit kept (B3 made more);
  - knock-on trades, taken by one arm only.
- **Each changed evaluation start:** what changed and why.

**Adoption, even if every criterion holds, needs:**
- a native NinjaTrader run of B3 reconciled as in docs/B_NATIVE.md;
- a forward test.
- The MNQ test period contains the episode the change was drawn from.

# 3. Results (executed after the pre-registration, commit 01b7401)

**Code check:**
- With NoiseLockAt 0, B3's simulator reproduces frozen B trade for trade (97 of 97, MNQ, 1 tick).
- The patch is `verification/candidate_b3.patch`. Results are in `verification/b3_mnq/` (primary) and
  `verification/b3_nq_supplementary/`.
- **All of these are simulator results. B3 has had no native NinjaTrader run.**

## MNQ (primary): 64 eligible sessions, 7/20 to 10/16

| | B, 1 tick | B3, 1 tick | B, 2 ticks | B3, 2 ticks |
|---|---:|---:|---:|---:|
| Trades; per eligible session | 97; 1.52 | 104; 1.62 | 97; 1.52 | 104; 1.62 |
| Net after costs | $13,218.80 | $14,295.60 | $13,030.80 | $14,097.60 |
| 7/20-8/31 / 9/1-10/16 | $2,992 / $10,226 | $3,777 / $10,519 | $2,906 / $10,124 | $3,689 / $10,409 |
| Profit factor | 2.58 | 2.62 | 2.54 | 2.59 |
| Intraday drawdown (open P/L) | $2,612.80 | $2,311.20 | $2,652.80 | $2,335.20 |
| Net ÷ intraday drawdown | 5.06 | 6.19 | 4.91 | 6.04 |
| 44 paired starts: pass / breach / expired | 24 / 6 / 14 | **24 / 6 / 14** | 24 / 6 / 14 | **24 / 6 / 14** |
| 13 later starts (9/1-9/17): pass | 13 | 13 | 13 | 13 |

**Every start has the same outcome in both arms, at both slippages.** (The later part has 13 starts: 9/7 has bars and
counts as a session. The pre-registration said 12.)

**Trades changed (1 tick):**
- **Five exits changed, all for the better:** +$1,454.00.
  - 7/23 11:00: +$30.40 → +$440.40
  - 7/24 10:30: +$10.40 → +$384.40
  - 9/8 10:00: +$10.40 → +$298.40
  - 9/23 11:00: +$412.40 → +$566.40 (B held it to 16:00)
  - 10/12 10:00: +$98.40 → +$326.40
- **Winners sacrificed on MNQ: none.**
- **Knock-on:** 7 trades taken only by B3 (its earlier exits freed the strategy to enter again): −$377.20, including
  two −$209.60 losers on 10/12.

**Why the breaches stayed** (`verification/b3_mnq/breach_sequences_B3_1t.csv`):
- Keeping +$410 on 7/23 and +$374 on 7/24 raised the account's equity.
- The next open profit then set a **new, higher peak**: $1,793 instead of $1,310. That was the 7/27 11:30 short, at
  0.70 noise units, below the lock's trigger.
- The same eight $209.60 stops followed, and the account breached in the same trade (7/30 11:00).
- On an intraday trail, profit kept before the peak moves the threshold up by the same amount. Only what happens after
  the last peak decides.

## NQ (supplementary; rescaled NQ priced at MNQ's $2 a point, not MNQ results): 2015-03 to 2025-06, 2,571 sessions

| | B, 1 tick | B3, 1 tick | B, 2 ticks | B3, 2 ticks |
|---|---:|---:|---:|---:|
| Net | $111,174 | $106,298 | $91,757 | $89,339 |
| Profit factor | 1.22 | 1.21 | 1.18 | 1.17 |
| Intraday drawdown | $13,444 | $14,468 | $15,146 | $15,595 |
| Net ÷ intraday drawdown | 8.27 | 7.35 | 6.06 | 5.73 |
| Years with a higher net ÷ intraday DD (of 11) | | 6 | | 6 |
| 2,641 starts: pass / breach / expired | 834 / 1,602 / 203 | 849 / 1,579 / 211 | 794 / 1,643 / 196 | 808 / 1,612 / 212 |

**Paired starts at 1 tick:**
- 68 went from breach to pass, 53 from pass to breach;
- 17 from expired to breach, 24 from breach to expired.

**Trades changed at 1 tick:**
- **Winners sacrificed:** 86 trades, −$66,110. B made $112,410 on them; B3 made $46,300.
- **B3 made more on** 137 trades: +$52,894.
- **Knock-on:** +$5,804 net.

## Against the criteria

| # | Criterion | Result |
|---|---|---|
| 1 | MNQ net ≥ B, all and 9/1-10/16, 1 and 2 ticks | Met (+$1,077 / +$1,067; later part +$292 / +$284) |
| 2 | MNQ net ÷ intraday DD higher, 1 and 2 ticks | Met (6.19 vs 5.06; 6.04 vs 4.91) |
| 3 | MNQ: fewer breaches and passes no fewer | **Failed:** 6 breaches in both arms, 24 passes in both, at both slippages |
| 4 | Frequency ≥ 95% of B's | Met (1.62 vs 1.52) |
| 5 | NQ does not contradict | **Failed:** net ÷ intraday DD lower over the whole period (7.35 vs 8.27; 5.73 vs 6.06); 6 of 11 years. Passes +0.6 points and breaches −0.9 points. |

## Verdict: B3 is rejected. Frozen B is unchanged.

- **On MNQ, B3 makes more money for less intraday drawdown.** It does not change a single evaluation outcome, so it does
  not address what breaches B.
- **On NQ it gives up more in sacrificed winners than it keeps,** the same pattern as every earlier give-back rule.
- **What the diagnosis leaves:**
  - B's MNQ breaches are a cluster of full-size losers after the last peak;
  - the earlier countermeasures to that (round 78's filters, round 115's cushion sizing) traded breaches for
    expirations.
- **No further candidate is proposed from this one MNQ episode.**
