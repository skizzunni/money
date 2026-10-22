# Candidate G: the daily candidate with its stop fitted to the $125 budget (pre-registration, October 22, 2026)

Written, with the code, **before any G result was viewed**. Results are added below the line in section 7, never
above it.

## 1. Why

The daily opportunity audit (docs/DAILY_AUDIT.md) found what keeps the daily candidate (D + F1 / D + F2) from 2-3
campaigns a session:
- **There are enough setups.** 84-88% of eligible sessions had a qualified setup (NQ 2015-2025).
- **Positions, pending orders and the three-campaign budget** refused under 1% of them.
- **Affordability refused 88-94%.** Two contracts at $125 all-in need R ≤ 29.25 points (market) or 29.75 (limit). The
  structural stops (noise line, Williams fraction, FVG edge) are several times that.

The fix addresses that cause and nothing else.

## 2. The change

**One rule changes:** what happens to a qualified setup whose structural stop is wider than the budget allows.
- **D, E, F ("skip"):** refused as unaffordable.
- **G "cap":** the stop moves toward the entry to the widest affordable distance (R = 29.25 points market, 29.75 limit),
  rounded toward the entry so the planned risk never exceeds $125. A stop already inside that distance is unchanged.
- **G "budget":** every stop is at that distance.

**Everything else is the shared specification, unchanged:**
- $125 planned risk including declared costs; two contracts, else no trade;
- a fee-aware breakeven at +1R; half off at +2R; an uncapped runner trailing 1R;
- no daily P&L cap or loser cutoff;
- at most three campaigns a session across all sleeves;
- flat at 15:55 ET or the earlier close.

**The sleeves, signals and filters are D / F's:** noise momentum, the Williams breakout, the sweep chain with F's
FVG-edge reference (before the fit), and the same skip, FOMC and NFP dates.

**Code:**
- `mnqbot/candidate_d.py`: `DConfig.stop_fit`, `max_r`, `fit_stop`.
- `MnqCandidateD.cs`: the setting **Stop wider than the budget** (`StopFit`: Skip / Cap / Budget). The default is Skip,
  so D, E and F are unchanged.
- NinjaScript and Python agree trade for trade on the user's MNQ bars for G cap and G budget (D + F2 sleeves), at
  $125 and the second parity budget (`tests/test_candidate_d.py`, configurations "G cap (D+F2)" and
  "G budget (D+F2)").

## 3. The protocol: develop, freeze, confirm once

The data split:

| Part | Data | Use |
|---|---|---|
| **Development** | NQ (`nq1m_scaled.pkl`) sessions 2015-03-02 to 2019-12-31 | the six variants below; the selection |
| **Holdout** | NQ sessions 2020-01-02 to 2025-06-30; the user's MNQ, 7/20 to 10/16/2026 | one run of the frozen variant |

**The development family** (six variants, `research/eval_g.py` `G_FAMILY`):

| | cap | budget |
|---|---|---|
| D sleeves (noise, Williams) | G-D cap | G-D budget |
| D + F1 sleeves (+ sweeps, E1 pools) | G-F1 cap | G-F1 budget |
| D + F2 sleeves (+ sweeps, E1 and session pools) | G-F2 cap | G-F2 budget |

**The selection rule (fixed now):**
1. A variant qualifies if, on development, it has P1 (at least 2.0 campaigns per eligible session at 2 ticks) and C1
   (net above $0 at 3 ticks).
2. Of those, the highest net ÷ intraday drawdown at 2 ticks is chosen.
3. If none qualifies, nothing is frozen and the holdout is not run.

**Amendments:** a further family may be pre-registered here as an amendment, with its own selection rule, before it
is run. It is developed on the development data only. Every family and its development results stay in this
document.

**The freeze:**
- `verification/candidate_g/frozen.txt` names the chosen variant.
- The hashes of the code are recorded in section 6 before the holdout run.
- `research/eval_g.py` refuses a holdout run without it.

**The holdout:** each holdout run is made once, with the frozen variant and frozen B on the same sessions.

**The honest limits of this split:**
- Both periods were seen in earlier candidates' results (B, D, E, F).
- The idea of fitting the stop comes from the participation audit, not from any profit result.
- The holdout is clean only for G.

