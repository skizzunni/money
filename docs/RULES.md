# MNQ Liquidity Sweep: the exact rules

These rules are implemented identically in four places:

- **All-in-one (start here):** [`pine/mnq_liquidity_sweep_all_in_one.pine`](../pine/mnq_liquidity_sweep_all_in_one.pine). It covers signals, alerts, the dashboard and the backtest.
- **Signals indicator:** [`pine/mnq_liquidity_sweep_signals.pine`](../pine/mnq_liquidity_sweep_signals.pine)
- **Backtest strategy:** [`pine/mnq_liquidity_sweep_bot.pine`](../pine/mnq_liquidity_sweep_bot.pine)
- **Python backtester:** [`mnqbot/`](../mnqbot)

Same bars in, same signals out. Every number below is a default and can be changed in settings.

---

## 1. Units and time

| Item | Value |
|---|---|
| Instrument | MNQ. 1 tick = 0.25 points = $0.50 per contract. 1 point = $2.00 per contract. |
| Chart | MNQ1!, **5-minute**, **extended hours ON** |
| Clock | New York time (ET). A bar is named by its **open** time: the "09:35 bar" runs 09:35–09:40. |
| Trading day | Starts **18:00 ET**. The 18:00 bar on Monday evening belongs to Tuesday. |
| Regular hours (RTH) | Bars **09:30 to 15:55** (open time ≥ 09:30 and < 16:00) |
| Overnight | Bars from 18:00 to 09:25 of the same trading day |
| **Entry window** | Bars **09:35 to 11:25** (open time ≥ 09:35 and < 11:30) |
| **Flatten time** | Bars with open time ≥ **15:50** |
| Rounding | To the nearest 0.25. An exact half tick rounds **up**. |
| ATR | 14-period Wilder ATR (TradingView `ta.atr(14)`) |

Everything is decided at the **close** of a bar. On the bar that is still forming, labels are provisional and can appear and disappear. Alerts fire only at bar close.

---

## 2. Liquidity levels

Up to six levels are active each trading day.

| Level | Definition | Active from |
|---|---|---|
| **PDH / PDL** | Highest high / lowest low of the previous trading day's RTH bars. If that day had none, the last day that did. | First bar of the trading day (18:00) |
| **ONH / ONL** | Highest high / lowest low of this trading day's overnight bars | The 09:30 bar |
| **SWH** | The newest bar whose high is **higher than** each of the 5 bars before it and **at least as high as** each of the 5 bars after it. All 11 bars must be in today's trading day. | The bar after it is confirmed (6 bars after the swing bar) |
| **SWL** | Mirror of SWH, using lows | Same |

A new swing replaces the old one of the same type.

**Taken:** a high level (PDH, ONH, SWH) is taken the first time any bar's **high ≥ level + 2 ticks**. A low level (PDL, ONL, SWL) is taken when any bar's **low ≤ level − 2 ticks**. This counts at any time of day, inside or outside the window. A taken level is ignored for the rest of the day.

---

## 3. Sweep

A **sell-side setup starts** when a bar inside the entry window takes one or more high levels **and closes below** at least one of them. That bar is the sweep bar.

- **L** (the swept level) = the highest of the levels it took and closed below.
- **X** (the extreme) = the sweep bar's high.

A **buy-side setup starts** the same way in mirror: the bar takes low levels and closes above. L = the lowest such level, and X = the sweep bar's low.

- If one bar qualifies both ways, neither counts.
- A newer sweep replaces one that is still waiting.

**While waiting** (each later bar, checked before looking for new sweeps on that bar):

1. If more than 12 bars have passed since the sweep bar, stop waiting. No trade.
2. Update X to the highest high (sell side) or lowest low (buy side) since the sweep bar, including this bar.
3. If this bar **closes back beyond L** (above L for sell side, below L for buy side), stop waiting. That was a breakout, not a sweep.

---

## 4. Setup (displacement + fair value gap)

Checked on bar **B**, which must be inside the entry window. **A** = the bar before B (the displacement candle), **Z** = the bar before A. A must be the sweep bar or later.

| | Sell setup | Buy setup |
|---|---|---|
| Displacement | A is bearish: **open − close ≥ 1.0 × ATR** of bar A | A is bullish: **close − open ≥ 1.0 × ATR** of bar A |
| Fair value gap (FVG) | **low(Z) − high(B) ≥ 4 ticks** (1 point) | **low(B) − high(Z) ≥ 4 ticks** |
| Gap | top = low(Z), bottom = high(B) | bottom = high(Z), top = low(B) |
| Still beyond the level | close(B) **<** L | close(B) **>** L |
| **Entry** (limit) | round(bottom + 0.5 × (top − bottom)) | round(top − 0.5 × (top − bottom)) |
| **Stop** | X + 4 ticks | X − 4 ticks |
| **Risk R** (points) | Stop − Entry | Entry − Stop |
| **Target** | round(Entry − 2 × R) | round(Entry + 2 × R) |

- The setup is **valid only if 8 ≤ R ≤ 60 points**.
- Once the four conditions above are met, the sweep stops waiting, whether R was valid or not.
- Entry is always on the correct side of the market: above it for a sell limit, below it for a buy limit.

