# Decision, October 20, 2026: frozen B, the Pine reference, and the candidates

Software correctness, continuous profitability and evaluation suitability are judged separately below. None of them
stands in for another.

## 0. Data, labels and units

**MNQ is the primary data for every selection and evaluation result here.**
- **The user's NinjaTrader exports:**
  - MNQ 09-26: 6/28 18:00 to 9/11 16:59 (New York);
  - MNQ 12-26: 9/10 to 10/16 16:59.
- **Traded-contract series:** 09-26 to the 9/10 session, back-adjusted by +284.50 points, then 12-26.
- **Warm-up:** 6/29 to 7/17, 14 full sessions.
- **Tested:** 64 eligible sessions, 7/20 to 10/16.
- **Evaluation:** 44 fully observed 30-day starts (7/20 to 9/17), plus 21 later starts whose window runs past the end
  of the data. Those are reported apart.
- **Native NinjaTrader DEC26:** data from 5/3, with a hole from 5/22 to 6/26.

**The limitation, stated plainly:**
- **Only 3.6 months of MNQ.** The 44 starts overlap: they are about 3 independent 30-day windows.
- **It is development data.** It is the period whose results chose B. No untouched MNQ history exists here: 03-26 and
  06-26 were not exported.
- **A conclusion about the evaluation cannot be settled on MNQ alone,** and it is not settled here.

