# v2 stops for the Noise-Area Momentum v1.5 rules (plan of 2026-11-10)

The plan: build the v1.5 rules with eval-safe stops (daily loss limit, a lock trigger in noise units, a gap guard,
tighten-only), pre-register gates, test on NQ 2015-2025, and report the $750/day question honestly. This file records
each phase as it is done. Attachments that arrived: the Pine trade log screenshot (Nov 2-9). The Pine v1.5 script used
is the user's archived file `pine/reference/mnq_noise_momentum_v1.5_user.pine`; the C# engine is
`ninjatrader/AddOns/MnqNoiseEngine.cs`. The NinjaTrader trades 229-233 screenshot did not arrive.

## Phase 0: the firm's rules (to confirm)

From Take Profit Trader's help center as read on 2026-11-05 (docs/NINJATRADER_V38.md, "The user's firm"); the user
should confirm these against the current pages:

| Rule | Test (evaluation) | PRO (funded) |
|---|---|---|
| Trailing drawdown | $2,000, **end of day** | $2,000, **intraday, including open profit**, until the floor reaches $50,000 |
| Profit target | $3,000 | none |
| Minimum days | 3 (the plan's gates use 5, stricter) | none |
| Consistency | best day under 50% of the profit | none |
| Daily loss limit | none | none |
| Automation | **not allowed**: "Automated trading systems, bots, or algorithmic execution tools are not permitted" | **not allowed**: "All trades must be manually executed by the trader" |
| Other | positions closed by 16:55; at most 60 micros | flat 1 minute either side of FOMC 14:00, NFP and CPI |

**So on this firm the bot is alert-assisted manual trading only:** NinjaTrader runs on SIM / paper, the strategy
sends the heads-up and the bracket (entry, stop, target) before each check, and the trader places every order
themselves. Bot trades must never be passed off as manual. The NinjaTrader strategies' "Place orders" switch must stay
off on a Take Profit Trader account. Since the funded account trails intraday, every gate below is run under both
end-of-day and intraday trailing.

## Phase 1: reconciliations

**(a) Pine against NinjaTrader on Nov 2-9.** The Pine log in the screenshot is **not v1.5**. It has v3.8's "Why" column
("locked win", "max loss stop", "stop at the line", "16:00 close") and sizes from 5 to 12 contracts, which v3.8's
Funded growth mode sets. In v1.5 the size is a fixed input. Reading the log row by row:
- Nov 5 has **four** Pine trades, not one: 10:30 short 7 (+$4,303.32, target), **11:00 short 10** @ 26974.25 → 11:30
  27069.50 (−$1,917.40, max loss stop), **12:00 short 8 @ 27151.25 → 27149.00 (+$26.08, locked win)**, and 12:00 short 8
  @ 27116.00 → 15:30 26743.25 (+$5,954.08, 16:00 close). The −$1,917.40 trade entered at 11:00. The 12:00 trade at
  27151.25 is exactly NinjaTrader's #229 (short 8 @ 27151.25 → 27149.00, +$26.08). **Pine and NinjaTrader agree on Nov 5
  12:00.** The plan's "divergence" set the 11:00 trade beside the 12:00 one. No data-feed, contract or warmup difference
  shows in that row. (Trades 230-233 can be checked when that screenshot arrives.)
- **The two big losses were not gaps through a stop.** Both filled about 95 points from entry: Nov 5 11:00, 26974.25 →
  27069.50 = 95.25 points on 10 MNQ; Nov 6 10:00, 27346.25 → 27250.50 = 95.75 points on 12 MNQ. Funded growth's max loss
  is **$187.50 a contract = 93.75 points**, measured from the expected fill. Both exits are that stop plus 1.5-2 points of
  slippage and fill difference. The 14.6- and 17.5-point "intended stops" in the plan are $350 ÷ qty ÷ $2, v1.5's
  setting, which this log did not use. **The stop did its job; it was 94 points away on 10-12 contracts.** So the loss
  came from size × per-contract risk, which v1.5 at a fixed 2 MNQ and its own $350 cap would not repeat. A real gap
  (a fill far past a resting stop) is still possible at the open or on news, and the gap guard and G5 measure it.

**(b) Reversals.** v1.5 reverses **only in its "Half-hour check" exit mode**. In its default, "Resting stop at the line",
it does not reverse: `inPosStop = useStop and pos != 0` skips the reverse branch, so an open trade ends only at its
stop, lock, target or 16:00. The C# engine never reverses. The Python reference (`mnqbot/noise.py`) and every
historical backtest in this repository since the resting stop (v1.1) use the resting-stop mode: **no reversals**, the
same as the C# engine. The comparisons below use that mode.

**(c) The $34/day number.** No result in this repository is "$34 a day" exactly. The nearest are the funded measures of
the 50K bot (G372 / G409 / G415 / G421): **per account, total, starting at 1 MNQ and adding a contract per $1,500 of
profit**: U48 $30.4 a session on the 16 recent 12-month starts, G421's variant D $35.1, U58 $49.2. They are not per
contract. The Pine's long-run claim of about $28 a day a contract matches round 32 (`docs/RESULTS.md`, NQ futures
2015-25 at 1 contract and a $117 max loss: $27.94 a day). The plan is right that these are to spec, not something to
"fix".

