# MNQ Liquidity Sweep Bot

A rules-based MNQ day-trading strategy with prop-firm risk rails. It comes as two pieces that implement the same logic:

| Piece | What it's for |
|---|---|
| `pine/mnq_liquidity_sweep_bot.pine` | TradingView strategy: draws the levels, backtests in Strategy Tester, and sends trade alerts to your phone. |
| `mnqbot/` (Python) | A stricter backtester with pessimistic fills, back-to-back prop evaluation simulation, Monte Carlo pass odds, and a buy-and-hold MNQ benchmark. |

## Read this first

**No bot never loses.** Anything sold as one is a scam or a backtest that peeked at the future. Every real edge has losing trades, losing days and losing weeks. This bot is built to **lose small, stop when the day goes wrong, and never let one trade end the account.** On a prop evaluation, that matters more than win rate.

**Beating buy-and-hold MNQ is not guaranteed either.** The backtester reports it as a plain YES/NO, so you can check instead of trusting.

**This has not been tested on real market data yet.** It was built in an environment with no market-data access. The tests prove the machinery works (fills, sizing, rails, no look-ahead). They don't prove the strategy makes money. Run it on real data before you risk anything (see [Is it any good?](#is-it-any-good)).

## The strategy in plain English

1. **Mark the obvious liquidity.** These are the previous day's regular-hours high and low, the overnight high and low, and the latest swing high and low. Stop orders pile up just beyond these levels.
2. **Wait for a sweep.** Between 9:35 and 11:30 New York time, price trades through one of those levels by at least 2 ticks, then closes back on the other side. The stops got run, and the move failed.
3. **Require displacement.** Within 12 bars, a strong candle the other way (body ≥ 1× ATR) leaves a **fair value gap**: a three-candle hole price skipped through.
4. **Enter on the retrace.** A limit order goes at the middle of the gap, with the stop 4 ticks beyond the sweep's extreme and the target at 2R. If it doesn't fill within 6 bars, or price reaches the target first, the order is cancelled.
5. **Manage it.** The stop moves to breakeven at +1R, and everything is flat by 15:50.

## Risk rails (defaults sized for a $25K, $1,500-drawdown evaluation)

| Rail | Default | Why |
|---|---|---|
| Max risk per trade | **$150** incl. fees + slippage | 10% of the drawdown. Contracts are calculated from the stop distance, not picked by feel. |
| Daily max loss | **$300** | Two full losses and you're done. Later trades are also shrunk so they can't break the limit. |
| Daily profit lock | **$600** | Stays under a 50% consistency rule on a $1,500 target ($750). Stops you giving it back. |
| Max trades per day | **3** | Overtrading kills evaluations. |
| Drawdown room | **≤25% per trade** | Never risks more than a quarter of the distance to the trailing drawdown line. |
| Max contracts | **15 micros** | Half the 30-micro firm cap. |
| Stop size | **8–60 points** | Skips setups too tight to survive noise or too wide to size. |
| Flatten | **15:50 ET** | Most firms require you flat before the close. |

**Why this matters:** 10 MNQ is $20 per point. NQ can move 75 points in a few minutes on an ordinary day, and 75 points on 10 MNQ is a $1,500 loss: the entire drawdown. Size from the stop, not from how confident you feel.

All of these are inputs in the TradingView script and fields in the Python config.

---

## Use it in TradingView

You need a browser once to add the script. The TradingView phone app can run scripts but can't paste new ones.

1. On tradingview.com, open an **MNQ1!** chart on **5 minutes** (1–3 minutes also works), with **extended trading hours ON**. The overnight levels need overnight bars.
2. Open **Pine Editor**, paste the whole of `pine/mnq_liquidity_sweep_bot.pine`, click **Save**, then **Add to chart**.
3. Open **Strategy Tester** and read the results honestly (see below). The dashboard in the top-right corner shows today's status, the room left to the drawdown line, and how many back-to-back evaluations the backtest would have passed or failed.
4. Set your firm's actual rules in the script settings under **Prop firm**. Rules change, so check them on the firm's site.
5. **Phone alerts:** click Alert (⏰) → Condition: *MNQ Liquidity Sweep Bot* → **alert() function calls only** → turn on *Notify in app* → Create. Each setup arrives as a ready-to-place bracket, like this:

   ```
   MNQ SHORT setup (swept ONH 31210.00)
   SELL LIMIT 3 @ 31198.00
   STOP 31215.00 | TARGET 31164.00
   Risk ~$107 | cancel if not filled in 6 bars
   ```

   You place that bracket in Tradovate yourself. Follow-up alerts tell you when it fills, when to move the stop to breakeven, when to cancel, and when to flatten.

On high-impact news days (FOMC, CPI, NFP), tick **Do NOT trade today** or set a **News blackout** window.

### Automation and prop firms

