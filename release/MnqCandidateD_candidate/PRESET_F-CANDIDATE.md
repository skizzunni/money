# Preset F-CANDIDATE: MnqCandidateD (D + F1, D + F2)

**Candidate F** (docs/CANDIDATE_F.md) is E's sweep chain with one change: the initial stop of a sweep setup is the
selected FVG's far boundary ∓ 2 ticks, not the sweep extreme. It runs on the same strategy file as D/E, with the
setting **Sweep initial stop = FvgFarEdge**.

**Status:** see docs/CANDIDATE_F.md for the verdict. It is for inspection and native checks unless that document
says it is accepted.

## Chart / Strategy Analyzer

These are as PRESET_D-CANDIDATE.md:

| Setting | Value |
|---|---|
| Instrument | MNQ front month (DEC26 now) |
| Data series | **1 Minute**, trading hours **CME US Index Futures ETH** |
| Days to load / start date | at least 45 days before the first tested session |
| Commission | a template of **$0.95 a side a contract** |
| Slippage | **2 ticks (base)**, 3 ticks (stress) |
| **Order fill resolution** | **High**, 1 Tick if the tick history is loaded (else 1 Second). Tick Replay alone does not establish fill accuracy |
| Calculate | On bar close |
| Entries per direction / handling | 1 / Unique entries |
| Exit on session close | On |
| Stop & target submission | Per entry execution |

## Strategy parameters

| Group | Setting | D + F1 | D + F2 |
|---|---|---|---|
| 1 | Noise momentum / Williams breakout | On / On | On / On |
| 1 | Sweep reversal E1 (higher-timeframe pools) / + session pools E2 | On / Off | On / On |
| 1 | **Sweep initial stop** | **FvgFarEdge** | **FvgFarEdge** |
| 2 | Planned risk budget, $ (2 contracts, all-in) | 125 | 125 |
| 2 | Commission a side, $ | 0.95 | 0.95 |
| 2 | Slippage allowance, ticks a contract: market / limit | 4 / 2 | 4 / 2 |
| 2 | Breakeven stop, points past the fill | 1.5 | 1.5 |
| 2 | Half off at R / runner trail R | 2 / 1 | 2 / 1 |
| 2 | Entry campaigns a day | 3 | 3 |
| 2 | Flat bar (minute of day) | 954 (15:54, filled 15:55) | 954 |
| 3 | Line stop, noise units | 0.24 | 0.24 |
| 3 | Skip dates / FOMC dates | defaults | defaults |
| 3 | NFP dates | as PRESET_D-CANDIDATE.md | same |
| 4 | Evaluation target / trailing drawdown, $ | 3000 / 2000 on an account; **0 / 0 in the Strategy Analyzer** (the replay applies the account) | same |
| 4 | Account starting balance; remember the highest equity | 50000; On | same |
| 4 | Place orders | On | On |

**The F alone diagnostics:**
- noise and Williams off;
- E1 on (F1 only), or E1 and E2 on (F2 only);
- Sweep initial stop FvgFarEdge.

**Sweep initial stop = SweepExtreme** gives E exactly (the D + E1 / D + E2 rows of PRESET_D-CANDIDATE.md).

## Native check

**Steps:**
1. Run the Strategy Analyzer on MNQ DEC26, 9/11 to 10/16/2026, with the settings above at 2 ticks.
2. Export the Trades and the NinjaScript Output.
3. Compare them with `research/d_parity.py`'s D + F1 / D + F2 configurations: the same entries, exits and P/L per
   position.

**What to look for in the Output:**
- Each sweep entry prints its limit, its stop, R, price risk and planned risk.
- A breakeven or trail stop that cannot be placed (beyond the bar's close) is replaced by a market exit named
  "Stop passed".
- A rejected stop closes the position (`StopCancelCloseIgnoreRejects`).