## 4. The acceptance gates (holdout NQ, 2 ticks, unless stated)

**Unchanged from D / E / F:**

| Gate | Threshold |
|---|---|
| G1 evaluation pass rate (non-overlapping windows) | ≥ 60% |
| G2 expiry | ≤ 15% |
| G3 worst window drawdown | ≤ $1,500 |
| G4 win rate | ≥ 50% |
| G5 profit factor | ≥ 1.35 |

**Added for the user's daily requirement and the comparison with frozen B:**

| Gate | Threshold |
|---|---|
| P1 campaigns per eligible session, zero-campaign sessions included | ≥ 2.0 |
| P2 sessions with 2 or 3 campaigns | ≥ 50% |
| C1 net at 3 ticks | > $0 |
| C2 net ÷ intraday drawdown | ≥ frozen B's on the same sessions |

**How results are reported:**
- G is accepted only if every gate passes. Every result is reported, pass or fail.
- MNQ is reported beside NQ as the execution check. It does not decide.
- Native NinjaTrader results, when the user runs them, are reported separately from the simulator.

## 5. What is reported

**Measures:**
- net, intraday drawdown, their ratio, average net trade, profit factor, win rate;
- monthly net;
- participation (0 / 1 / 2 / 3 campaign shares over every eligible session);
- evaluation outcomes.

All at $0.95 a side, 2 ticks base and 3 ticks stress.

**Files:**
- the daily opportunity audit for the frozen variant;
- the trade ledger;
- the exact preset.

## 6. Frozen at pre-registration (sha256)

| File | sha256 |
|---|---|
| `mnqbot/candidate_d.py` | `630fbab22907db29d6b5f0f7f79d14a5c70ed301ed8ed8c03550c08c16fcfc32` |
| `ninjatrader/Strategies/MnqCandidateD.cs` | `babd74e7e644f3f0cdd76357adb695f114e8088e7c6a9606b85b96d5a28aa527` |
| `research/eval_d.py` | `e7dbe6620b949b7bd2adf50376f13294d16dbbded41fdb5dd8a39848e9d8060b` |
| NQ data `nq1m_scaled.pkl` | `89c0b157f826853f9ffa7e3e22e4e08f3e4b31d5e1492824ffc06a35fc083328` |

`research/eval_g.py` is the commit's own.

## 7. Results

### 7.1 Development, family 1 (NQ, 1,208 eligible sessions 2015-03-02 to 2019-12-31; 58 non-overlapping windows)

**Source:** `verification/candidate_g/dev1/`.

| 2 ticks | B | G-D cap | G-D budget | G-F1 cap | G-F1 budget | G-F2 cap | G-F2 budget |
|---|---:|---:|---:|---:|---:|---:|---:|
| Positions | 2,245 | 2,093 | 2,092 | 2,110 | 2,121 | 2,119 | 2,132 |
| Net $ | 48,990 | 6,047 | 4,903 | 6,527 | 4,436 | 5,322 | 3,468 |
| Intraday DD $ | 9,037 | 6,724 | 6,722 | 6,832 | 6,965 | 6,919 | 7,262 |
| Net ÷ DD | 5.42 | 0.90 | 0.73 | 0.96 | 0.64 | 0.77 | 0.48 |
| Average net trade $ | 21.82 | 2.89 | 2.34 | 3.09 | 2.09 | 2.51 | 1.63 |
| Profit factor | 1.22 | 1.05 | 1.04 | 1.05 | 1.04 | 1.04 | 1.03 |
| Net at 3 ticks $ | 37,508 | 2,860 | 2,203 | 3,334 | 1,096 | 2,119 | 117 |
| **Campaigns per eligible session (P1)** | 1.86 | **1.73** | 1.73 | **1.75** | 1.76 | 1.75 | 1.76 |
| Sessions with 0 / 1 / 2 / 3 campaigns % | 42 / 14 / 10 / 12 (+22 above 3) | 19 / 29 / 11 / 41 | 19 / 29 / 11 / 41 | 19 / 29 / 11 / 41 | 19 / 28 / 12 / 41 | 19 / 28 / 12 / 41 | 18 / 28 / 13 / 41 |
| Evaluations: pass / breach / expired (of 58) | 17 / 34 / 7 | 0 / 4 / 54 | 0 / 4 / 54 | 0 / 5 / 53 | 1 / 5 / 52 | 0 / 5 / 53 | 1 / 5 / 52 |

