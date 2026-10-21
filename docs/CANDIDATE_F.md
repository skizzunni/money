# Candidate F: pre-registration (October 21, 2026)

**Committed before any F code or F result exists.**

**Sources:**
- The user's instructions of 10/21:
  - "New candidate F … Single change vs E: stop = beyond the FVG far edge + 2 ticks (invalidation), not the sweep
    extreme. Everything else identical …";
  - the follow-up, "Proceed with Candidate F as a preregistered, single-change experiment …".
- The attachment named in the first message did not reach the session. Everything below comes from the two messages'
  text and from E's committed protocol (docs/CANDIDATE_D.md, commit d35c6c0). Where a choice had to be made, it is
  marked **[declared here]**.

**D, D + E1 and D + E2 remain rejected.** Nothing of D or E is retuned. D is kept unchanged as a research component of
the combined book; it is not a deployment candidate on its own. Frozen B v1.1 remains the reference.

## The question

**Does replacing E's sweep-extreme stop with the confirmed FVG far-edge stop do two things?**
- make enough setups executable under the existing two-contract/$125 budget;
- improve the combined book enough to pass the unchanged gates.

**Affordability alone is not acceptance.** If F makes more setups affordable but the combined book fails a gate, F is
rejected.

## 1. The single change

**An initial-stop reference setting** (Python `DConfig.e_stop`, NinjaScript property `SweepStop`):

| Setting | Initial stop of a sweep setup |
|---|---|
| `extreme` (E, unchanged) | The sweep extreme − d × 0.1 × ATR14, rounded away from the entry to the tick |
| `fvg` (F) | The selected FVG's far boundary − d × 2 ticks (0.50 point), rounded away from the entry to the tick |

d is +1 for a long and −1 for a short.

**The far boundary:**
- E's FVG in complete five-minute bars k−2, k−1, k:
  - **bullish** when low[k] > high[k−2], the gap spanning high[k−2] to low[k];
  - **bearish** when high[k] < low[k−2], the gap spanning high[k] to low[k−2].
- **For a long** (a bullish gap), the far boundary is the gap's lower boundary, high[k−2]. The stop is high[k−2] − 0.50.
- **For a short** (a bearish gap), it is the gap's upper boundary, low[k−2]. The stop is low[k−2] + 0.50.
- The entry stays at the proximal boundary: low[k] for a long, high[k] for a short.

**Rounding is E's convention, unchanged:**
- The boundary is converted to the decision bar's prices (× that bar's scale factor; 1 on MNQ).
- The 2 ticks are subtracted (long) or added (short).
- The result is rounded **away** from the entry to the tick: down for a long, up for a short, with E's 1e-7
  tolerance.
- The limit price keeps E's rounding: down for a long, up for a short.
- On MNQ the boundary is on the grid and no rounding occurs. On rescaled NQ, a boundary carried across a month boundary
  can be off the grid. An exact half tick then rounds away as well.

**Frozen at the decision:**
- The FVG is the one E selects: the most recently completed qualifying gap at the decision, with E's qualification
  unchanged.
- Its far boundary and the stop are fixed when the setup arms (the decision, when the limit is placed).
- The stop is never widened, never moved to another zone, and never recomputed after the entry.
- Afterwards it moves only by the unchanged breakeven and trail rules, which only tighten.

**Everything else is E's committed protocol, unchanged:**
- the pools and their priority;
- penetration, reclaim, BOS reference, BOS and FVG timing;
- session and news exclusions (decisions 09:45-15:00; no sweep setups on FOMC, NFP and skip days);
- the room multiple;
- entry mechanics (a limit at the proximal edge, from the next bar; a fill when price trades a tick through it or
  opens past it);
- the pending order's expiry and cancellations;
- the breakeven, the half and the runner trail;
- costs, portfolio priority (noise, then Williams, then sweep), one position or pending entry at a time, at most three
  campaigns a day, and two contracts or nothing.
- The runner keeps no fixed target.

