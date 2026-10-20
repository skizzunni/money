# Preset B-PRACTICE-v1.1: momentum only (B), 4 MNQ, on a simulation account

**For practice only:** a NinjaTrader simulation account, never a funded or paid evaluation account.

## Account

1. Control Center → Accounts → right-click → create a **new simulation account** named **`SimB`**:
   - Initial balance **$50,000**.
   - The name must **not** start with APEX or PA, so the strategy uses the FUNDED setting below (off = the 50K
     evaluation rules).
2. Assign a commission template of **$0.95 per side per contract** to SimB. This is the rate the native tests used.
3. Before the first session, reset SimB to $50,000 if it has traded.

## Chart

- Instrument: **MNQ front month**: DEC26 now; MAR27 from the December roll (move after a session's close).
- Bars: **1 Minute**. Trading hours: **CME US Index Futures ETH**.
- **Days to load: 45**: the strategy needs 14 full sessions before its first trade.
- Add the strategy **from the chart**: MnqNoiseMomentum, account **SimB**, **Enabled**.

## Strategy settings

**Only two differ from the defaults: UseBreakout Off, Diagnostics On.**

**Group 1 (Account):**

| Setting | Value |
|---|---|
| Evaluation or funded from the account's name | On (SimB is not APEX-, so the next setting decides) |
| FUNDED ACCOUNT | **Off** |
| Contracts in an evaluation | **4** |
| Contracts on a funded account | 4 |
| Evaluation: max loss per trade, $ | **200** |
| Funded: max loss per trade, $ | 200 |
| Evaluation: no new entries after this many losers today | **3** |
| Funded: no new entries after this many losers today | 2 |
| Place orders | **On** |
| Evaluation: close everything at this profit, $ | **3000** (the strategy closes all and stops once SimB is $3,000 up) |
| Evaluation: profit already made before this start | 0 |
| Evaluation: read its profit from the account | On |
| Evaluation: the day it was bought | (empty) |
| Evaluation: bold finish from this day | **0 (off)** |
| Evaluation: bold finish size | 2.5 (unused) |
| Evaluation: account's starting balance, $ | **50000** |
| Funded: payout stop / payouts taken / $200 days / profit since payout / best day | On / 0 / 0 / 0 / 0 (unused: FUNDED off) |
| Funded: remember the payout cycle in a file | On (unused) |
| Stop only ever tightens | **On** |
| Daily gate: losing trades / loss limit | **0 / 0 (off)** |
| Bot: close half at this many R | **0 (off)** |

**Group 2 (Exits):**

| Setting | Value |
|---|---|
| Take-profit, noise units | 1.5 |
| Line stop, noise units past the line | 0.24 |
| Evaluation lock at / lock moves the stop to entry + | 1.0 / 2.5 points |
| Funded lock (unused) | 0.5 / 6.25 |

**Group 3 (Entries):**

| Setting | Value |
|---|---|
| Noise lookback | 14 |
| Fed days: no shorts before 14:00 | On |
| Skip dates, Fed dates | Defaults (they run to the end of 2027) |

**Group 4 (Alerts):** Sound alerts On.

**Group 5 (Breakout):**

| Setting | Value |
|---|---|
| **Breakout in the bot's gaps** | **Off. This is what makes it B.** |
| The other breakout settings | Defaults, unused |

**Group 6 (Diagnostics):** **On.** It adds order, fill and blocked-signal lines to the Output; no trading change.

**Fixed by the strategy itself** (shown for reference, nothing to set):

| Setting | Value |
|---|---|
| Calculate | On bar close |
| Entries per direction / handling | 1 / Unique entries |
| Exit on session close | On (60 s) |
| Start behavior | Wait until flat |
| Bars required to trade | 0 (its own 14-session warm-up) |

When everything matches, save it as a template named **B-PRACTICE-v1.1** (the template menu at the bottom of the
strategy dialog).

## Each session

- **Before 09:30 New York:** NinjaTrader connected, the chart open, the strategy enabled (green). The Output's first
  three lines are "MNQ settings:". Check that they show "PlaceOrders True", "4 MNQ", "UseBreakout False" and
  "Diagnostics True".
- **After 16:00:** NinjaScript Output → right-click → Save as `B-PRACTICE_<yyyy-mm-dd>_output.txt`. Control Center →
  Executions → export the day's fills. Then clear the Output.
- **Stop the test only for an operational fault:**
  - a position without a stop;
  - a fill the Output does not explain;
  - a runtime error or a disabled strategy;
  - a mismatch between the account's and the strategy's position.
- **Never stop it for performance, and never change a setting.**

**What the strategy does not do:** it does not enforce the evaluation's $2,000 trailing threshold (NinjaTrader's
simulation account does not either). Breaches are measured afterwards from the saved fills and the 1-minute bars, so
also export the MNQ 1-minute bars weekly (Tools → Historical Data → Export).