**What the fit did:**
- Participation went from 0.12 to 1.73-1.76 campaigns per session. 81% of sessions are active, and 52-54% have 2 or 3
  campaigns.
- Every variant is profitable at 2 and 3 ticks.

**The selection rule:**
- P1 (at least 2.0 a session) fails for all six; C1 passes for all six.
- **None qualifies, so nothing is frozen and the holdout is untouched.**

**The diagnosis (development data only):**
- Frozen B risks $200 on 4 contracts, about 25 points a contract. That is the same distance as G's 29.25, so a tight
  stop is not what separates them.
- Per contract and trade, B nets about $5.45 and G-D cap $1.45.
- B lets a trade ride its noise line, tightened at every check, to a 1.5-noise-unit target. G's runner trails 1R
  (29 points) behind the best price and is shaken out by ordinary noise.

### Amendment 1 (pre-registered before it was run): the runner trails the noise line

**The change, for noise-momentum campaigns only:**
- The stop also tightens to frozen B's line stop: the current check's line ∓ 0.24 noise units, B's `LineStop`,
  updated at each check and never loosened.
- After the half is off, the runner trails by that line instead of 1R ("line"), or by the tighter of the line and
  2R behind the best price ("line+2R").
- Williams and sweep campaigns keep the 1R trail. The noise line is not a level for them.

**Unchanged:**
- the fitted initial stop (cap);
- the fee-aware breakeven at +1R; half off at +2R; an uncapped runner;
- the $125 budget, two contracts, three campaigns, 15:55.

**The family** (`research/eval_g.py` `G_AMEND1`): G-D cap line, G-D cap line+2R, G-F1 cap line, G-F1 cap line+2R.

**The rule and the data:** the same selection rule (P1 and C1, then the highest net ÷ DD at 2 ticks), on the same
development data. The holdout stays untouched.

### 7.2 Development, amendment 1 (the same 1,208 sessions)

**Source:** `verification/candidate_g/dev_a1/`.

| 2 ticks | B | G-D cap line | G-D cap line+2R | G-F1 cap line | G-F1 cap line+2R |
|---|---:|---:|---:|---:|---:|
| Positions | 2,245 | 1,982 | 2,069 | 2,000 | 2,088 |
| Net $ | 48,990 | 14,974 | 11,532 | 15,527 | 12,021 |
| Intraday DD $ | 9,037 | 5,792 | 6,373 | 5,906 | 6,488 |
| Net ÷ DD | 5.42 | 2.59 | 1.81 | 2.63 | 1.85 |
| Average net trade $ | 21.82 | 7.56 | 5.57 | 7.76 | 5.76 |
| Profit factor | 1.22 | 1.13 | 1.10 | 1.13 | 1.10 |
| Net at 3 ticks $ | 37,508 | 11,985 | 8,308 | 12,531 | 8,787 |
| **Campaigns per eligible session (P1)** | 1.86 | **1.64** | 1.71 | **1.66** | 1.73 |
| Sessions with 0 / 1 / 2 / 3 campaigns % | 42 / 14 / 10 / 12 (+22) | 19 / 31 / 16 / 34 | 19 / 29 / 12 / 39 | 19 / 31 / 17 / 34 | 19 / 29 / 13 / 39 |
| Evaluations: pass / breach / expired (of 58) | 17 / 34 / 7 | 1 / 4 / 53 | 0 / 4 / 54 | 1 / 4 / 53 | 0 / 5 / 53 |

**What the line trail did:**
- Net is 2.4 times family 1's, the drawdown is lower, and net ÷ DD is 2.6 (0.96 before).
- The noise sleeve went from +$0.70 to +$7.85 a trade.

**The selection rule:** P1 still fails (1.64-1.73), so nothing is frozen.

**Participation (development):**
- 19% of sessions have no qualified setup in any sleeve.
- One-campaign sessions are mostly a single Williams breakout.

**The evaluation outcomes:**
- At $125 a campaign, the best variant nets about $3,100 a year. A $3,000 target in 30 days would need about 0.7R net
  per campaign.