**Check your firm's rules before automating anything.** Third-party summaries of Take Profit Trader's policy conflict, and most say it bans bots and automated order entry, including TradingView alerts routed into the account ([proptradingvibes](https://proptradingvibes.com/blog/takeprofittrader-copy-trading-rules), [tradingfinder](https://tradingfinder.com/props/take-profit-trader/), [PickMyTrade FAQ](https://pickmytrade.io/prop-firm-faq/take-profit-trader/), [TradersPost](https://blog.traderspost.io/article/automate-take-profit-trader-with-traderspost)). Breaking that rule can void an account that passed. That's why the default alert mode is **Phone (I place the trade)**.

The script can send **TradersPost JSON** (`Alert format` setting) for a personal account that permits automation. Paper-trade it first.

---

## Python backtester

```bash
pip install -e ".[dev]"            # pandas, numpy, pytest
python -m pytest                   # 33 tests
python -m mnqbot config > my.json  # all settings, edit as you like
```

### Get data

- **TradingView export** (best match to what you trade): from an MNQ1! chart with extended hours on, open the chart menu → *Export chart data…*, if your plan includes it.
- **Yahoo Finance** (quick look, about 60 days of 5-minute bars): `pip install yfinance`, then `python -m mnqbot fetch --out data/mnq_5m.csv`.
- Any comma-separated CSV with a header, a time column (unix or ISO) or Date+Time columns, plus open/high/low/close, also works.

### Run it

```bash
python -m mnqbot backtest data/mnq_5m.csv                      # full report + CSVs in results/
python -m mnqbot backtest data/mnq_1m.csv --resample 5min      # aggregate 1m first
python -m mnqbot backtest data.csv --config my.json --start 2026-01-01 --end 2026-07-01
python -m mnqbot setups data.csv                               # every setup, ignoring risk rails
```

The report shows win rate, profit factor, expectancy in dollars and R, max drawdown, best and worst days, and buy-and-hold 1 MNQ over the same period. It also shows how many **back-to-back prop evaluations** would have passed or failed on that data, plus a **Monte Carlo** pass/fail rate from reshuffling the days. `results/` gets `trades.csv`, `daily.csv`, `equity.csv` and `summary.json`.

### How the backtester stays honest

- Limit entries and targets fill only if price trades **through** them by a tick, never just a touch.
- Stops fill with a tick of slippage, or at the open if price gaps past them.
- If a bar touches both the stop and the target, it counts as **the stop**.
- No target is credited on the bar the entry fills, and breakeven moves wait for the next bar.
- Every decision uses closed bars only. A test cuts the data at random points and checks earlier trades don't change (`test_no_lookahead`).
- Fees default to $0.62 per contract per side. Change them in `costs`.
- Evaluations: the end-of-day trailing drawdown stops trailing at the starting balance, and touching the line intraday fails the account. Passing needs the target, a minimum number of trading days, and the consistency rule. An account stuck so close to the line that it can't size a trade counts as failed, because you'd be paying for a reset.

---

## Is it any good?

Decide with data, not hope. The rules of thumb:

1. **At least 100 trades** before you believe any number. 20 trades is noise.
2. **Profit factor above about 1.3 after costs**, and a positive expectancy in R.
3. **Out-of-sample.** Tune settings on one period (`--end`), then run once, untouched, on a later period (`--start`). If it falls apart, the tuning was curve-fitting.
4. **Don't over-tune.** If it only works at `displacement_atr = 1.15`, it doesn't work.
5. **Compare to buy-and-hold** and to the Monte Carlo pass rate. A 30% pass rate means 7 in 10 evaluation fees lost.
6. **Forward-test** with alerts only (no money) for 2–4 weeks. Then trade 1–2 micros, and size up only once live results match the backtest.

If it doesn't pass these, change the idea, not just the numbers, or don't trade it.

## Where TradingView and Python can differ

- TradingView may resolve some intrabar orderings differently from the Python worst-case rule.
- On a drawdown breach, TradingView exits at the bar close. Python exits at the drawdown line.
- Swing-level confirmation and level tie-breaking match by construction. Commission and slippage are hardcoded at the top of the Pine script for sizing, so keep them in sync if you change them in the strategy properties.
- Python can't know news days unless you list them in `risk.no_trade_dates` / `risk.blackout_windows`.

## Files

```
pine/mnq_liquidity_sweep_bot.pine   TradingView strategy + alerts + dashboard
mnqbot/config.py                    every setting, with defaults
mnqbot/strategy.py                  levels -> sweep -> displacement -> FVG setup
mnqbot/engine.py                    fills, sizing, daily rails, prop evaluation simulation
mnqbot/report.py                    metrics, benchmark, Monte Carlo
mnqbot/data.py                      CSV loading, sessions, ATR, optional Yahoo download
tests/                              33 tests
```

*Not financial advice. Futures are leveraged and you can lose more than you expect. Past backtest results don't predict future results.*
