# Candidate: B's entries with risk-budget sizing, account protection and a runner exit (October 19, 2026)

Status: **built and tested on the stand-in simulator; not run in native NinjaTrader.** Frozen B
(`release/MnqMomentumB_v1`, sha256 unchanged) is the comparison and is not modified.

## 1. The rules as implemented (`ninjatrader/Strategies/MnqMomentumRunner.cs`)

**Entries (B's, unchanged):**
- B's own engine (`AddOns/MnqNoiseEngine.cs`, unchanged), with B's settings: noise band, 14-session warm-up,
  half-hour checks 10:00-15:30, both directions, B's skip and Fed dates. The breakout is not part of it.
- One position at a time. Position, quantity and average price come from NinjaTrader's Position, which is built from
  the executions.
- A signal arriving while the candidate still holds a position is not taken.

**Risk before each entry:**
- Stop distance = B's protective stop (the noise-line stop or the 25-point cap, whichever is closer), in whole ticks.
- Risk per contract = stop points × $2 + 2 × $0.95 commission + 4 ticks reserve (2 at the entry, 2 at the stop).
  That is 2 × points + $3.90.
- Budget = the smallest of:
  - $200;
  - half the room above the reserve line;
  - what is left of today's $400 backstop after the day's realized result.
- Contracts = min(4, floor(budget / risk per contract)). If not even one contract fits, there is no trade.
  - Example: a 25-point stop is $53.90 a contract, so 3 contracts ($161.70).
- The stop goes in, in ticks from the fill, before the entry. It never widens, and the strategy never adds to a
  position.
- The reserve is used for sizing only. Results are the fills' P/L less the actual commission; slippage is not charged
  twice.

**Exits:**
- **B's protections:**
  - the protective stop from the fill: the noise line, at most 25 points;
  - the lock: at +25 points the stop moves to entry + 2.5;
  - the stop only ever tightens.
- **Runner (Runner exit on):**
  - no take-profit of its own;
  - R = the fill to the initial stop, fixed for the position;
  - once the best price since the entry (completed bars from the fill on) is 2R past the fill, a trail sits at
    best − 3 × ATR(14) for a long (best + 3 × ATR for a short);
  - ATR(14) is Wilder's, on completed 5-minute bars of 09:30-16:00;
  - the stop is the tighter of the trail and B's stop, rounded to a tick toward the price, and never loosens;
  - a new stop applies from the next bar.
  - The settings 3 × ATR, 2R and 14 bars were chosen before the test; no alternatives were tried.
- **B-protected (Runner exit off):** B's take-profit of 1.5 noise units from the fill.
- **Flat by 15:55 New York**, or 5 minutes before an earlier session end (from NinjaTrader's session iterator). No
  entry after that time.

**Account (evaluation profile: $3,000 target, $2,000 intraday trail, 30 calendar days):**
- Highest equity: closed plus open P/L at each completed bar's best price, from the evaluation start.
  - Live, it is remembered in `Documents\NinjaTrader 8\MnqNoiseMomentum\runner-account-<account>.txt` with the pass
    and today's losers, so a restart keeps them.
  - The threshold Apex shows can be entered as a floor.
- Liquidation line = highest equity − $2,000. Reserve line = liquidation line + $300.
- If an open position's stop would let equity fall below the reserve line, the stop moves up to the reserve line's
  price, or the position is closed at market if the price is already past it.
- No entry after 2 losing positions in a day. Positions are counted once each, however many fills they had.
- Once realized profit reaches the target, everything is closed and the strategy stops for good. The take-profit
  sits at $3,025 realized, a $25 margin.
- **Our own controls, not Apex's.** Apex's current evaluation has no daily loss limit and no minimum days. All these
  limits are planned: a gap or a failed order can exceed them.

**Orders:**
- A rejected order while in a position closes the position at market, sent again at each bar until flat.
- A rejected entry leaves no position.
- Every signal not taken prints its time and reason to the Output.

## 2. Tests (`tests/test_runner.py`, stand-in) - executed

All of these pass:
- With every new limit off, the candidate makes B's trades exactly: the same trades, fills and P/L.
  - Synthetic bars in the tests.
  - The user's MNQ bars at 0, 1 and 2 ticks: 98 / 97 / 97 trades, identical to the cent.
- **Sizing:** the contracts equal the formula's for every entry; a $20 budget skips every signal where one contract
  doesn't fit.
- **The trail**, against an independent ATR computation:
  - the stops are unchanged until 2R;
  - from then on, each stop is the tighter of the untrailed stop and the best trail so far;
  - no stop ever loosens.
- **Flat time:** by 15:55, and by 12:55 on a 13:00 early close.
- **Daily limits:** no entry after 2 losing positions, including positions filled in two parts; each entry's planned
  risk fits within the $400 backstop.
- **Target:** the strategy stops at the evaluation target.
- **Reserve:** stops tighten or the position closes when an outside balance drop threatens the reserve; entries stop
  when the room is gone.
- **Orders and restarts:**
  - a rejected stop closes the position, and a rejected close is sent again;
  - a rejected entry leaves no position;
  - a remembered pass, a remembered peak, and an entered threshold all survive a restart.
- **Entries:** every entry is one of B's.
- **Setup:** anything but a 1-minute chart is refused.
