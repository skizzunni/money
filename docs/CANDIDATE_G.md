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

(None yet.)