**(d) The 5-12 sizing.** In v3.8's Funded growth (Pine and NinjaTrader alike): 1 MNQ, plus one contract per $1,500 of
profit since the start date (faster above $9,000), up to 60, each trade's risk at $187.50 a contract, cut to the day's
budget and the room above the trailing floor. **On TradingView the profit is the chart's own backtest** since its start
date, so after a strong simulated history the Pine shows 10-12 contracts that no real account has earned. NinjaTrader
sizes from the smaller of the strategy's equity and the live account's (`EqEff`), so live it cannot size from
simulated profit. The plan's fixed 2 MNQ for the evaluation replaces all of this.

## Phase 3: pre-registration (written and committed 2026-11-10, before any v2 backtest)

**What is compared.** The v1.5 rules (noise lines, 14-session lookback, 12 half-hour checks, resting stop at the line
0.24 noise units past it, max loss $350 for the position, lock at 1 max loss of profit to entry + 2.5 points, 1.5-noise-
unit take-profit, 4-loser daily limit, the Fed rule, flat at 16:00, skip dates; no reversals) at a **fixed 2 MNQ**:
- **v1.5 stops:** as above.
- **v2 stops:** DailyLossLimit −$400 (a resting stop where today's closed P/L plus the open trade's P/L, after its exit
  commission, reaches −$400; then no new entries that day; also no new entries once the closed P/L is at or below
  −$400), LockTriggerNoise 0.75 (the lock arms when a bar reaches 0.75 × the current check's noise × the entry price in
  profit; the lock stop stays entry + 2.5 points), GapGuard on (a stop that fills more than 2× its intended loss distance
  from the entry ends new entries for the day), TightenOnly on (the stop only ever moves toward the price).
- **v2 grid (Phase 4):** daily limit −300 / −400 / −500 × stop buffer 0.24 / 0.35 × gap guard on / off (12 variants).

**Data and costs.** NQ futures 2015-2025, 5-minute bars, back-adjusted at the rolls and rescaled to today's price level
(`nq5m_scaled.pkl`, as every NQ result in this repository), regular hours. $0.62 a side a contract; **2 ticks** of
slippage on every market and stop fill (entry and exit sides), none on the take-profit limit.

**The evaluation replay.** Consecutive non-overlapping 30-calendar-day windows from 2015-01-05 to 2025-12-31, each a
fresh $50K evaluation at 2 MNQ under Take Profit Trader's Test rules: pass when the closed profit is at least $3,000,
the account has traded on at least 5 days and the best day is under 50% of the profit (checked at each day's end; if
the best day is too large, trading continues); fail when the balance, open trades marked at each bar's worst price,
touches the floor (the highest end-of-day balance less $2,000, at most the start); expiry when the 30 days end with
neither. **Intraday variant** (the funded account): the floor trails the highest balance *including open profit*
(bar extremes, the worst order inside a bar), stopping at the start; every gate is reported under both.

**The gates** (on the windows, 2 MNQ):
- **G1** pass rate ≥ 60%;
- **G2** expiry ≤ 15%;
- **G3** the worst window's drawdown ≤ $1,500 (largest fall of the end-of-day balance from its high within a window);
- **G4** profit factor ≥ 1.35 (all trades 2015-2025, run continuously at 2 MNQ);
- **G5** largest single-trade loss ≤ $500 (all trades 2015-2025; the gap audit lists every trade whose stop filled
  more than 2× its intended distance);
- **G6** NinjaTrader ↔ Python trade-for-trade parity of the engine, before any of the above counts.
MNQ (the user's 2026 bars) is reported separately as an execution check, not a gate.

**Selection.** At most one variant: among v1.5 and the 12 v2 variants, those passing G1-G6 under end-of-day trailing
(the evaluation's rule), the highest pass rate (ties: the smaller G3). Intraday results are reported beside it.
**Kill criteria:** if the selected v2 variant does not beat v1.5's pass rate (G1), or v2 fails G5, the v2 stops are
rejected and the answer is "size + daily limit only", with no further stop tuning on this data.

**The tight-stop grid** (reported, not selected on): max loss cap $100 / $200 / $350 × line buffer 0.10 / 0.24 / 0.35 at
2 MNQ with v1.5's lock (1 max loss): $ a day a contract, max drawdown a contract (end-of-day), profit / drawdown, win
rate, profit factor, 2015-2025. **Separation:** (i) cap $100 / $200 / $350 with the lock trigger fixed at 0.75 noise
units; (ii) cap fixed at $350 with the lock trigger at the points the $100 / $200 / $350 caps imply under v1.5 (25 /
50 / 87.5 points at 2 MNQ). If the long run refutes the $100 cap, $350 stays.

**Phase 4b.** For the selected variant (v2 defaults if none is selected): $ a day and max drawdown at 1, 2, 3, 5 and 8
MNQ, and whether any size reaches $750 a day with max drawdown under $2,000. Then the noise + Williams combination
(both sleeves, one shared risk budget): $ a day, drawdown and profit / drawdown against noise-only v2; if it does not
beat noise-only's ratio, no sizing up.