---

## 5. Should the signal be taken? (risk rails)

These checks run in this order at the close of bar B. The first one that applies blocks the signal.

1. A position or a working order already exists.
2. *(Strategy only)* The simulated account hit its drawdown line today.
3. "Do NOT trade today" is ticked. This applies to today only, not to past days. In Python, it's the dates in `risk.no_trade_dates`.
4. The daily news blackout is on and B is inside it (default 09:55–10:05 when enabled). In Python, it's `risk.blackout_windows`, which is off by default.
5. B's open time is ≥ 15:50.
6. **3 trades** have already filled today.
7. Today's realized P/L is **≤ −$300**.
8. Today's realized P/L is **≥ +$600**.
9. *(Strategy only)* The evaluation would pass at today's close: target reached, enough days, and consistency OK.

---

## 6. Position size

```
risk per contract = R × $2 + 2 × $0.62 fees + 1 tick slippage ($0.50)
budget            = the smallest of:
                      $150
                      $300 + today's realized P/L
                      25% × room to your drawdown line
contracts         = floor(budget ÷ risk per contract), capped at 15
```

If contracts = 0, there is no signal.

**Room to your drawdown line** is your account balance minus the balance where your firm liquidates you:

- **Indicator, and the all-in-one in *Live: my real account* mode:** enter it in settings and update it every morning. The default is $1,500.
- **Strategy, the all-in-one in *Backtest a prop evaluation* mode, and Python:** simulated (see §9).

The firm's own cap (30 micros) also applies in the strategy and Python.

---

## 7. Order handling

| Event | Exact rule (sell shown; buy is the mirror) |
|---|---|
| Place | A sell limit at Entry, at the close of B. It is live from the bar after B. |
| Fill | A bar's **high ≥ Entry + 1 tick**. Touching Entry is not enough. The fill price is Entry. |
| Can fill on | Bars B+1 to B+6 |
| Cancel: missed | Not filled, and a bar's **low ≤ Target**. The move happened without you. |
| Cancel: expired | Not filled by the close of bar B+6 |
| Cancel: late | A bar opens at ≥ 15:50 before the order filled (checked before the fill check), or a new trading day starts |

---

## 8. Managing the trade

| Bar | Rule (short shown; long is the mirror) |
|---|---|
| Fill bar | **Only the stop counts.** If high ≥ Stop, exit at Stop + 1 tick. No target, no breakeven on this bar. |
| Later bars, in this order | 1. Open ≥ Stop: exit at the **open** + 1 tick (gap).<br>2. High ≥ Stop: exit at Stop + 1 tick.<br>3. Low ≤ Target − 1 tick: exit at **Target**. |
| Same bar hits stop and target | **The stop wins.** |
| Breakeven | On a bar after the fill bar with no exit: if low ≤ Entry − 1R, the stop moves to Entry from the next bar on. |
| Flatten | Still in at the close of a bar with open time ≥ 15:50: exit at that bar's close + 1 tick (long: − 1 tick). |
| Session ends early (holiday) | Exit at the last bar's close when the next trading day starts. |

```
P/L = direction × (exit − entry) × contracts × $2 − 2 × $0.62 × contracts
      (direction = +1 long, −1 short)
```

---

## 9. Evaluation simulation (strategy, all-in-one in backtest mode, and Python)

Defaults are for a $25K evaluation with a $1,500 drawdown. **Check your firm's current rules.**

