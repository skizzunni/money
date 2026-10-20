# Preset B-NATIVE-v1.1: frozen B in the Strategy Analyzer (the configuration reconciled with the simulator)

The reconciliation behind it: `docs/B_NATIVE.md` (97 of 97 trades from 7/20 to 10/16; totals equal at 1 tick).

**Code.** B v1.1 (`release/MnqMomentumB_v1.1/SHA256SUMS.txt`). Its trading logic is v1's; only the realtime error
handling differs (INSTALL.md), so every backtest trade is v1's:
- `Strategies/MnqNoiseMomentum.cs`, sha256 `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35`
- `AddOns/MnqNoiseEngine.cs`, sha256 `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7`

**Strategy Analyzer:**

| Setting | Value |
|---|---|
| Instrument | **MNQ DEC26 (12-26), unmerged**: Tools → Options → Market data → Merge policy "Do not merge" |
| Data series | **1 Minute**, trading hours **CME US Index Futures ETH** |
| Start / End | **1/1/2026 / 10/17/2026** (data loads from 5/3; warm-up 5/4 to 5/21; trading from 6/29) |
| Compare from | **7/20/2026**, the simulator's first tested session |
| Commission | **On**, a template of **$0.95 per side per contract** |
| Slippage | **2 ticks (base)**, then **3 ticks (stress)**. The reconciliation was made at 0, 1 and 2 |
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

Save the template as **B-NATIVE-v1.1**.

**Contract and roll:**
- **For validation:** DEC26 unmerged, as above. It is what was run and reconciled.
- **For an account:** the front month, moved after a session's close at the roll: 9/10 for SEP→DEC; for DEC→MAR,
  8 days before the 12/18 expiry. This is `PRESET_B-PRACTICE-v1.1.md`.
- docs/B_NATIVE.md section 2 shows the choice changed no trade on these data. It is not guaranteed to on others: the calendar spread
  moves the absolute levels, and a level can round differently.

**Acceptance rule for any further native run of this preset** (the user's three existing v1 runs, at 0, 1 and 2 ticks, pass):
- every native trade from 7/20 has a simulator trade with the same entry minute, direction, contracts, exit minute and
  exit kind;
- from 10/1, prices are identical;
- elsewhere, per-trade P/L is within $4.00.

**Expected on the simulator, MNQ 7/20 to 10/16** (`verification/b_slippage/`):
- 2 ticks: 97 trades, $13,030.80, intraday drawdown $2,652.80; 44 starts 24 pass / 6 breach / 14 expired.
- 3 ticks: 97 trades, $11,606.80, intraday drawdown $2,692.80; 24 / 6 / 14. One trade (9/23 10:00) changes from its
  target (+$1,022.40) to its stop (−$213.60): a tick worse fill puts the fill bar's high on its stop.
