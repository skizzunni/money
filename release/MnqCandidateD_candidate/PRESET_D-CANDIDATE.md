# Preset D-CANDIDATE: MnqCandidateD (D, D + E1, D + E2)

**Rejected candidate:** for inspection and native checks only (INSTALL.md).

## Chart / Strategy Analyzer

| Setting | Value |
|---|---|
| Instrument | MNQ front month (DEC26 now) |
| Data series | **1 Minute**, trading hours **CME US Index Futures ETH** (E2's session pools need the overnight bars) |
| Days to load / start date | at least 45 days before the first tested session (14 full sessions for the noise lines, a previous week for E1) |
| Commission | a template of **$0.95 a side a contract** |
| Slippage | **2 ticks (base)**, 3 ticks (stress) |
| **Order fill resolution** | **High**, 1 Tick if the tick history is loaded (else 1 Second). This is the granular fill processing; Tick Replay alone does not establish fill accuracy |
| Calculate | On bar close |
| Entries per direction / handling | 1 / Unique entries |
| Exit on session close | On |
| Stop & target submission | Per entry execution |

## Strategy parameters

| Group | Setting | D | D + E1 | D + E2 |
|---|---|---|---|---|
| 1 | Noise momentum / Williams breakout | On / On | On / On | On / On |
| 1 | Sweep reversal E1 / + session pools E2 | Off / Off | On / Off | On / On |
| 2 | Planned risk budget, $ (2 contracts, all-in) | 125 | 125 | 125 |
| 2 | Commission a side, $ | 0.95 | 0.95 | 0.95 |
| 2 | Slippage allowance, ticks a contract: market / limit | 4 / 2 | 4 / 2 | 4 / 2 |
| 2 | Breakeven stop, points past the fill | 1.5 | 1.5 | 1.5 |
| 2 | Half off at R / runner trail R | 2 / 1 | 2 / 1 | 2 / 1 |
| 2 | Entry campaigns a day | 3 | 3 | 3 |
| 2 | Flat bar (minute of day) | 954 (15:54, filled 15:55) | 954 | 954 |
| 3 | Line stop, noise units | 0.24 | 0.24 | 0.24 |
| 3 | Skip dates / FOMC dates | defaults | defaults | defaults |
| 3 | NFP dates | `2026-01-02,2026-02-06,2026-03-06,2026-04-03,2026-05-08,2026-06-05,2026-07-02,2026-08-07,2026-09-04,2026-10-02,2026-11-06,2026-12-04` | same | same |
| 4 | Evaluation target / trailing drawdown, $ | 3000 / 2000 on an account; **0 / 0 in the Strategy Analyzer** (the replay applies the account) | same | same |
| 4 | Account starting balance; remember the highest equity | 50000; On | same | same |
| 4 | Place orders | On | On | On |
| 4 | Print refusals (the daily opportunity audit) | On | On | On |

## What was compared, and how to check it natively

**Every published result is the Python model's.** It was held to this file on the NinjaTrader stand-in
(`tests/test_candidate_d.py`).

**A native check:**
1. Run the Strategy Analyzer on MNQ DEC26, 9/11 to 10/16/2026, with the settings above at 2 ticks.
2. Export the Trades and the NinjaScript Output.
3. `research/d_parity.py`'s comparison applies: same entries, exits and P/L per position.

**Playback:**
1. Market Replay data for the same days, on a Playback connection with a simulation account.
2. With EvalTarget 3000 and EvalTrail 2000, the highest equity is written to
   `Documents\NinjaTrader 8\MnqCandidateD-<account>.txt`. It survives a restart.