- **Drawdown line** = min(highest end-of-day balance − $1,500, starting balance $25,000). It stops trailing at the starting balance.
- **Fail** if equity touches the line at any bar's worst price, counting an open position at the bar's high (short) or low (long). The position is closed and trading stops for the day. Python exits at the line price; the TradingView strategy exits at the bar close.
- **Pass** at a day's close when profit ≥ $1,500, there are ≥ 5 days with trades, and the best day is < 50% of profit.
- **Stalled = fail** (you'd be paying for a reset). This happens at a day's close if room < $70.96, which is one contract at the minimum 8-point stop ÷ 25%. It also happens after 3 setups in a row are skipped because the room was too small.
- After a pass or a fail, a fresh $25K attempt starts the next trading day.

---

## 10. Alerts, and exactly what to do

**To set up:** create an alert on the chart and turn on app notifications. For Condition, choose:

- **MNQ Liquidity Sweep All-in-One → alert() function calls only**, or
- **MNQ Liquidity Sweep Signals → Any alert() function call**

The messages are the same in both scripts.

A signal alert looks exactly like this:

```
MNQ SELL signal (swept ONH 20010.00)
SELL LIMIT 4 @ 19998.00
STOP 20015.00 | TARGET 19964.00
Risk $142.96 | cancel if not filled within 6 bars (30 min)
```

| Alert text | What you do in Tradovate |
|---|---|
| `SELL LIMIT 4 @ 19998.00` / `STOP 20015.00 \| TARGET 19964.00` | Place a **sell limit**, 4 contracts at 19998.00, with an attached bracket: stop-loss at 20015.00 and take-profit at 19964.00. |
| `BUY LIMIT …` | Same, buy side. |
| `FILLED SHORT 4 MNQ @ 19998.00` | Confirm your order filled and the bracket is live. |
| `MOVE STOP TO BREAKEVEN 19998.00` | Move your stop to 19998.00. |
| `CANCEL the unfilled MNQ limit order` | Cancel the entry order and its bracket. |
| `EXITED at TARGET / STOP / BREAKEVEN $x` | Information only. Your bracket should already have done this, so confirm you're flat. |
| `FLATTEN NOW (end of session) $x` | Close at market and cancel all working orders. |

**Never:**

- take a trade the indicator didn't signal
- move a stop farther away
- add contracts
- keep trading after a `DONE` status

If you miss an alert by more than a bar, skip the trade.

---

## 11. Worked example

The numbers below are checked by `tests/test_strategy.py`.

| Bar (ET) | O / H / L / C | What happens |
|---|---|---|
| overnight | high 20010.00 | **ONH = 20010.00** |
| 09:35 | 20002 / **20014** / 20001 / **20006** | Takes ONH (20014 ≥ 20010.50) and closes below it, so a **sell-side sweep**. L = 20010, X = 20014. |
| 09:40 | **20006** / 20007 / 19992 / **19991** | Displacement: body 15.00 ≥ 1.0 × ATR (7.70) |
| 09:45 | 19991 / **19995** / 19991 / 19993 | FVG: low(09:35) 20001 − high(09:45) 19995 = 6.00 ≥ 1.00. Close 19993 < 20010. **SELL signal.** |
| | | Entry = round(19995 + 0.5 × 6) = **19998.00**. Stop = 20014 + 1.00 = **20015.00**. R = 17.00. Target = 19998 − 34 = **19964.00** |
| | | Risk per contract = 17 × 2 + 1.24 + 0.50 = $35.74. Contracts = floor(150 ÷ 35.74) = **4** (risk $142.96) |
| 09:50 | 19993 / **19999** / 19992 / 19996 | 19999 ≥ 19998.25, so **filled** at 19998.00 |
| 09:55 | 19996 / 19997 / **19978** / 19980 | 19978 ≤ 19998 − 17 = 19981, so **stop to breakeven** (19998.00) |
| 10:00 | 19980 / 19982 / **19960** / 19962 | 19960 ≤ 19963.75, so **target** at 19964.00 |
| | | P/L = 34 × 4 × $2 − 4 × $1.24 = **+$267.04** (+1.87R) |

Now suppose the 09:55 bar's low had been 19985 instead, so there is no breakeven. Then if the 10:00 bar traded both 20016 and 19960, the **stop wins**: exit at 20015.25 = **−$142.96** (exactly −1R).

---

## 12. All settings

| Setting | Default | | Setting | Default |
|---|---|---|---|---|
| Entry window | 09:35–11:30 | | Max $ risk per trade | 150 |
| Flatten at | 15:50 | | Max contracts | 15 |
| Levels | PDH/PDL, ONH/ONL, swings | | Daily max loss | 300 |
| Swing length | 5 bars each side | | Daily profit lock | 600 |
| Sweep through | 2 ticks | | Max trades per day | 3 |
| Displacement within | 12 bars | | Share of drawdown room per trade | 25% |
| ATR length | 14 | | Room to drawdown line (indicator) | 1,500 |
| Displacement body | ≥ 1.0 × ATR | | Fees per contract per side | 0.62 |
| Min FVG | 4 ticks | | Slippage (stops, market) | 1 tick |
| Entry inside gap | 0.5 (middle) | | Limit fills need | 1 tick through |
| Stop buffer | 4 ticks | | Eval target / drawdown | 1,500 / 1,500 (EOD trailing) |
| Reward : risk | 2.0 | | Eval min days / consistency | 5 / best day < 50% |
| Stop size allowed | 8–60 points | | Firm max contracts | 30 |
| Order expires after | 6 bars | | Breakeven at | 1.0 R |

---

## 13. What is and isn't verified

**Verified by the tests (`python -m pytest`):**

- The real `.pine` source files are run through a strict Pine interpreter (`tests/pine_interpreter.py`). All three scripts produce **the same orders, fills, exits and P/L as the Python engine, to the cent**, on 120 sessions of test data and 17 hand-built boundary cases. The all-in-one is checked in both account modes, including exit reasons, labels and alert text.
- The strategy and the all-in-one in backtest mode also match Python's evaluation pass/fail counts.
- 11 deliberately planted bugs were each caught by these tests. Rerun that check with `python tests/mutation_check.py`.

**Not verified, so check these yourself:**

1. **Compiling inside TradingView.** It wasn't reachable from here. The interpreter enforces Pine v6's main rules, but if TradingView shows an error, send me the line.
2. **The TradingView strategies' fills.** The strategy and all-in-one Strategy Tester numbers come from TradingView's own simulator, which can order events inside a bar differently. The indicator and Python always assume the worst case.
3. **Whether it makes money on real MNQ data.** No rule set wins every trade. Backtest it (README → "Is it any good?") before risking money.
4. **Your firm's rules.** They change, and most firms ban automated order entry.