## 2. The quantities that depend on the initial risk

**Every quantity derived from R uses F's stop.** E's sweep-based R is not kept anywhere.

**R** = d × (limit − F's stop), in points.

**The size rule:**
- planned all-in risk = 2 × (R × $2 + 2 × $0.95 + 2 ticks × $0.50) ≤ $125;
- otherwise the setup is skipped. This means R ≤ 29.75 points.
- The quantity is never raised to spend unused budget, and never lowered to one contract.

**Each of these takes F's R:**
- **the +1R breakeven trigger:** a completed bar's extreme reaches fill + d × R;
- **the +2R half:** the take-profit at fill + d × 2R, in ticks from the fill (`round(2R / tick)`, exact on the grid);
- **the runner trail:** best − d × 1R after the half;
- **the room test:** the nearest unpenetrated opposing pool of the set at least 2R + 1.45 points from the limit;
- **the pending entry's cancellations:** "ran away" at limit + d × 2R, "stop traded" at F's stop.

**Eligibility is E's, unchanged.**
- E has no minimum-risk or maximum-stop rule beyond R > 0 and the budget. None is added or removed.
- F's smallest possible R is 0.75 point: a one-tick gap plus the 2 ticks.

**The ledger records both risks for every position:**
- price risk, R × $2 × 2;
- all-in planned risk.

## 3. Execution feasibility (declared before any F result)

These are E's rules. They are restated because F's tighter stops reach them more often. Each is covered by a synthetic
test on both implementations before any market result is viewed.

**(a) The initial stop:**
- It is sent with the entry and attached to both contracts. It is effective from the fill, as submitted, not before.
- For a long, the limit lies above the stop, so price must trade through the limit before it can reach the stop. A
  stop reached on the fill bar is therefore reached after the fill: the order of events is forced, not assumed.
- **If a bar opens beyond both the limit and the stop** (a gap through the intended stop):
  - the limit fills at that open;
  - the stop is already passed when it is submitted;
  - the contract is closed at that open less the slippage. This is the market close that
    `StopCancelCloseIgnoreRejects` makes of a rejected stop. No fill at the passed stop price is simulated.
- **The count of such positions is reported.**

**(b) The half's target:**
- It does not work on a limit entry's fill bar (E's rule).
- A bar reaching both a stop and the target fills the stop.

**(c) Breakeven at the declared trigger:**
- The trigger is unchanged: a completed bar's extreme at fill + d × 1R. The limit fill bar does not count.
- From the next bar the stop is fill + d × 1.50 points.
- **When R < 1.50, the breakeven stop lies beyond the trigger price.**
  - It is placed only if it is strictly on the protective side of the bar's close (a sell stop below the close).
  - If not, it cannot legally be placed. The position is then closed at market at the next open ("Stop passed"), as
    E's protocol already specifies (docs/CANDIDATE_D.md section 1).
- Neither the trigger nor the 1.50 offset is changed, and no stop is simulated at a price the market has already
  passed.
- **The count of "Stop passed" exits, and their net, is reported.**

**(d) The trail** is held to the same placement rule.

**(e) Partial entry fills:**
- If one contract's limit fills and the other's does not, the other is cancelled.
- The filled contract is managed alone (its own target if it is the half) and is one campaign.

**(f) Event order:**
- An entry filled before its cancellation is confirmed is a real position and is managed.
- A new entry is never placed while a cancellation is pending.
- Stops are effective from their submission bar, never retroactively.

**(g) Budget boundary:**
- R 29.75: $124.80, taken.
- R 30.00: $125.80, skipped.

## 4. Parity (only for the new behaviour)

The completed D/E infrastructure is reused:
- `research/d_parity.py`;
- `tests/test_candidate_d.py`;
- the stand-in's limit entries and exit executions.

**What is added:**
- **Configurations** D + F1, D + F2 and F only (code coverage), on the user's MNQ bars (fixture sha256 `66169bfa…`), at
  $125 and at the test-only $2,000 budget.