**NQ is supplementary only.**
- Rescaled NQ futures, 2015-03 to 2025-06 (Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet`), priced at MNQ's $2 a
  point.
- Each month is rescaled to a 30,661 level, so 2023 points are multiplied by 1.34 to 2.76.
- It is labelled wherever it appears. Its dollars are never MNQ results.

**Units:** `tests/test_mnq_units.py` checks $2 a point, $0.50 a tick and $0.95 a side in every component that prices a
trade:
- the NinjaTrader strategies on the simulator (B and C), with every price on the 0.25 grid;
- the Python reference and the Pine source in the interpreter (point value 2, tick 0.25);
- the evaluation replay's equity and drawdown (3 contracts, a 6-point fall = $36);
- C's planned risk: a 25-point stop is $53.90 a contract, 4 ticks = $2.00.

B's sizing is 4 MNQ × 25 points × $2 = $200 at the max-loss stop.

## 1. Software correctness

**Verified:**
- **Frozen B, native NinjaTrader against the simulator** (docs/B_NATIVE.md).
  - Every simulator trade from 7/20 to 10/16 is a native trade: 97 of 97, with the same entry minute, exit minute and
    exit kind.
  - P/L is within $4.00 a trade. Totals are equal to the cent at 1 tick, ±$10 at 0 and 2 ticks.
  - The contract choice before the roll (DEC26 native, 09-26 in the simulator) changed no trade.
- **Pine v1.5 reference (R4):**
  - The Pine source in the interpreter and the Python reference agree trade for trade (111 trades).
  - Every Pine/NinjaTrader mismatch has a cause (docs/PINE_REFERENCE.md sections 1 and 1b):
    - A, 16:00 exit timing: sign mixed, $0;
    - B, naming only;
    - D, tick rounding: always NinjaTrader's way, cents;
    - C, the fill-bar stop measured from the expected fill or the actual fill. This is a structural rule whose
      outcome depends on the bars: 13 trades better for NinjaTrader and 20 worse at 1 tick, 30 and 11 at 2 ticks.
      Of its −$1,195, −$1,168 is one trade (8/3 10:30), whose low touched NinjaTrader's stop exactly and passed two
      ticks above Pine's.
  - **The gap is not "Pine is optimistic" in general.**
- **Evaluation cohorts** (`verification/cohorts/paired_*.csv`):
  - R4 and R2 use exactly the same fully observed starts: MNQ 44, NQ 2,641. 21 late starts are excluded on each
    side, all for the same reason: the 30 days run past the end of the data.
  - The earlier NQ totals (2,542 against 2,626) left out the path-dependent windows: 99 R4 and 15 R2 at 1 tick.
  - **Paired, MNQ:** R4 1 pass and 43 expired; R2 44 expired. The one R4 pass became an R2 expiry.
  - **Paired, NQ at 1 tick** (supplementary):
    - of R4's 344 breaches, R2 had 296 expired, 44 breached and 4 path-dependent;
    - of R4's 221 passes, R2 had 160 expired, 52 passed, 3 breached and 6 path-dependent.
- **Intraday peak accounting (candidate C):**
  - A position's equity history ends at its exit. A take-profit fill and an opening-gap stop add nothing after the
    fill.
  - A stop inside a bar is reported as bounds: determined at the open, protective at the bar's best price.
  - The entry's pending-order guard is held until the cancellation or completion is confirmed.
  - Each rule has a synthetic test with independently calculated peaks (`tests/test_candidate_c.py`,
    `tests/test_eval_sim.py`), and each test fails when its fix is reverted.
  - Rerun on MNQ: no outcome of B, C0 or C1 changed (`verification/candidate_c_peakfix_mnq/`).

**Not verified:**
- B3 in native NinjaTrader;
- a TradingView List of Trades joined to a native run of the Pine preset;
- the evaluation replay on native DEC26 bars before the 9/10 roll (an optional export, docs/B_NATIVE.md section 4).

## 2. Continuous profitability (frozen B, 4 MNQ / $200, $0.95 a side)

**MNQ, primary** (the simulator, reconciled with native; 7/20 to 10/16):

| | 1 tick | 2 ticks |
|---|---:|---:|
| Trades; per eligible session | 97; 1.52 | 97; 1.52 |
| Net after costs | $13,218.80 | $13,030.80 |
| Profit factor | 2.58 | 2.54 |
| Intraday drawdown (open P/L); net ÷ it | $2,612.80; 5.06 | $2,652.80; 4.91 |
| Months | Jul −$328, Aug +$3,320, Sep +$5,580, Oct +$4,646 | |

- **Native B_L1** (6/29 to 10/16, including the 6/29-7/17 trades the simulator spends warming up): $12,889.20.
- **This is development data.** It is not evidence of future results.

**NQ, supplementary:**
- $111,174 at 1 tick, profit factor 1.22, from 2015-03 to 2025-06.
- Years range from −$2,873 (2025, to June) to +$25,528 (2018); 2017 and 2023 were near zero.

**Verdict on profitability:** positive after costs on both. MNQ has 3.6 months; NQ is a rescaled proxy.

## 3. Evaluation suitability (Apex 50K: $3,000 target, $2,000 intraday trailing loss, 30 calendar days)

| Frozen B, 1 tick | Pass | Breach | Expired | Note |
|---|---:|---:|---:|---|
| MNQ, 44 overlapping starts (primary) | 24 | 6 | 14 | About 3 independent windows. The 6 breaches are one 7/23-7/30 episode. |
| NQ, 2,641 starts (supplementary) | 834 | 1,602 | 203 | 2 path-dependent |

- **On MNQ it passed more often than it breached.** On ten years of NQ it breached about twice as often as it passed.
- **The MNQ sample cannot outweigh that,** and the NQ result is a proxy. **Evaluation suitability is not
  established.**
- **Its breaches** (docs/B_BREACHES.md):
  - MNQ: half is open profit given back, half is full-size losers after the last peak.
  - NQ: about a third is give-back and two thirds are losers.

## 4. The independent tests quoted by the user (item 2): not reproduced, and why

| | ChatGPT's test, as quoted | My figures |
|---|---|---|
| Data | NQ proxy, **unscaled** | NQ futures, **rescaled to 30,661** each month (2023 points × 1.34-2.76) |
| Dates | 2023 to July 2025 (the dataset ends 7/24/2025) | 2023-01-01 to 2025-06-30, a slice of one run started 2015-03 (warm history) |
| Strategy code | Pine v1.5 settings; the execution engine was not stated | NinjaTrader strategy code (MnqNoiseMomentum) on the simulator: bracket from the actual fill (category C above) |
| Chart / size / stop | 5 minutes, 2 contracts, 17.5 points | Same |
| Costs | Not stated | $0.95 a side; slippage 1 and 2 ticks |
| Sessions | Not stated | Sessions with missing minutes skipped; the strategy's skip dates |
| R4 (4 losses) | $1,030.86; closed DD $3,897.60 | $4,845, profit factor 1.09 |
| R2 (2 losses) | $4,915.81; closed DD $2,761.27; 1.47 trades a session | $5,804, profit factor 1.16 |

**The decisive difference is the scaling.**
- The 17.5-point stop and lock are fixed in points, while the noise lines scale with price.
- On rescaled data every 2023 move is 1.3 to 2.8 times larger, so the same stop is relatively much tighter and each
  point is worth more. It is a different experiment from the unscaled proxy, not a variant of the same one.
- Execution (Pine fill-bar semantics or NinjaTrader's bracket), the end date and the unstated costs add to it.

**Both are NQ proxies, so neither decides anything for MNQ.**
- On MNQ, R2 against R4 was $562 against $2,961 at 1 tick, with 0 passes against 1 in 44 starts.
- An unscaled NQ rerun to match the quoted test was not made: MNQ is the instrument, and this would be one more proxy
  run.

## 5. Candidates

| Candidate | What | Verdict | Why |
|---|---|---|---|
| R2 (Pine, 2 losses) | Pine v1.5 with 2 losing trades a day instead of 4 | **Rejected** as a general improvement | MNQ net −81%, net ÷ intraday DD 0.29 against 1.76; the trades it removes were net winners (docs/PINE_REFERENCE.md) |
| C (MnqMomentumC) | Decoupled signals, room-based sizing, $300 reserve | **Not promoted** | Its 0 MNQ breaches come with 6 starts that became unable to fund a trade; passes 18 against B's 24 |
| B3 (noise lock) | At 1.0 noise unit of profit, stop to entry + 0.5 unit | **Rejected** | MNQ: +$1,077 net and net ÷ intraday DD 6.19 against 5.06, no winner sacrificed, but **every evaluation outcome identical** (24 / 6 / 14). NQ: net ÷ DD lower (7.35 against 8.27); 86 winners sacrificed (−$66,110) against 137 trades improved (+$52,894) |

## 6. Verdict

- **Frozen B is the recommended configuration, unchanged.**
  - Its software is verified against native NinjaTrader on the period behind its results.
  - It is profitable after costs on MNQ (development data) and on the NQ proxy.
  - **Adopt it for simulation-account forward testing only.** Use v1.1 (docs/FIXES_2026-10-20.md): the same trading
    logic, with realtime errors no longer ignored.
    - On a simulation account: `release/MnqMomentumB_v1.1/PRESET_B-PRACTICE-v1.1.md`.
    - Validation in the Strategy Analyzer: `PRESET_B-NATIVE-v1.1.md`, at 2 ticks base and 3 stress.
  - **At 3 ticks of slippage** it still made $11,606.80 on MNQ, with the evaluation outcomes unchanged.
  - **It is not adopted as an evaluation strategy.** Suitability is not established: about 3 independent MNQ windows,
    against a breach rate twice the pass rate on ten years of NQ.
- **The Pine v1.5 four-loss reference (R4) stays the Pine reference, unchanged.**
- **R2 and B3 are rejected. C is not promoted.**
- **No further parameter change is proposed.** The MNQ data holds one breach episode, and each countermeasure to its
  components has now failed a pre-registered test.
- **What would move the evaluation question:**
  - the forward test (docs/NATIVE_RUNS.md section 8);
  - MNQ history before 6/28, if NinjaTrader has it (03-26, 06-26).

## 7. Complete source and dependencies

**NinjaTrader 8 (frozen B):**

| File | sha256 |
|---|---|
| `Strategies/MnqNoiseMomentum.cs`, v1.1 (current) | `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35` |
| `Strategies/MnqNoiseMomentum.cs`, v1 (reconciled with native) | `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3` |
| `AddOns/MnqNoiseEngine.cs` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` |

- Packaged in `release/MnqMomentumB_v1.1.zip`, with INSTALL, both presets and SHA256SUMS. Nothing else is needed in
  NinjaTrader. v1 is in git history (docs/VERSIONS.md).

**Other code:**
- **Pine reference:** `pine/reference/mnq_noise_momentum_v1.5_user.pine`, sha256
  `cd44ee68d575e74019cd308f1079838a2b5cb7453d8b7c40473436c59b851975` (`release/PineReference_v1.5.zip`).
- **Candidate C:** `release/MnqMomentumC_candidate.zip`; `MnqMomentumC.cs` sha256
  `1a5142c233ae50b56357557f3c584c0f2eb9a71ddc62f0f7a3390bfdcb914fe0`.
- **B3 (rejected):** `verification/candidate_b3.patch` against B's two files.

**Research:**
- Python 3.13, pandas 3.0, numpy 2.5, pyarrow 26 (NQ parquet), pynescript (the Pine interpreter); `pyproject.toml`.
- The simulator: .NET 8 SDK, `ninjatrader/tests/Sim` (the strategy files compiled against NinjaTrader stand-ins,
  C# 5).

**Scripts of this round:**
- `research/b_native_reconcile.py` (native B against the simulator);
- `research/pine_nt_structure.py` (Pine/NinjaTrader categories);
- `research/b_breaches.py` (breach sequences);
- `research/b3_compare.py` (B3 against B);
- `research/candidate_c.py` (C rerun);
- `research/eval_sim.py` (evaluation replay).

**Data:**
- MNQ exports: the user's own, not in the repository; `verification/data_sha256.txt`.
- NQ: Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet`.

## Addendum (October 21, 2026): candidates D, D + E1 and D + E2

Built and tested as pre-registered (docs/CANDIDATE_D.md).

**The build:**
- A shared position manager: two MNQ within $125 all-in or no trade, a fee-aware breakeven, exactly half at +2R, a
  trailing runner, 15:55 flat, three campaigns a day.
- Sleeves: noise momentum, the Williams breakout and a causal sweep/reversal sequence.
- The NinjaScript and Python agree position by position on the NinjaTrader stand-in.

**Result: all three rejected on NQ** (2 ticks):
- 0 of 123 non-overlapping evaluations passed; all expired;
- profit factor 1.07-1.09;
- 0.10 trades a session.
- The $125 two-contract rule with structural stops turns down 97% of the signals.

**Frozen B v1.1 stays the reference.** Nothing was retuned.

## Addendum (October 21, 2026): candidate F

Pre-registered (docs/CANDIDATE_F.md, 7176271) before any F code. Built and frozen with hashes (a975289) before any F
result.

**The single change from E:** the sweep setup's initial stop at the selected FVG's far boundary ∓ 2 ticks, instead of
the sweep extreme.

**Result: rejected on NQ** (2 ticks; D + F1 and D + F2):
- G1 0 of 123 windows passed; G2 123 of 123 expired; G4 48.8% / 46.7%; G5 1.05 / 0.98. All four fail.
- G3 passes ($603 / $653).

**Affordability went up, the trading did not improve:**
- Executable setups rose from 2 to 274 (E1 pools) and from 5 to 1,072 (with the session pools).
- But most limits were cancelled when price ran +2R (in F's small R) before the retrace.
- F added only 35 / 62 positions, and they lose before and after costs: PF 0.73 / 0.47, 60-68% stopped at the
  initial stop.
- The combined net fell from $1,086 (D) to $631 / −$358.

**The roll-adjusted NQ series (docs/NQ_ROLLS.md) changes no F or D verdict.**

**Frozen B v1.1 stays the reference.** Nothing was retuned, and no further variation was launched.

## Addendum (October 21, 2026, overnight): net and gross profit against the maximum drawdown

**The user's new objective:** net and gross far above the maximum drawdown, and only that. The whole study is in
docs/NET_VS_DRAWDOWN.md.

**Frozen B already meets it over the long run:** 2011-2026, net is 7.5 times its maximum drawdown.

**Kept, as a candidate for a simulation account: BWF** (`release/MnqPortfolioBWF_candidate/`):
- frozen B, unchanged;
- its own breakout in the gaps at $200 (a setting);
- a new pre-FOMC drift strategy at 2 MNQ (`MnqFomcDrift.cs`, held to `mnqbot/fomc.py` trade for trade).

| | Frozen B | BWF |
|---|---:|---:|
| Net ÷ max drawdown, 2011-2026 | 7.5 | 12.5 |
| Net ÷ max drawdown, NQ walk-forward 2017-2025 | 4.7 | 12.1 |
| Chance that net exceeds the max drawdown within 1 / 3 / 5 years | 52 / 73 / 86% | 65 / 89 / 96% |

**Not established:**
- **The newest 15 months** (NSX, July 2025 to September 2026): BWF had 0.16 against B's 0.21, and is in an open
  drawdown since February 2025.
- **MNQ:** 62 sessions, worse there.
- **Native NinjaTrader:** not run.

**Rejected:**
- volatility-scaled contracts;
- an overnight long;
- the turn of the month;
- daily loss limits;
- a long-only breakout;
- the pre-holiday drift.

**Frozen B v1.1 stays the reference.** BWF runs beside it on simulation.
