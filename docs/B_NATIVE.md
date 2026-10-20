# Frozen B in native NinjaTrader against the simulator: reconciliation and the exact preset (October 20, 2026)

**Labels.**
- **Native:** the user's own NinjaTrader Strategy Analyzer runs B_L0 / B_L1 / B_L2 (docs/REFERENCE.md section 4e),
  rebuilt from their fills. Each run's summary matches to the cent.
- **Simulator:** the stand-in (`ninjatrader/tests/Sim`) running the same two files on the user's exported MNQ bars.
- **Instrument:** MNQ only, at $2 a point, $0.50 a tick and $0.95 a side (`tests/test_mnq_units.py`). No NQ in this
  document.

## 1. The two runs do not use the same bars, so every trade is assigned to a period

| | Native (B_L0/1/2) | Simulator (every MNQ evaluation result) |
|---|---|---|
| Contract | MNQ DEC26 throughout, unmerged; the deferred contract before the 9/10 roll | Traded contracts: MNQ 09-26 to the 9/10 session (back-adjusted +284.50), MNQ 12-26 from 9/11 |
| Data | From 5/3 18:01; a hole from 5/22 to 6/26 | From 6/28 18:00 (the user's exports) |
| Warm-up (14 full sessions) | 5/4 to 5/21; trading from 6/29 | 6/29 to 7/17; trading from 7/20 |
| Costs | $0.95 a side; slippage 0 / 1 / 2 | Same |

The four periods:
- **6/29 to 7/17:** the native run trades and the simulator is still warming up.
- **7/20 to 9/10:** different contracts (DEC26 against 09-26).
- **9/11 to 9/30:** the same 12-26 bars, but the simulator's 14-session noise average still holds 09-26 sessions.
- **10/1 to 10/16:** the same bars and the same noise history.

## 2. Result: every simulator trade from 7/20 is a native trade (`research/b_native_reconcile.py`)

Trades are matched by entry minute, direction and contracts. Per-trade rows are in
`verification/b_native/B_L*_native_vs_standin.csv`; the table below is `by_period.csv`.

| Slippage | Period | Native trades, net | Simulator trades, net | Same entry minute, exit minute and exit kind | Same points (exit minus entry) |
|---|---|---|---|---|---|
| 1 tick | 7/20-9/10, different contracts | 48, $3,229.20 | 48, $3,227.20 | 48 | 47 |
| 1 tick | 9/11-9/30, mixed noise history | 29, $5,343.60 | 29, $5,345.60 | 29 | 21 |
| 1 tick | 10/1-10/16, identical | 20, $4,646.00 | 20, $4,646.00 | 20 | 20 |
| **1 tick** | **7/20-10/16** | **97, $13,218.80** | **97, $13,218.80** | **97** | **88** |
| 0 ticks | 7/20-10/16 | 98, $13,461.20 | 98, $13,471.20 | 98 | 92 |
| 2 ticks | 7/20-10/16 | 97, $13,040.80 | 97, $13,030.80 | 97 | 86 |
| any | 6/29-7/17 (simulator warming up) | 21 (−$285.60 / −$329.60 / −$377.60) | 0 | | |

**Every remaining difference is one or two ticks on a stop or target level, at the same minute and of the same kind**
(at most $4.00 a trade).
- **9/11 to 9/30:** the noise average, and so the target and line-stop levels, differs by a tick or two.
- **August, at 1 and 2 ticks:** two stops. The price levels differ by the calendar spread, so a stop measured in ticks
  from a slipped entry rounds differently.
- **Totals over 7/20 to 10/16:**
  - 1 tick: the same to the cent;
  - 0 ticks: the simulator $10.00 higher;
  - 2 ticks: the simulator $10.00 lower.
- **Not one trade** has a different entry, a different exit minute, or a different exit kind.

**What this shows and what it does not:**
- **Shown:** the simulator reproduces native NinjaTrader's frozen-B trades for the whole MNQ period behind B's
  evaluation results (7/20 to 10/16). Using DEC26 or 09-26 before the roll changed no trade.
- **Not shown:** the intraday price path inside each trade on native DEC26 bars before 9/10. The evaluation replay's
  peaks use the 09-26 bars. Their point moves match DEC26 in 47 of 48 trades' results, but MAE/MFE was not compared
  bar by bar.
  - It can be: the optional request in section 4.
- **The native 6/29-7/17 trades (21) are not in any simulator evaluation start.** Those starts begin 7/20.

So the simulator's frozen-B MNQ results can be used to compare changes to B. A change must still get its own native
run before it is adopted, because this reconciliation covers B's code paths only.

## 3. The exact preset: B-NATIVE-v1 (the reconciled configuration)

**Since superseded for any account by B v1.1** (`release/MnqMomentumB_v1.1/PRESET_B-NATIVE-v1.1.md`). v1.1 has the
same trading logic, does not ignore realtime errors, and uses 2 ticks as the base slippage and 3 as the stress
(docs/FIXES_2026-10-20.md). The preset below is v1's, as reconciled.

**Code.** The two files, unchanged (`release/MnqMomentumB_v1/SHA256SUMS.txt`):
- `Strategies/MnqNoiseMomentum.cs`, sha256 `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3`
- `AddOns/MnqNoiseEngine.cs`, sha256 `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7`

**Strategy Analyzer:**

| Setting | Value |
|---|---|
| Instrument | **MNQ DEC26 (12-26), unmerged**: Tools → Options → Market data → Merge policy "Do not merge" |
| Data series | **1 Minute**, trading hours **CME US Index Futures ETH** |
| Start / End | **1/1/2026 / 10/17/2026** (data loads from 5/3; warm-up 5/4 to 5/21; trading from 6/29) |
| Compare from | **7/20/2026**, the simulator's first tested session |
| Commission | **On**, a template of **$0.95 per side per contract** |
| Slippage | **1 tick** (primary); 2 ticks (check); 0 (check) |
| Order fill resolution | Standard (Fastest); fill limit orders on touch **Off** |
| Entries per direction / handling | 1 / Unique entries |
| Exit on session close | On |
| Calculate | On bar close |

**Strategy parameters.** All defaults, except the following:

| Setting (group) | Value |
|---|---|
| FUNDED ACCOUNT (1) | Off |
| Contracts in an evaluation (1) | **4** |
| Evaluation: max loss per trade, $ (1) | **200** |
| Evaluation: no new entries after this many losers today (1) | **3** |
| Stop only ever tightens (1) | **On** |
| Daily gate losers / $ (1) | 0 / 0 (off) |
| Bot: close half at R (1) | 0 (off) |
| Take-profit / line stop, noise units (2) | 1.5 / 0.24 |
| Evaluation lock at / plus (2) | 1.0 / 2.5 |
| Noise lookback (3) | 14 |
| **Breakout in the bot's gaps (5)** | **Off: this is what makes it B** |
| Diagnostics (6) | On |

Save the template as **B-NATIVE-v1**.

**Contract and roll:**
- **For validation:** DEC26 unmerged, as above. It is what was run and reconciled.
- **For an account:** the front month, moved after a session's close at the roll: 9/10 for SEP→DEC; for DEC→MAR,
  8 days before the 12/18 expiry. This is `release/MnqMomentumB_v1/PRESET_B-PRACTICE-v1.md`.
- Section 2 shows the choice changed no trade on these data. It is not guaranteed to on others: the calendar spread
  moves the absolute levels, and a level can round differently.

**Acceptance rule for any further native run of this preset** (applied to the existing three, which pass):
- every native trade from 7/20 has a simulator trade with the same entry minute, direction, contracts, exit minute and
  exit kind;
- from 10/1, prices are identical;
- elsewhere, per-trade P/L is within $4.00.

## 4. Optional, once: native DEC26 bars before the roll

Tools → Historical Data → Export, MNQ 12-26, 1 Minute, Last, **6/28/2026 to 9/11/2026**.

With these bars, the evaluation replay can be run on the exact native bars too. It closes the one gap in section 2.
