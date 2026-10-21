# The daily MNQ strategy: opportunity audit and comparison with frozen B (October 21, 2026)

## Scope (the user's correction of October 21)

**The main deliverable is a daily MNQ strategy:**
- 2-3 qualified entry campaigns per eligible session, at most three, no forced trades.
- An occasional zero-trade day is acceptable. A strategy trading only around rare events is not the deliverable.

**The shared rules:**
- $125 planned risk including declared costs;
- two contracts when affordable, otherwise skip;
- a fee-aware breakeven at +1R;
- half off at +2R, and an uncapped trailing runner;
- no daily P&L cap or loser cutoff;
- at most three campaigns across all sleeves;
- flat at 15:55 ET or the earlier close.

**The candidate:**
- **Candidate F,** the last preregistered daily candidate authorized (docs/CANDIDATE_F.md, preregistered in
  7176271, frozen in a975289).
  - Its two books: **D + F1** (noise momentum, Williams breakout, sweep reversals on the previous-day / previous-week
    pools) and **D + F2** (the same, plus the session pools).
  - Both under the shared position manager (`MnqCandidateD.cs`, `mnqbot/candidate_d.py`).
- **Its verdict (rejected) stands.** Nothing is retuned here, no rejected version is reopened, and no other strategy
  is started.

**The pre-FOMC drift is a separate experiment** (docs/FOMC_EXPERIMENT.md). It is not part of this strategy or its
preset.

## What ran where

**Simulator** (the NinjaTrader stand-in, and the Python model held to it position by position):
- every candidate figure below;
- the refusal lines `MnqCandidateD.cs` now prints match the Python audit's counts by reason
  (`tests/test_daily_audit.py`).

**Native NinjaTrader:**
- **Frozen B:** reconciled with the simulator, 97 of 97 trades over 7/20-10/16/2026 (docs/B_NATIVE.md).
- **The daily candidate (D / E / F) has not run natively.**
- The only native run of anything new is the FOMC experiment's (docs/FOMC_EXPERIMENT.md). It agrees with the
  simulator to the cent and is not part of this strategy.

## 1. The daily opportunity audit

**The audit** (`research/daily_audit.py`; one row a session in `verification/daily_audit/<data>/daily_audit_<book>.csv`).
Each row holds:
- the data coverage: 09:30-16:00 minutes of 390, and electronic-session minutes;
- the status: eligible, warm-up, holiday or half day, missing data;
- the sleeves' warm-up;
- raw setups by sleeve:
  - noise: checks closing past a line;
  - Williams: level touches;
  - sweep: pool penetrations;
- qualified setups: those passing every sleeve rule;
- limit orders placed, and campaigns (entries that filled);
- every refusal by reason.

**The refusal reasons:**
- unaffordable: more than $125 planned for two contracts;
- blocked by a position;
- blocked by a pending order;
- the daily entry budget exhausted;
- same-bar priority;
- after the entry window;
- missing data;
- not qualified: an FOMC-morning noise short, a bar touching both Williams levels, a sweep decision outside the window,
  the room test, an incomplete sweep chain.

### MNQ (the user's data; 62 eligible sessions, 7/20 to 10/16/2026; 15 warm-up, 2 missing-data and 1 holiday or half-day session apart)

| 2 ticks | D + F1 | D + F2 |
|---|---:|---:|
| Raw setups: noise / Williams / sweep penetrations | 211 / 46 / 84 | 211 / 46 / 272 |
| Qualified setups | 255 | 280 |
| **Refused: unaffordable (over $125 for two contracts)** | **243** | **257** |
| Refused: blocked by a position | 1 | 1 |
| Refused: blocked by a pending order | 0 | 0 |
| Refused: daily entry budget exhausted | 0 | 0 |
| Refused: same-bar priority | 0 | 5 |
| Refused: after the entry window | 1 | 1 |
| Limit orders placed (sweep) | 4 | 10 |
| **Campaigns** | **6** | **7** |
| Not qualified: FOMC-morning short / room | 8 / 0 | 8 / 2 |
| Sweep chains incomplete | 78 | 239 |
| Sessions with no valid setup | 16.1% | 12.9% |
| **Campaigns per eligible session** | **0.10** | **0.11** |
| **Sessions with 0 / 1 / 2 / 3 campaigns** | **91.9 / 6.5 / 1.6 / 0.0 %** | **90.3 / 8.1 / 1.6 / 0.0 %** |
| Campaigns per active session (shown only beside the above) | 1.20 | 1.17 |

