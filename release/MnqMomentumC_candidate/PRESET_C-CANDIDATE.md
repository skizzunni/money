# Preset C-CANDIDATE: candidate C on a simulation account

**For a native check or practice only:** a NinjaTrader simulation account, never a paid evaluation account. The
pre-registered comparison in `docs/CANDIDATE_C.md` decides adoption. Frozen B (`MnqMomentumB_v1`) is unchanged and
stays the benchmark.

## Account

1. Control Center → Accounts → right-click → create a **new simulation account** named **`SimC`**, initial balance
   **$50,000**.
2. Assign a commission template of **$0.95 per side per contract** to SimC.
3. Reset SimC to $50,000 before the first session. Delete
   `Documents\NinjaTrader 8\MnqNoiseMomentum\c-account-SimC.txt` if an earlier test left one: it holds the remembered
   highest equity and pass.

## Chart

- Instrument: **MNQ front month**: DEC26 now; MAR27 from the December roll (switch after a session's close).
- Bars: **1 Minute** (the strategy refuses any other). Trading hours: **CME US Index Futures ETH**.
- **Days to load: 45**: the signals need 14 full sessions first.
- Add the strategy **from the chart**: **MnqMomentumC**, account **SimC**, **Enabled**.

## Strategy settings (all at their defaults)

**Group 1 (Trading):**

| Setting | Value |
|---|---|
| Place orders | **On** |
| Max planned loss per position, $ (costs included) | **200** |
| Max contracts | **4** |
| Commission per side per contract, $ (for sizing) | **0.95** |
| Sizing reserve, ticks (2 at entry + 2 at the stop) | **4** |
| Flat by, minute of day New York | **955** (15:55; 5 minutes before an earlier session end) |
| Output: a line for every check past a line | **On** |

**Group 2 (Account):**

| Setting | Value |
|---|---|
| Evaluation: profit target, $ | **3000** (an open profit of $3,025 closes the position; the pass counts only once realized) |
| Evaluation: trailing drawdown, $ | **2000** |
| Reserve above the liquidation line, $ | **300** |
| Daily net-loss backstop, $ (planned risk included) | **400** |
| No entries after this many losing positions today | **2** |
| Account starting balance, $ | **50000** |
| Evaluation start | **(empty)** live: the account's own balance is the evaluation's |
| Live: read the account's balance from the broker | **On** |
| Live: remember the highest equity, the pass and today's losers in a file | **On** |
| Live: the account's liquidation threshold now, $ | **0** on a fresh account; otherwise the threshold Apex shows |

**Group 3 (Entries, B's):** Skip dates and Fed dates at their defaults (to the end of 2027).

**Group 4 (Comparison):** Signals from B's model position **Off**; Pass only on realized profit **On**. These two
switches exist only to reproduce the comparison's C0 and C1a. Leave them as they are.

**Fixed by the strategy:** Calculate on bar close; 1 entry per direction, unique entries; exit on session close on;
start behavior wait until flat.

Save as a template named **C-CANDIDATE**.

## Strategy Analyzer (to reproduce the comparison natively)

Same settings, with:
- **Account Backtest.**
- **Slippage 1, then 2.**
- **Commission on.**
- **Evaluation start:** each start session in turn (yyyy-MM-dd) for the evaluation replay.
- **Continuous research:**
  - Evaluation target **0**, trailing drawdown **100000**, reserve **0**;
  - evaluation start **empty**.
- **Data:** MNQ 09-26 to the 9/10 roll session, then 12-26, or the single contract's data with that limitation noted.

## Each session

- **Before 09:30 New York:** the Output's first line is "C settings:". Check "PlaceOrders True, SignalsFromModel False,
  PassOnRealizedOnly True, MaxRisk 200, MaxContracts 4".
- **After 16:00:**
  - Save the NinjaScript Output as `C_<yyyy-mm-dd>_output.txt`. Every qualifying check has a line: "entry sent", or
    "not taken: <reason>".
  - Export the day's Executions.
- **At the end of a run:** the "C audit" lines report:
  - data coverage, complete sessions and the warm-up;
  - first and last trades;
  - signals, entries, and refusals by reason;
  - whether trading stopped. `research/output_audit.py` reads them.
- **Stop the test only for an operational fault:**
  - a position without a stop;
  - a fill the Output does not explain;
  - a runtime error or a disabled strategy;
  - a mismatch between the account's and the strategy's position.
- **Never change a setting during the test.**

**Limits of the protections:** they are planned. A gap, a fast market or a failed order can exceed the $200 per
position, the $400 day, and the $300 reserve.
