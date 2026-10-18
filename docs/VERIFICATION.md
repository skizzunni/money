# Verification of the current implementation (October 18, 2026)

Labels: **executed** (run here), **from the exports** (the user's two NinjaTrader exports), **implemented + tested**,
**blocked** (needs the user's MNQ bars or NinjaTrader), **not done**.

## 1. What supports every reported comparison

| Item | Where |
|---|---|
| Original strategy + engine (commit `d4cb597`, the first export) | `docs/baseline/*.d4cb597.cs.txt` |
| Revised strategy + engine (commit `23bca3b`, the second export) | `git show 23bca3b:ninjatrader/...`; diff from the original: `docs/baseline/original_to_revised.diff` |
| Current files (this commit: + ledger, gate, half-off option; all off by default) | `ninjatrader/Strategies/MnqNoiseMomentum.cs`, `ninjatrader/AddOns/MnqNoiseEngine.cs` |
| The harness (NinjaTrader stand-in, runner) | `ninjatrader/tests/Sim/` (`NinjaTraderStubs.cs`, `Program.cs`, `Sim.csproj`), `research/controlled.py`, `research/data_gaps.py` |
| Exact configuration of every controlled run | `verification/trades_*.tar.gz`: one `*.config.txt` per run (sim build, data file, dates, treatment, every property passed) |
| Per-trade exports of every controlled run | the same archives: one CSV per run (direction, entry/exit bar and time, prices, exit reason, $, entry name, contracts) |
| Summaries | `verification/summary_*.csv` |
| Reruns of rounds 132-139 on complete sessions | `verification/reruns/round*_complete_sessions.txt` |
| The user's exports | `data/nt_strategy_analyzer_2026-08-18_10-17.csv` (original), `data/nt_strategy_analyzer_revised_trades.csv` + `_summary.csv` |

**Data provenance** (SHA-256 in `verification/data_sha256.txt`; the files are too large for the repository):
- `nq1m_scaled.pkl`: NQ futures 1-minute bars, January 2015 - July 2025, from the public Hugging Face dataset
  `mdelcristo/NQ-F_1min_OHLCV_Parquet` (MIT licence; real exchange prices including the contract rolls), each month's
  prices rescaled to today's level (`research/timeframes.scaled`: a factor per month so the month's first close is
  30,661, rounded to the 0.25 tick). The rescaling makes a jump at each month boundary (median 3.7%).
- `nsx1m_scaled.pkl`: HistData.com `NSXUSD` 1-minute bid prices (a CFD on the Nasdaq-100 cash index), November 2010 -
  September 2026, rescaled the same way. Not futures: no volume, a basis to futures, and holes (below).
- **Neither is the user's MNQ DEC26 data.** Every result below is on these, not on the bars NinjaTrader used.

## 2. The harness against NinjaTrader on the user's bars - blocked

Needs the 1-minute MNQ DEC26 bars of the runs (Tools -> Historical Data -> Export). With them: both exports replayed
in the stand-in on those bars, compared trade by trade on order timing, stop changes, fills, quantities, fees and
exits, every difference listed. What can be said without them, from the exports: commission $0.95 a contract a side
in both runs (matching the harness); the original export's fills are one tick against every market order (slippage
1), the revised one's none.

## 3. Original / revised x 0 / 1 tick on identical data - executed (not on the user's MNQ bars: blocked)

NQ futures 2015-2025, complete sessions, breakout on, net $ (both code versions compiled against the same stand-in;
identical bars, 14-session warm-up, $0.95 a side, fixed sizing):

| | 0 ticks | 1 tick |
|---|---|---|
| original (`d4cb597`) | 203,074.3 | 175,021.6 |
| revised (`23bca3b`) | 203,082.0 | 175,144.7 |

Code effect +7.7 at 0 ticks, +123.1 at 1 tick; slippage effect -28,052.7 (original), -27,937.3 (revised);
**interaction +115.4**: the two do interact (the tighter stop and the tick both move the same stop-outs), but the
interaction is 0.4% of the slippage effect. Untreated data: the same code and interaction figures. Index 2025-26:
code +54.0 / +56.0, slippage about -3,170, interaction +2.0. **On the user's 70 shared trades** (from the exports):
the +$415 cannot be split exactly without the bars; the attribution in CONTROLLED.md (about $78 code, $337 slippage)
is an inference from the trade list, not a measurement.

## 4. September 16, 11:31 - partly confirmed