**Why the opportunities are missing:**
- **It is not a lack of setups.** 87% of eligible sessions had at least one qualified setup.
- **It is not a lack of time or of the three-campaign budget.**
  - Position blocks: 1. Pending orders: 0.
  - The budget was exhausted on no session.
- **It is affordability.**
  - 257 of 280 qualified setups (92%) were refused because two contracts' planned risk exceeded $125.
  - That needs a stop within 29.25 points (market) or 29.75 (limit). At 2026's MNQ volatility the structural stops are
    several times that: median R 86-138 points (docs/CANDIDATE_D.md; docs/CANDIDATE_F.md for the sweeps).

### NQ (2015-2025, the deciding data; 2,571 eligible sessions; 32 warm-up, 85 holiday or half-day and 6 missing-data sessions apart)

The missing-data sessions are 2020-03-09, 03-12, 03-16, 03-18, 2025-02-10 and 2025-06-20. Holidays and early closes
come from the NYSE calendar, so a short holiday session is not counted as missing data.

| 2 ticks | D + F1 | D + F2 |
|---|---:|---:|
| Raw setups: noise / Williams / sweep penetrations | 8,917 / 1,833 / 3,706 | 8,917 / 1,833 / 12,684 |
| Qualified setups | 11,136 | 12,490 |
| **Refused: unaffordable (over $125 for two contracts)** | **10,478 (94.1%)** | **11,033 (88.3%)** |
| Refused: blocked by a position | 101 | 104 |
| Refused: blocked by a pending order | 2 | 2 |
| Refused: daily entry budget exhausted (on 3 sessions) | 11 | 11 |
| Refused: same-bar priority | 21 | 475 |
| Refused: after the entry window | 4 | 6 |
| Market entries / sweep limit orders placed | 268 / 251 | 268 / 591 |
| **Campaigns** | **303** | **330** |
| Not qualified: FOMC-morning short / decision window / room | 38 / 1 / 4 | 38 / 8 / 255 |
| Sweep chains incomplete | 3,277 | 10,643 |
| Sessions with no valid setup | 16.3% | 12.1% |
| **Campaigns per eligible session** | **0.118** | **0.128** |
| **Sessions with 0 / 1 / 2 / 3 campaigns** | **90.0 / 8.7 / 0.9 / 0.4 %** | **89.0 / 9.6 / 0.9 / 0.5 %** |
| Campaigns per active session (shown only beside the above) | 1.17 | 1.17 |

**The same finding as on MNQ, over eleven years:**
- 84-88% of eligible sessions had at least one qualified setup.
- Positions, pending orders and the three-campaign budget together refused under 1% of them.
- The $125 two-contract rule refused 88-94%.

## 2. The comparison with frozen B

**The setup** (`research/comparison_report.py`; `verification/daily_audit/comparison_<data>.csv`,
`monthly_<data>.csv`):
- identical dates, costs ($0.95 a side; 2 ticks base, 3 stress) and account starts;
- the same evaluation starts (Apex 50K: $3,000 target, $2,000 trailing including open P/L, 30 days).

### MNQ (62 eligible sessions; 3 non-overlapping, 42 overlapping evaluation starts)

| | B, 2t | B, 3t | D + F1, 2t | D + F1, 3t | D + F2, 2t | D + F2, 3t |
|---|---:|---:|---:|---:|---:|---:|
| Positions | 97 | 97 | 6 | 6 | 7 | 7 |
| **Net** | $13,030.80 | $11,606.80 | $77.20 | $68.20 | $161.40 | $151.90 |
| **Intraday drawdown** | $2,652.80 | $2,692.80 | $440.20 | $447.20 | $440.20 | $447.20 |
| **Net ÷ drawdown** | 4.91 | 4.31 | 0.18 | 0.15 | 0.37 | 0.34 |
| Average net trade | $134.34 | $119.66 | $12.87 | $11.37 | $23.06 | $21.70 |
| Profit factor; win rate | 2.54; 58.8% | 2.33; 57.7% | 1.24; 50.0% | 1.21; 33.3% | 1.50; 57.1% | 1.46; 42.9% |
| Campaigns per eligible session | 1.56 | 1.56 | 0.10 | 0.10 | 0.11 | 0.11 |
| Sessions with 0 / 1 / 2 / 3 / more than 3 | 56.5 / 4.8 / 4.8 / 9.7 / 24.2 % | same | 91.9 / 6.5 / 1.6 / 0 / 0 % | same | 90.3 / 8.1 / 1.6 / 0 / 0 % | same |
| Evaluations, non-overlapping: pass / breach / expired | 1 / 1 / 1 | 1 / 1 / 1 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| Evaluations, overlapping | 23 / 6 / 13 | 23 / 6 / 13 | 0 / 0 / 42 | 0 / 0 / 42 | 0 / 0 / 42 | 0 / 0 / 42 |