- G1 (60% passes) and G2 (expiry ≤ 15%) cannot be met under the $125 rule by any variant of this kind.
- They stay in the gate table and are reported as they come out.

### Amendment 2 (pre-registered before it was run): a 15-minute check grid for the noise sleeve

**The change:**
- The noise sleeve checks every 15 minutes from 10:00 to 15:30 (23 checks), not every 30 (12).
- Each check's noise is the average over the last 14 sessions of |close ÷ open - 1| at that minute: the same
  definition at the finer grid.
- The line trail of amendment 1 follows the 15-minute lines.
- Frozen B's engine (`MnqNoiseEngine.cs`) is not touched. The grid is the candidate's own.

**The aim:** more qualified chances to re-enter after a stop or a scratch on active days, without forcing a trade.

**The family** (`G_AMEND2`): G-D cap line q15, G-F1 cap line q15. The selection rule, data and holdout are as
before.

### 7.3 Development, amendment 2 (the same sessions)

**Source:** `verification/candidate_g/dev_a2/`.

| 2 ticks | G-D cap line q15 | G-F1 cap line q15 | (G-D cap line, 30 minutes) |
|---|---:|---:|---:|
| Positions | 2,082 | 2,098 | 1,982 |
| Net $ | 10,831 | 10,785 | 14,974 |
| Intraday DD $ | 8,254 | 8,269 | 5,792 |
| Net ÷ DD | 1.31 | 1.30 | 2.59 |
| Net at 3 ticks $ | 7,844 | 7,793 | 11,985 |
| Campaigns per eligible session | 1.72 | 1.74 | 1.64 |
| Sessions with 0 / 1 / 2 / 3 campaigns % | 19 / 28 / 15 / 38 | 18 / 28 / 16 / 38 | 19 / 31 / 16 / 34 |

**Verdict:**
- The 15-minute grid adds 0.08 campaigns a session. It costs 28% of the net and adds 43% to the drawdown.
- P1 fails. **Rejected.**
- The 19% of sessions with no qualified setup is unchanged. No exit or check timing in these sleeves reaches it.

### Amendment 3 (pre-registered before the holdout): freeze the best development variant and confirm it once

**Why freeze despite P1:**
- No variant of these sleeves reaches P1 (2.0 campaigns a session) on development. The ceiling is set by the 19% of
  sessions with no setup.
- More development rounds on the same data would only fit it more closely.
- The holdout is used once, for an honest out-of-sample reading.
- **P1 stays a gate and is reported as it comes out**, as are G1-G5, P2, C1 and C2. Freezing is not acceptance.

**The frozen variant: G-D cap line.**
- Its sleeves are noise momentum and the Williams breakout.
- It has the fitted stop (cap), and noise campaigns follow the noise line.
- Everything else is the shared specification.
- G-F1 cap line had a marginally higher net ÷ DD on development (2.63 against 2.59). Its sweep sleeve made 27
  campaigns in five years (+$96), within noise.
- G-D cap line is chosen for parsimony and because it is the variant ported to TradingView
  (`pine/mnq_daily_g.pine`). The NinjaScript runs both.

**What it is in each implementation:**
- **NinjaScript:** `MnqCandidateD`, with these settings: noise On, Williams On, E1 Off, E2 Off, StopFit Cap, and
  RunnerTrail Line.
- **Python:** `DConfig(stop_fit="cap", runner_trail="line")`.
- **Pine:** `pine/mnq_daily_g.pine` at its defaults.

**Parity:**

| Comparison | Data | Result |
|---|---|---|
| NinjaScript against Python | the user's MNQ bars, $125 and the second budget | identical, trade for trade (`tests/test_candidate_d.py`, configuration "G-D cap line") |
| Pine against Python | raw NQ 2015-2019, development only (`research/pine_g_parity.py`) | 1,653 of 1,655 campaigns identical to the cent |

The two Pine differences are both a half target touched on the fill bar. The model fills it there; the test
emulator checks only the stop on a fill bar. The Pine script is the same either way.

**Frozen (sha256):**