Confirmed from the exports: original entry 29507.00, stop exit 29482.00 (exactly 25 points, the $200 cap from the
fill), MAE exactly $200.00, i.e. the trade's worst price was 29482.00; revised entry 29506.75 (one tick better), exit
29509.25 at 11:56 (entry + 2.5, the lock), +$12.40. **Inferred, not confirmed**: that the revised stop sat at 29481.75
and that no later bar touched it before the lock armed - the minute bars are needed (blocked). Oct 12: the tighter
stop at 30947.00 is consistent with the ratchet; not confirmed without the bars.

## 5. Risk controls: what is fixed, with tests

| Control | Status | Tests (`tests/test_ninjatrader.py`) |
|---|---|---|
| Execution-based daily accounting | **implemented + tested** (this commit): the day's trades from NinjaTrader's own trade records (built from executions), a position filled in parts counted once; dashboard "Today (fills, both setups)" | `test_daily_ledger_from_fills_counts_positions_not_fills` (every entry split into two fills: same trades, same line); mutation: counting fills as trades fails it |
| Shared bot/breakout risk limits | **implemented + tested, off by default**: `DailyMaxLosers`, `DailyLossLimit` (the new trade's planned risk included), in front of both entry paths; live, the $ check uses the worse of the strategy's and the account's realized P/L | `test_daily_gate_max_losers_both_setups`, `test_daily_gate_loss_limit_both_setups` (both show the gate binding); mutation: the breakout path ungated fails |
| Partial fills | **partly**: accounting tested with split fills (above); the strategy's management of a position that fills in parts (NinjaTrader's `PerEntryExecution`: a stop and target per part) is **not tested** - the stand-in fills an entry at once. Needs Playback |
| Restart persistence | evaluation target from the account's balance (`test_evaluation_target_from_the_account_after_a_restart`), payout cycle in a file (`test_payout_cycle_survives_a_restart`, 7 restart points), account-position guard (`test_account_position_guard`). **Not persistent**: the daily ledger and gate after a restart count the trades NinjaTrader replays from history (virtual), not the account's real fills; live, the $ check also reads the account's realized P/L, which does survive |
| The model's own loser count | unchanged: the engine still counts its model trades (bot only) for its 3-loser rule |

## 6. Session close, and the ratchet