**Monthly net, MNQ:**

| Month | B 2t | B 3t | D + F1 2t | D + F1 3t | D + F2 2t | D + F2 3t |
|---|---:|---:|---:|---:|---:|---:|
| 2026-07 | −374.00 | −420.00 | 0 | 0 | 0 | 0 |
| 2026-08 | 3,280.40 | 3,240.40 | 74.40 | 71.40 | 158.60 | 155.10 |
| 2026-09 | 5,516.40 | 4,216.40 | −205.40 | −210.40 | −205.40 | −210.40 |
| 2026-10 (to 10/16) | 4,608.00 | 4,570.00 | 208.20 | 207.20 | 208.20 | 207.20 |

### NQ (2,571 eligible sessions; 123 fully observed non-overlapping and 2,552 overlapping evaluation starts)

| | B, 2t | B, 3t | D + F1, 2t | D + F1, 3t | D + F2, 2t | D + F2, 3t |
|---|---:|---:|---:|---:|---:|---:|
| Positions | 4,938 | 4,924 | 303 | 303 | 330 | 330 |
| **Net** | $91,575.20 | $73,309.60 | $631.10 | $316.10 | −$358.00 | −$698.00 |
| **Intraday drawdown** | $14,934.80 | $15,815.20 | $1,907.80 | $2,034.30 | $1,997.30 | $2,056.30 |
| **Net ÷ drawdown** | 6.13 | 4.64 | 0.33 | 0.16 | −0.18 | −0.34 |
| Average net trade | $18.54 | $14.89 | $2.08 | $1.04 | −$1.08 | −$2.12 |
| Profit factor; win rate | 1.18; 50.0% | 1.14; 49.6% | 1.05; 48.8% | 1.02; 27.7% | 0.98; 46.7% | 0.95; 26.7% |
| Campaigns per eligible session | 1.92 | 1.92 | 0.118 | 0.118 | 0.128 | 0.128 |
| Sessions with 0 / 1 / 2 / 3 / more than 3 | 41.8 / 14.0 / 9.8 / 11.6 / 22.8 % | 41.8 / 14.0 / 9.8 / 11.7 / 22.7 % | 90.0 / 8.7 / 0.9 / 0.4 / 0 % | same | 89.0 / 9.6 / 0.9 / 0.5 / 0 % | same |
| Evaluations, non-overlapping: pass / breach / expired | 34 / 81 / 8 | 34 / 81 / 8 | 0 / 0 / 123 | 0 / 0 / 123 | 0 / 0 / 123 | 0 / 0 / 123 |
| Evaluations, overlapping (path-dependent) | 745 / 1,586 / 212 (9) | 716 / 1,619 / 214 (3) | 0 / 0 / 2,552 | same | 0 / 0 / 2,552 | same |

**Yearly net, NQ** (the months are in `monthly_nq.csv`):

| Year | B 2t | D + F1 2t | D + F2 2t |
|---|---:|---:|---:|
| 2015 | 10,297 | −540 | −557 |
| 2016 | 12,080 | −518 | −393 |
| 2017 | −1,989 | 1,854 | 1,698 |
| 2018 | 24,815 | −18 | −137 |
| 2019 | 3,787 | 684 | 379 |
| 2020 | 2,897 | −22 | 22 |
| 2021 | 18,018 | −500 | −247 |
| 2022 | 17,606 | −186 | −221 |
| 2023 | −719 | −16 | −661 |
| 2024 | 8,673 | −256 | −245 |
| 2025 (to June) | −3,890 | 149 | 3 |