| File | sha256 |
|---|---|
| `mnqbot/candidate_d.py` | `4998010483b5231f416d17416add1aad0e990dd6094840ef26158a33a7c8ed5d` |
| `ninjatrader/Strategies/MnqCandidateD.cs` | `b61bb6738828800e371f6ad5198eee47f035f7bfed0d7c2c7cb32a650e50a93c` |
| `research/eval_d.py` | `e7dbe6620b949b7bd2adf50376f13294d16dbbded41fdb5dd8a39848e9d8060b` |
| `research/eval_g.py` | `ee71e0204c57d04e4c4d672200f2c559f2a661feada519a824b9c36753ba3f94` (one fix after freezing, before any holdout computation: the frozen name was read as its first word, "G-D", and the run stopped at once; the earlier hash was `3edac3fb…`) |
| `pine/mnq_daily_g.pine` | `c5456086…` at the freeze; `107e4154eeb45085a69a49a2b0600b70d870eaaa4f8ae7e46b82f58e3efe1cc4` after the holdout, its header comment only (the results), no code change |

**The holdout:** `research/eval_g.py holdout-nq`, then `holdout-mnq`, once each. Results go in section 7.4.

### 7.4 Holdout: the frozen G-D cap line, run once (simulator; native NinjaTrader not yet run)

**Source:** `verification/candidate_g/holdout_nq/` and `verification/candidate_g/holdout_mnq/`. Both runs used
identical sessions, costs and evaluation starts for G and frozen B.

**NQ, 2020-01-02 to 2025-06-30** (1,363 eligible sessions, 65 fully observed non-overlapping windows; the deciding
data):

| | B 2t | **G 2t** | B 3t | **G 3t** |
|---|---:|---:|---:|---:|
| Positions | 2,693 | 2,338 | 2,685 | 2,340 |
| **Net $** | 42,585 | **16,726** | 35,802 | **12,421** |
| **Intraday DD $** | 13,731 | **4,936** | 14,121 | **5,829** |
| **Net ÷ DD** | 3.10 | **3.39** | 2.54 | **2.13** |
| Average net trade $ | 15.81 | 7.15 | 13.33 | 5.31 |
| Profit factor | 1.15 | 1.12 | 1.13 | 1.09 |
| Win rate % | 49.5 | 51.0 | 49.1 | 27.2 |
| **Campaigns per eligible session** | 1.98 | **1.72** | 1.97 | 1.72 |
| Sessions with 0 / 1 / 2 / 3 campaigns % | 41 / 14 / 9 / 11 (+25 above 3) | **18 / 29 / 15 / 37** | | 18 / 29 / 15 / 37 |
| Evaluations, non-overlapping: pass / breach / expired | 17 / 47 / 1 | 1 / 5 / 59 | 17 / 47 / 1 | 1 / 6 / 58 |
| Evaluations, overlapping (path-dependent) | 380 / 887 / 70 (7) | 30 / 128 / 1,179 (7) | 371 / 895 / 76 (2) | 25 / 143 / 1,173 (3) |
| By sleeve | | noise 1,504 / +16,748; Williams 834 / -22 | | noise +13,997; Williams -1,577 |
| Overruns (beyond planned risk) | n/a | 444, worst $36 | n/a | 756, worst $38 |

**Yearly net, 2 ticks:**

| Year | B | G |
|---|---:|---:|
| 2020 | 2,897 | -3,372 |
| 2021 | 18,018 | 3,836 |
| 2022 | 17,606 | 2,240 |
| 2023 | -719 | 214 |
| 2024 | 8,673 | 13,537 |
| 2025 (to June) | -3,890 | 271 |

Negative months: B 25 and G 28, of 66 (`ledger.csv.gz` has every position).

**MNQ, 7/20 to 10/16/2026** (62 eligible sessions; the execution check, not deciding):

| | B 2t | G 2t | B 3t | G 3t |
|---|---:|---:|---:|---:|
| Positions | 97 | 95 | 97 | 95 |
| Net $ | 13,031 | 1,652 | 11,607 | 1,084 |
| Intraday DD $ | 2,653 | 1,580 | 2,693 | 1,621 |
| Net ÷ DD | 4.91 | 1.05 | 4.31 | 0.67 |
| Average net trade $ | 134.34 | 17.38 | 119.66 | 11.41 |
| Campaigns per session | 1.56 | 1.53 | | |
| Sessions with 0 / 1 / 2 / 3 % | 56 / 5 / 5 / 10 (+24) | 19 / 40 / 8 / 32 | | |
| By sleeve | | noise 53 / +3,159; Williams 42 / -1,507 | | |