- **Correction**: "the session-close change cannot affect backtests" was wrong as stated. NinjaTrader's exit 60 s
  before the session end acts on the session of the chart's trading-hours template: with an RTH template (session
  end 16:00) it closes at 15:59, a minute before the strategy's own 16:00 exit, which changes those trades' exits in
  a backtest; with an ETH template (end 17:00, apparently the user's) it never acts in a backtest, because the
  strategy is flat by 16:01. The stand-in has no template, so neither case is tested here.
- **The ratchet, defined**: within one position (entry to exit), every stop price the strategy sends for a long is
  greater than or equal to the previous one, and for a short less than or equal, starting from the bracket stop
  sent with the entry; the take-profit is not part of it; a new position starts afresh. Tested on every stop order
  sent: `test_stop_ratchet_within_a_position` (with the setting off, the same bars break it, so the check can fail).
- **Its value, re-measured on complete sessions** (round 139 rerun): neutral - the account nets $64.0 / $39.7 /
  -$29.0 / $38.8 a week with it against $64.7 / $39.7 / -$29.1 / $34.4 without; it no longer passes its adoption bar.
  It stays on as a risk control (a stop never moves back toward the price), not as a performance improvement; off is
  one setting.

## 7. Missing data and its treatment - executed

`research/data_gaps.py`, on the controlled windows:

| | NQ futures 2015-25 | Index 2025-26 |
|---|---|---|
| Sessions | 2,680 | 323 |
| Weekdays with no bars | 34 (exchange holidays: Good Friday, Christmas, New Year...) | 4 |
| Sessions ending before 15:59 | 88 (holidays with early closes, half days) | 32 (half days and **data holes**: Oct 27-31 2025, several days in March 2026) |
| Sessions missing minutes mid-session | 5 (90 minutes) | 20 (87 minutes) |
| Trades crossing a session end (exit filled at a later session's open) | 6, net +$2,726.50 | 6, net +$1,839.20 |
| In the research engine (rounds 132-139) | 3 bot trades, +$2,345 | 15 bot trades (2011-26), +$15,135 |

**Treatment** (reported beside the untreated results, nothing dropped silently): no new trades on a session whose
09:30-16:00 data is incomplete (`controlled.py ... complete`; `MNQ_COMPLETE_ONLY=1` for the research scripts) - for
holidays and half days this is the strategy's own rule (its skip dates), for data holes it is data cleaning.
**Reruns** (all in `verification/`): the controlled matrix (both treatments, both datasets) and rounds 132-139.
**What changed**: the 16:00-bar bug only affected the controlled harness (fixed, rerun). On complete sessions:
round 139's ratchet no longer passes (above); round 133's pick becomes "funded 3 MNQ" and passes its bar (recorded,
**not adopted**: no optimization during verification); rounds 134 (breakout $400), 135, 136, 137, 138 keep their
decisions; round 132's latest window turns negative (the funded strategy's mean day -$6). On the index data 52 of
323 sessions (16%) are incomplete and the latest-window results move a lot with them (net $15,333 -> $2,407 at one
tick): **the latest 15 months are not reliable evidence either way**.

## 8. Evaluation outcomes

Rules modelled (Apex 50K intraday-trail evaluation, from third-party summaries of Apex's help center): start at
$50,000; **pass** when equity (balance + open P/L) reaches +$3,000 (+$25 for the closing fees, "close at target");
**fail** when equity touches the threshold, $2,000 below the highest equity so far including open profit (it never
stops trailing during the evaluation); no daily loss limit; 30 calendar days; no minimum days.
- **controlled.py** (one window per session): a window starts at each session's first minute and runs 30 calendar
  days. Passed: the target is reached before any minute whose worst equity touches the threshold (each minute's worst
  point is compared with the peak before that minute; if both happen in one minute, the fail counts). Failed: the
  threshold first. **Expired** (reported as "timeout"): neither within 30 days. **Unresolved**: windows whose 30 days
  run past the end of the data are not counted at all.
- **The research slot model** (rounds 132-139): from each start session, evaluations one after another (a new one
  the session after a fail or an expiry), each judged as above; after a pass, the funded account until it fails or
  pays its sixth payout (threshold stops at +$100, daily loss limit $1,000 / $2,000 / $3,000 by balance, five $200
  days, $52,600, the 50% rule, the caps).
- **Overlap**: windows start every session, so they overlap heavily (consecutive windows share 29 of 30 days). The
  percentages are shares of start dates, not independent trials; their effective sample is far smaller than the
  count (roughly one independent window a month), and no confidence interval here treats them as independent.

## 9. The forward test: frozen before it starts

**Frozen**: this commit's two files, both arms identical except one setting.
- **Arm A, the current exit**: every setting at its default (bot 4 MNQ / $200 / 3 losers; breakout $400 / 1-10 MNQ /
  take-profit 8 stops; lock at 1R to entry + 2.5; take-profit 1.5 noise units; stop ratchet on; payout stop and
  evaluation target as default; daily gate off; `PartialAtR` 0).
- **Arm B, half off at 1R**: the same, with `PartialAtR` 1: a limit for half the bot's contracts at the fill +/- 1R
  (R = the initial risk, 25 points), sent at each bar's close while the full position is open (so it works from the
  bar after the fill), the other half keeping every rule; R is never redefined. Verified trade for trade against the
  research model with the same definition (`test_half_off_at_1r_matches_the_bot`, mutation-checked).
- **Setup**: two simulation accounts used for nothing else (Sim101 for A; a new one, e.g. "SimHalf", for B: Control
  Center -> Accounts -> right-click -> Add simulation account), the same MNQ contract and data connection, each arm on
  its own 1-minute chart, Place orders on, evaluation mode (the Sim account names are not APEX-: FUNDED off).
- **Run**: from the first session after installation, 20 sessions. No setting changes during the test; a defect
  found stops the test (it does not get tuned around).
- **Recorded daily**: both accounts' executions (export) and the 1-minute bars; every trade replayed in the stand-in
  on those bars must match entry, stop changes and exit within a tick and P/L within fees.
- **Judged on, defined now**: net after costs, intraday equity drawdown, worst day, longest losing streak, and the
  replayed evaluation outcome (pass / fail / unresolved from the first session). **Stop at once** on: a position
  without a stop, an execution the replay can't explain, a day below -$1,100 in either arm.
- **It is a pilot.** Twenty sessions cannot show a difference of the size the research found (half at 1R lowered the
  intraday drawdown 13-25% for 31-38% less net over years); the pilot checks that both arms trade as tested, and
  gives a first, uncertain read. Any decision needs the 20 sessions repeated, or more.