**Negative months (of 124):** B 50; D + F1 40; D + F2 45.

## 3. The preregistered gates (NQ, 2 ticks, 123 non-overlapping windows; unchanged)

| Gate | D + F1 | D + F2 | Frozen B (reference) |
|---|---|---|---|
| G1 pass rate ≥ 60% | 0.0% **FAIL** | 0.0% **FAIL** | 27.6% FAIL |
| G2 expiry ≤ 15% | 100% **FAIL** | 100% **FAIL** | 6.5% pass |
| G3 worst window drawdown ≤ $1,500 | $602.55 pass | $652.60 pass | $2,171.00 FAIL |
| G4 win rate ≥ 50% | 48.8% **FAIL** | 46.7% **FAIL** | 50.0% pass |
| G5 profit factor ≥ 1.35 | 1.05 **FAIL** | 0.98 **FAIL** | 1.18 FAIL |

At 3 ticks the same gates fail, and G4 falls to 27.7% / 26.7%.

**On MNQ** (not deciding):
- D + F1 fails G1, G2 and G5, and passes G3 and G4.
- D + F2 fails G1 and G2, and passes G3, G4 and G5, on 7 positions.

## 4. Which requirements failed

| Requirement | Result | Verdict |
|---|---|---|
| **2-3 qualified entry campaigns per eligible session** | 0.10-0.13 a session; **89-92% of eligible sessions have none**; 2 or 3 campaigns on 1-2% | **FAILED** |
| At most three campaigns | Never exceeded (never reached) | met |
| No forced trades | Every entry is a qualified setup | met |
| $125 planned risk, two contracts or skip | Enforced. It refuses 92% of qualified setups on MNQ, the main cause of the participation shortfall | met as a rule; it is what blocks participation |
| Fee-aware breakeven, half at +2R, uncapped runner, 15:55 flat, no daily caps | Implemented, and tested on synthetic sequences against hand-computed values | met |
| **Net profit and intraday drawdown against frozen B** | MNQ: $161 against $13,031; NQ: −$358 / +$631 against $91,575. Net ÷ DD 0.37 / −0.18 against 4.91 / 6.13 | **FAILED**: lower net, and a lower profit-to-drawdown ratio |
| **Preregistered gates G1-G5** | G1, G2, G4, G5 fail; G3 passes | **FAILED** (rejected, as recorded) |
| **Native NinjaTrader validation** | Not run for the daily candidate | **not established** |

**In one sentence:** the daily candidate meets the shared risk rules, but under them it cannot reach the daily
participation target on MNQ. The $125 two-contract rule refuses almost every qualified setup, and the few it takes do
not beat frozen B's net or its profit-to-drawdown ratio.

## 5. Deliverables

**Source:**
- `ninjatrader/Strategies/MnqCandidateD.cs`, which now prints its refusals (setting "Print refusals", no trading
  change);
- `ninjatrader/AddOns/MnqNoiseEngine.cs`;
- `mnqbot/candidate_d.py`.

**Presets:** `release/MnqCandidateD_candidate/PRESET_F-CANDIDATE.md` (D + F1 / D + F2) and `PRESET_D-CANDIDATE.md`.
The package is `release/MnqCandidateD_candidate.zip` (`release/SHA256SUMS.txt`).

**Results:**
- **Trade ledgers:** `verification/candidate_f/{mnq,nq}/ledger.csv.gz`, every position with its contracts.
- **Daily opportunity audit:** `verification/daily_audit/{mnq,nq}/daily_audit_<book>.csv` and
  `daily_audit_summary.csv`.
- **Comparison and monthly tables:** `verification/daily_audit/comparison_{mnq,nq}.csv` and
  `monthly_{mnq,nq}.csv`.

**Tests:** `tests/test_candidate_d.py`, `tests/test_candidate_f.py` and `tests/test_daily_audit.py`: parity with the
NinjaScript, hand-computed sequences, and the audit's reconciliation.

**For a native run:**
- Strategy Analyzer, MNQ DEC26, 1-minute ETH, the preset at 2 ticks.
- Export the Trades and the NinjaScript Output. The "D refusal" lines are comparable with `daily_audit_<book>.csv`.
