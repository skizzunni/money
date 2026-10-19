# MNQ Momentum B v1: results and readiness (October 18, 2026)

**B** = the strategy with the breakout off: momentum only, 4 MNQ, $200 max loss a trade, 3 losers a day, lock at 25
points to entry + 2.5, take-profit 1.5 noise units, flat by 16:00. Code: `MnqMomentumB_v1` (sha256 in `INSTALL.md`).

## What was tested natively in NinjaTrader (run by the user; analysed from its own files)

**Runs:**
- Strategy Analyzer, MNQ DEC26 (one contract, not merged), 1-minute bars, trading hours CME US Index Futures ETH.
- Commission $0.95 a side.
- Slippage 0, 1, 2 ticks.

**The 22 native runs of the day** (all configurations): 3,188 fills, **0 rejected orders, 0 ignored orders, 0
runtime errors**.

**B over the longest native period:**
- Requested 1/1 to 10/17/2026. The data starts 5/3, and 5/22 to 6/26 has no bars.
- **Traded 6/29 to 10/16: 77 sessions, warm-up before.**

| B, after commission | 0 ticks | 1 tick | 2 ticks |
|---|---:|---:|---:|
| Trades | 119 | 118 | 118 |
| Net | $13,175.60 | $12,889.20 | $12,663.20 |
| Closed-trade drawdown | $2,736.80 | $2,808.80 | $2,882.80 |
| Longest losing streak | 6 | 6 | 6 |
| Worst day | −$622.80 | −$628.80 | −$634.80 |

**Monthly** (0 ticks):

| Month | Net |
|---|---:|
| June (2 days) | +$1,350 |
| July | −$1,918 |
| August | +$3,360 |
| September | +$5,699 |
| October 1-16 | +$4,684 |

The largest 5 trades are 75% of the net.

**Slippage:** NinjaTrader slips market entries, market exits and stops alike. (An earlier version of this report
said it left most stops unslipped; that was a misreading, corrected in docs/MNQ_NATIVE.md.)

## Against the evaluation's rules

**Rules used:** $50K, $3,000 target, $2,000 trailing drawdown that follows unrealized peaks, 30 calendar days.
- These come from third-party summaries. Apex's own pages could not be reached from here.
- Daily loss limit and minimum trading days are unconfirmed; sources conflict.
- **Confirm them on your account.**

**Native, from the fills (4 MNQ, 1 tick):** 56 start dates, 6/29 to 9/17.

| Size | Pass | Fail | Expired |
|---|---:|---:|---:|
| 4 MNQ | 34 | 5 | 17 |
| 2 MNQ | 12 | 0 | 44 |

**This is weak evidence:**
- The 56 windows overlap almost entirely: about 2-3 independent 30-day windows.
- They cover B's best stretch.
- They use **closed-trade equity only.** The fills carry no unrealized peaks, which the trailing rule counts. The true
  trailing risk is higher.
- The 2 MNQ row is the 4 MNQ fills halved, not a native run.

**The native fact that matters most:** in this same period, B's **closed-trade** drawdown at 4 MNQ reached
$2,737-2,883, already more than the $2,000 the account allows. The intraday drawdown is at least as large.

**The stand-in simulator on the user's MNQ bars, with intraday peaks** (added after the bars arrived; corrected
accounting; docs/MNQ_NATIVE.md):
- **Data:** the traded contracts (09-26, then 12-26 from the 9/10 roll).
- **Native check:** NinjaTrader's own runs were reproduced only for the 20 October trades: all 20 exactly at 0 ticks;
  19 of 20 at 1 and 2 ticks, with totals equal to the cent.
- **Result, 44 fully observed starts (7/20 to 9/17), 4 MNQ, at 1 and at 2 ticks:** 24 pass / 6 fail / 14 expire.
  Back to back: 4 / 1 / 1.
- **Limits:** about 3 independent windows, and the period that chose B.

**Not native, for context only (rescaled NQ and index data on the stand-in; not proof about MNQ):**
- Over ten years of NQ, the same rules at 4 MNQ: **31.6% pass, 60.7% fail, 7.7% expire.**
- At 2 MNQ / $100: 7.7% pass, 14.7% fail, 77.6% expire. Smaller size mostly turns outcomes into expiries; it does not
  improve passing.
- Details are in `docs/EVALUATION.md`.

## Verdict

**This version does not meet the goal.** It does not show a credible path to passing the 50K evaluation without
excessive failure risk:
1. **The only long test against these rules shows it failing about 61% of evaluations at 4 MNQ** (substitute data).
   Smaller size does not fix that; it mostly runs out of time.
2. **The native MNQ evidence is one 77-session stretch:** about 2-3 independent evaluation windows. Even there, B's
   closed drawdown went past the $2,000 trailing allowance.
3. **On the user's MNQ bars (the simulator, July to October 2026) it passed more than it failed.** But that is about
   3 independent windows from the period that selected it, against ten years of substitute data that say the
   opposite. It is not enough to establish a pass rate.

**Ready for a frozen practice test: yes, on a simulation account only, as an operational test.**
- The package compiles in NinjaTrader and ran clean in 22 native backtests.
- Its settings are frozen (`PRESET_B-PRACTICE-v1.md`).
- What it has never done is run live: real-time data, restarts, the account checks, and the $3,000 close live. A
  practice test checks exactly that.
- It does not change the verdict above. A 20-40 session practice result cannot establish an edge or a pass rate.
- **Nothing here supports buying an evaluation on the expectation of passing.**

## Unresolved

- **The account's exact rules** (daily loss limit, minimum days, time limit): not confirmed.
- **Untouched MNQ data** (03-26, 06-26): not provided. The forward practice test is the validation.
- **The zero-trade run of 8/9 to 10/17:** cause unknown; needs its original code and settings with diagnostics.
- **The breakout on ten years of substitute data** added money, which disagrees with the native period. Not resolved;
  B is kept on the native evidence.

Supporting files:
- `docs/REFERENCE.md` (native reconciliation and A/B/C);
- `docs/EVALUATION.md`;
- `docs/NATIVE_RUNS.md`;
- `verification/native_long/` (runs, rebuilt trades, `eval_closed_equity.txt`);
- `verification/`.
