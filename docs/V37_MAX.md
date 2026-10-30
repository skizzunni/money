# v3.7: v3.6 sized for the most profit inside the user's limits (pre-registration)

Written and committed on 2026-10-30, before the scan in this file was run.

**The goal:** the most net profit v3.6 can make on a 100K account, inside:
- a **$2,000 end-of-day trailing drawdown** that stops at the starting balance;
- a **$1,000 daily loss limit**, with no stop-trading rule.

**What stays fixed:** v3.6's entry, stop, lock, take-profit, filters and session rules are unchanged. Only sizing is
scanned:
- `profit_step`: one more MNQ for each this many dollars of closed profit. Values: 500, 750, 1,000, 1,500, 2,000.
- `size_up_to`: the most MNQ. Values: 5, 10, 15, 20, 30.

That makes 25 settings, each starting at 1 MNQ.

**Selection** (on the histories only, 5-minute bars):
- A setting qualifies if the $2,000 floor is never touched (`tb0` = 0) on both NQ 2015-2025 and the Nasdaq-100 index
  2011-2026.
- Of those, the one with the highest of the smaller of the two histories' net per year.
- The user's window (the Jan 2025 – Oct 2026 stand-in, 5- and 30-minute bars) is not used to choose. It is reported
  once, afterwards.

**Reported:** net, closed drawdown, end-of-day drawdown, winners, PF, worst day and floor touches, for every set.

**Targets:** the user's targets (net at least $75,000, at least 80% winners, PF at least 2, drawdown under $4,000)
are reported as measured. v3.6's entries win about 55-65% of trades, so the win-rate target is not expected to be
met by any sizing.