**Monthly net, MNQ, 2 ticks:**

| Month | B | G |
|---|---:|---:|
| 2026-07 (from 7/20) | -374 | -903 |
| 2026-08 | 3,280 | 512 |
| 2026-09 | 5,516 | 1,013 |
| 2026-10 (to 10/16) | 4,608 | 1,030 |

**The gates (NQ holdout, 2 ticks):**

| Gate | Result | Verdict |
|---|---|---|
| G1 evaluation pass rate ≥ 60% | 1.5% | FAIL |
| G2 expiry ≤ 15% | 90.8% | FAIL |
| G3 worst window drawdown ≤ $1,500 | $2,070 | FAIL |
| G4 win rate ≥ 50% | 51.0% (27.2% at 3 ticks) | PASS at 2 ticks, FAIL at 3 |
| G5 profit factor ≥ 1.35 | 1.12 | FAIL |
| P1 campaigns per eligible session ≥ 2.0 | 1.72 | FAIL |
| P2 sessions with 2 or 3 campaigns ≥ 50% | 53% | PASS |
| C1 net at 3 ticks > $0 | $12,421 | PASS |
| C2 net ÷ intraday DD ≥ frozen B's (3.10) | 3.39 | PASS |

**On MNQ** (not deciding): G3 passes ($1,395); G1, G2, G4, G5, P1, P2 and C2 fail; C1 passes.

**What the holdout shows:**

1. **The fit fixed participation out of sample.**
   - From 0.12 campaigns a session (F) to 1.72 on NQ and 1.53 on MNQ.
   - 82% of NQ sessions and 81% of MNQ sessions traded.
   - It never exceeds three, and every entry is a qualified setup.
2. **It is profitable out of sample at both costs.**
   - On the NQ holdout its net ÷ intraday drawdown (3.39) beats frozen B's (3.10).
   - It does that with about a third of B's drawdown ($4,936 against $13,731), at $125 a campaign.
3. **The noise sleeve carries it.**
   - Williams breakouts were flat on the NQ holdout (-$22 at 2 ticks) and lost on MNQ (-$1,507).
   - That is recorded and not tuned away: it is the holdout.
4. **Evaluation passes are out of reach at $125 a campaign.**
   - G nets about $3,000 a year on NQ.
   - A $3,000 target in 30 days would need about 0.7R net a campaign. Hence G1 and G2.
5. **2.0 campaigns a session is not reached.**
   - 18% of sessions have no qualified setup in either sleeve.
6. **G is not accepted under the pre-registered gates.** Every failure is listed above.

### 7.5 The daily opportunity audit of the frozen G-D cap line (2 ticks)

**Source:** `research/daily_audit.py`; `verification/daily_audit/g_{nq,mnq}/`.

| | NQ 2015-2025 (2,571 sessions) | MNQ 7/20-10/16/2026 (62) |
|---|---:|---:|
| Raw setups: noise / Williams | 8,917 / 1,833 | 211 / 46 |
| Qualified setups | 10,712 | 249 |
| Refused: unaffordable | **0** (F: 88-94%) | **0** |
| Refused: blocked by a position | 3,109 | 99 |
| Refused: blocked by a pending order | 0 | 0 |
| Refused: daily entry budget exhausted (3 campaigns) | 3,263 | 54 |
| Refused: same-bar priority | 20 | 1 |
| Not qualified: FOMC-morning short | 38 | 8 |
| **Campaigns** | **4,320** | **95** |
| **Campaigns per eligible session** | **1.68** | **1.53** |
| **Sessions with 0 / 1 / 2 / 3 campaigns %** | **18.8 / 30.0 / 15.6 / 35.6** | **19.4 / 40.3 / 8.1 / 32.3** |
| Sessions with no valid setup % | 18.8 | 19.4 |
| Missing-data / holiday or half-day / warm-up sessions | 6 / 85 / 32 | 2 / 1 / 15 |

**What it shows:**
- Every session with a qualified setup now trades. The zero-campaign share equals the no-setup share exactly.
- The remaining refusals are the open position and the three-campaign budget. Both are rules of the specification.
- The participation shortfall against 2.0 is the 19% of sessions on which neither sleeve has a setup.