- **Synthetic F sequences, hand-computed:**
  - the FVG selected, the rounded entry and stop, both directions;
  - an off-grid boundary with the half-tick case;
  - the budget boundary;
  - R, the breakeven activation and the "Stop passed" case at R < 1.50;
  - the partial exit at +2R and the runner's exit, net P/L;
  - a gap through the stop;
  - one contract of two filled;
  - a fill during a pending cancellation.
- **Python and NinjaScript must agree position by position** on all of them. The ledger fields compared are the
  sleeve, direction, entry kind, signal, fill and exit bars, each contract's fill, exit and reason, the stop, R, planned
  risk and net P/L.

**Hashes and order:**
- Before any F result on the evaluation data is viewed, the sha256 of the Python model, the NinjaScript strategy,
  the stand-in, the evaluation replay, the setup-ledger script and the exact configurations are recorded below in
  "Frozen sources", in their own commit.
- The parity tests compare the two implementations' fields for equality and do not total them.

## 5. The candidates and what is judged

| Name | Sleeves | Judged |
|---|---|---|
| Reference | Frozen B v1.1 | Reference only |
| D | Noise + Williams (frozen) | Reference only (rejected) |
| **D + F1** | D + F on the higher-timeframe pools (previous day, previous week) | **Gates G1-G5** |
| **D + F2** | D + F on the higher-timeframe pools, then the session pools (E's priority) | **Gates G1-G5** |
| F1 only, F2 only | F alone, no noise or Williams | Diagnostic (required), not judged |

**E1 pools first:**
- D + F1 is the first stage.
- D + F2 adds the session pools behind E1's in E's priority, as D + E2 did.
- **[declared here]** Both are judged, each against all five gates, as D + E1 and D + E2 were.
- Each book is run whole, with the existing scheduler. No result is estimated by adding standalone profits or by
  deleting trades.

## 6. Data, starts and costs (as D/E)

**NQ decides the gates** with MNQ-equivalent $2-a-point economics:
- `nq1m_scaled.pkl` (sha256 `89c0b157…`), 2015-03-02 to 2025-06-30, the same 2,571 eligible sessions as D/E;
- the same evaluation starts: 124 non-overlapping (123 fully observed) and 2,552 fully observed overlapping;
- **[declared here]** this is the same series D/E were judged on, so that F is compared with E on the same data.

**MNQ is the execution check:**
- the user's exports, 7/20 to 10/16/2026, as D/E: 3 non-overlapping starts, 42 overlapping;
- not deciding.

**The roll sensitivity (docs/NQ_ROLLS.md) [declared here]:**
- The deciding series is unadjusted at the contract rolls, found in this round.
- Frozen B, D, D + F1 and D + F2 are also run on the ratio back-adjusted series (`nq1m_scaled_roll_adjusted.pkl`,
  sha256 `0a61966c…`), with the same starts, and reported beside the deciding run.
- If it changes any gate's pass or fail, that is stated with the verdict. The verdict itself is taken on the deciding
  series.

**Costs:**
- $0.95 a side a contract;
- slippage 2 ticks (the base, which decides) and 3 ticks (the stress, reported) on every market and stop fill;
- no slippage on limit fills.

**This is development data, all of it.**

## 7. Gates (unchanged; NQ, non-overlapping starts, 2 ticks; all must pass)

| Gate | Requirement | Measured as |
|---|---|---|
| G1 | Evaluation pass rate ≥ 60% | passes ÷ fully observed non-overlapping starts; a path-dependent window is never a pass |
| G2 | Expiry ≤ 15% | expired ÷ the same starts |
| G3 | Worst window drawdown ≤ $1,500 | as D/E (open P/L included, worst intrabar path) |
| G4 | Win rate ≥ 50% | completed positions with net > 0 ÷ all completed positions, continuous run; scratches (\|net\| < 0.1R) and the win rate without them reported beside it |
| G5 | Profit factor ≥ 1.35 | gross profit ÷ gross loss, continuous run |

**The replay** is `research/eval_d.py`, unchanged: $3,000 target, $2,000 trailing threshold of the highest equity
including open P/L, 30 calendar days, four intrabar orders.

**Every denominator is reported, with every gate's measured value and PASS / FAIL.**

**Verdict:**
- D + F1 (or D + F2) is accepted only if all five gates pass at 2 ticks on the deciding NQ series, with parity
  established.
- Otherwise it is rejected, and each failed gate is named.
- Nothing is retuned. No further variation is launched.

## 8. Where an improvement comes from (reported)

**The setup ledger, before affordability and portfolio gating:**
- Every sweep decision on NQ and on MNQ. The chain up to the decision is identical under E and F, so they are the same
  decisions.
- **For each:** its pool, direction, decision time, FVG, limit, and E's and F's stop, R, price risk and planned risk.
- **Classes:**
  - affordable under both stops;
  - **newly affordable under F;**
  - affordable under E only;
  - affordable under neither;
  - excluded by the other unchanged rules: the decision window, and the room test under the stop concerned;
  - **displaced in the combined book:** a position or pending entry already open, the day's three campaigns used, the
    session's close, or a higher-priority sleeve's entry (or an earlier sweep setup) on the same bar.

**Matched entries:**
- Every decision is also replayed alone, outside the portfolio and without the budget, once with E's stop and once
  with F's, under the same position manager and cancellations. This is a diagnostic, never a filter.
- Matched entries are the decisions filled under both.
- **On them:**
  - initial-stop exits;
  - +1R and +2R attainment;
  - net $ per position;
  - costs as a percentage of the initial price risk:
    - declared: 2 × $1.90 commission + 2 × 2 ticks allowance, ÷ R × $4;
    - realized: commission plus the slippage actually paid.
- These are shown for all matched entries, and for those affordable under both stops.
- **[declared here]** "F stopped out, E succeeded": the matched entries where F's position ended at its initial stop
  while E's position on the same setup closed with net > 0. Reported as a diagnostic only.

**Reported beside the gates** (each book; NQ, then MNQ; 2 and 3 ticks), as D/E:
- net expectancy, average win and loss in R;
- intraday drawdown; evaluation pass / breach / expiry;
- trades per eligible session, zero-trade sessions, entries a day;
- yearly results, profit factor, the dependence on the largest winners;
- each sleeve's contribution and the profitable trades it displaces;
- planned and realized risk, the overruns;
- the "Stop passed" and gap-through-stop counts.

**The three questions are answered separately:**
1. Did F materially increase executable setups?
2. Did it improve net dollar expectancy and evaluation outcomes?
3. Did the combined book satisfy the pre-registered acceptance rules?

## 9. What ran where

- **The results are the Python model's,** parity-checked against `MnqCandidateD.cs` on the NinjaTrader stand-in.
- Native NinjaTrader has not run D, E or F. No forward simulation has run.
- The preset states the native settings for the user's own check: a granular fill resolution and a Playback forward
  run.

## Frozen sources

**Recorded after the parity extension and before any F result on the evaluation data was viewed.**
- No D + F or F run on NQ or on the MNQ execution-check data had been made when this was committed.
- The MNQ parity tests run the F configurations on the user's MNQ fixture, but they only compare the two
  implementations field by field.

**Code and configuration (sha256):**

| File | sha256 |
|---|---|
| `mnqbot/candidate_d.py` (the model; `DConfig.e_stop`, `sweep_prices`, `room_ok`) | `7deeb8b206d8127fd70f13d0014ecdf6e3a5326aedf20ba9beaef28913cbbb05` |
| `ninjatrader/Strategies/MnqCandidateD.cs` (`SweepStop`) | `88fa86ba71ce353cc554a51143183509bed55f154ebb789eb2fea9d0cc5164e3` |
| `ninjatrader/AddOns/MnqNoiseEngine.cs` (unchanged) | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` |
| `ninjatrader/tests/Sim/NinjaTraderStubs.cs` (unchanged) | `2a9d61bbca64bbed4ad2c0f04e98143e4d448cb748e38e64db4437b8c9b4dc5a` |
| `ninjatrader/tests/Sim/Program.cs` (enum properties) | `ecf597d0a263bf069c9b8703e0f2b7ad3c652850878efd16b157cea846d42c62` |
| `research/eval_d.py` (`--f`: `F_CANDIDATES`, `F_STAGES`) | `11ff5aa1174705e4a3c58802c546ce7e4e561171b0129e60fb467d99c06031ee` |
| `research/f_setups.py` (setup ledger, matched entries, execution counts) | `7a3d92f159db9ff0acbbc0c69a2254dccea51c58434477e7da2ca8c7e18fcb59` |
| `research/d_parity.py` (F configurations) | `7479ae34c099f017180996805fcfc22609a49fa85b114d1bdaba560b2eeb1113` |
| `research/nq_rolls.py` | `6e34689c19cc49d388fb8050132b49c11bda2621b87ea79921983e29c27d6b13` |
| `tests/test_candidate_f.py` | `9870a857d358fc248d4e9dbff91d824ecd0418c78c3795bf0b48d6f4d1d0f08e` |
| `tests/test_candidate_d.py` | `636a9bef009fd4a3f3054c38da1462a3400dc11b64c02e7d44006d07adf5f69a` |
| `release/MnqCandidateD_candidate/PRESET_F-CANDIDATE.md` | `3545d5f58faec6d70067ffdc4d7c63c14d40799ac374be8acae3ae1184b16eaf` |
| `release/MnqCandidateD_candidate.zip` | `e997bc06a7254cbf9b3fc55ff912c5a34e5a4b8a669bd644e9b9d3ee7b217b3a` |
| `research/fomc_dates.csv` / `research/nfp_dates.csv` | `da11aadf…` / `20c7ed23…` |

**The configurations** (`research/eval_d.py`, `F_CANDIDATES`; all with the `DConfig` defaults, $125, 2 / 3 ticks):

| Book | Configuration |
|---|---|
| D | `{}` |
| D+F1 | `{"e1": True, "e_stop": "fvg"}` |
| D+F2 | `{"e1": True, "e2": True, "e_stop": "fvg"}` |
| F1 only | `{"noise": False, "williams": False, "e1": True, "e_stop": "fvg"}` |
| F2 only | `{"noise": False, "williams": False, "e1": True, "e2": True, "e_stop": "fvg"}` |

The NinjaScript equivalent is the same switches with `SweepStop=FvgFarEdge` (PRESET_F-CANDIDATE.md).

**Data (sha256):**

| Data | sha256 |
|---|---|
| NQ, deciding: `nq1m_scaled.pkl` | `89c0b157f826853f9ffa7e3e22e4e08f3e4b31d5e1492824ffc06a35fc083328` |
| NQ, roll sensitivity: `nq1m_scaled_roll_adjusted.pkl` | `0a61966cb3a527ad0287615e5a5ab029feccf957709d8417e85eecfe5e899e7d` |
| MNQ: `MNQ_09-26.Last.txt` / `MNQ_12-26.Last.txt` (the user's exports) | `bddc9a52…` / `6a1cfb21…` |
| Frozen B on the stand-in: the B v1.1 `Sim.dll` used for D/E | `3fffd5d0e1cdb43f5de3f88239635b92052d4d7b70e9676e93e2f3a76f573cd1` |

**Parity evidence at this commit:**
- `tests/test_candidate_d.py` (22 tests) and `tests/test_candidate_f.py` (15) all pass: 43 of 43.
- The MNQ parity covers seven configurations (D, D + E1, D + E2, E only, D + F1, D + F2, F only) × $125 and $2,000:
  14 of 14 identical position by position.
- The D/E results are unchanged by the extension. The E tests, and the E configurations' MNQ parity, give the same
  positions as before.
