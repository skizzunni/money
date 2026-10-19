# Preset RUNNER-CANDIDATE: the runner candidate on a simulation account

**For a native check or practice only:** a NinjaTrader simulation account, never a paid evaluation account. The
comparison in `docs/RUNNER.md` decides whether this candidate is adopted. Frozen B (`MnqMomentumB_v1`) is unchanged
and stays the comparison.

## Account

1. Control Center → Accounts → right-click → create a **new simulation account** named **`SimRunner`**, initial
   balance **$50,000**.
2. Assign a commission template of **$0.95 per side per contract** to SimRunner.
3. Reset SimRunner to $50,000 before the first session. Delete
   `Documents\NinjaTrader 8\MnqNoiseMomentum\runner-account-SimRunner.txt` if an earlier test left one: it holds the
   remembered highest equity and pass.

## Chart

- Instrument: **MNQ front month**: DEC26 now; MAR27 from the December roll (switch after a session's close).
- Bars: **1 Minute** (the strategy refuses any other). Trading hours: **CME US Index Futures ETH**.
- **Days to load: 45.** B's entries need 14 full sessions before the first signal.
- Add the strategy **from the chart**: **MnqMomentumRunner**, account **SimRunner**, **Enabled**.

## Strategy settings (all are the defaults except the account)

**Group 1 (Trading):**

| Setting | Value |
|---|---|
| Place orders | **On** |
| Runner exit (off: B's take-profit) | **On** (Off is "B-protected", the comparison's second configuration) |
| Max planned loss per position, $ (costs included) | **200** |
| Max contracts | **4** |
| Commission per side per contract, $ (for sizing) | **0.95** |
| Sizing reserve, ticks (2 at entry + 2 at the stop) | **4** |
| B exits: take-profit, noise units | 1.5 (unused while Runner exit is on) |
| Runner: trail, x ATR | **3.0** |
| Runner: trail starts at this many R | **2.0** |
| Runner: ATR length, 5-minute bars | **14** |
| Flat by, minute of day New York | **955** (15:55; 5 minutes before an earlier session end) |

**Group 2 (Account):**

| Setting | Value |
|---|---|
| Evaluation: profit target, $ | **3000** (closes everything and stops at $3,025 realized, a $25 margin) |
| Evaluation: trailing drawdown, $ | **2000** |
| Reserve above the liquidation line, $ | **300** |
| Daily net-loss backstop, $ (planned risk included) | **400** |
| No entries after this many losing positions today | **2** |
| Account starting balance, $ | **50000** |
| Evaluation start | **(empty)** in live/practice use: the account's own balance is the evaluation's |
| Live: read the account's balance from the broker | **On** |
| Live: remember the highest equity, the pass and today's losers in a file | **On** |
| Live: the account's liquidation threshold now, $ | **0** on a fresh account. On an account that has already traded, enter the threshold Apex shows |

**Group 3 (Entries, B's):** Skip dates and Fed dates at their defaults (they run to the end of 2027).

**Fixed by the strategy** (nothing to set): Calculate on bar close; 1 entry per direction, unique entries; exit on
session close on; start behavior wait until flat.

When everything matches, save it as a template named **RUNNER-CANDIDATE** (the template menu at the bottom of the
strategy dialog).

## Strategy Analyzer (to reproduce the comparison natively)

Same settings, with these changes:
- **Account Backtest**; slippage **1**, then **2**; commission on ($0.95 a side).
- **Evaluation start** = the session the evaluation starts (yyyy-MM-dd). Each start date is a separate run.
- Data: MNQ 09-26 to the 9/10 roll session, then 12-26 (as `research/mnq_bars.py` builds it), or the single
  contract's own data with that limitation noted.

## Each session

- **Before 09:30 New York:** connected, chart open, strategy enabled. The Output's first line is "MNQ runner
  settings:". Check: "PlaceOrders True, RunnerExit True, MaxRisk 200, MaxContracts 4, trail 3 x ATR(14, 5 min) after
  2R".
- **After 16:00:** save the NinjaScript Output as `RUNNER_<yyyy-mm-dd>_output.txt` and export the day's Executions.
  Each skipped signal has its own Output line ("signal ... not taken: <reason>").
- **Stop the test only for an operational fault:** a position without a stop; a fill the Output does not explain; a
  runtime error or a disabled strategy; a mismatch between the account's and the strategy's position.
- **Never change a setting during the test.**

**Limits of the protections:** they are planned. A gap, a fast market or a failed order can exceed the $200 per
position, the $400 day, and the $300 reserve.
