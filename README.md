# MNQ Liquidity Sweep Bot

A rules-based MNQ day-trading strategy with prop-firm risk rails. Every piece below implements exactly the same rules:

| Piece | What it's for |
|---|---|
| **`pine/mnq_noise_momentum.pine`** | **The one strategy here with a tested edge (16 years).** Noise-area momentum from a 2024 paper: BUY/SELL/EXIT alerts every half hour, flat at 16:00. Rules in [`docs/NOISE.md`](docs/NOISE.md). On a $25K / $1,500 evaluation it still failed more often than it passed. |
| `pine/mnq_liquidity_sweep_all_in_one.pine` | The original sweep/breakout bot in one TradingView script (no edge on real data, see below): BUY/SELL signals with size, limit price, stop and target, phone alerts, a dashboard, and a Strategy Tester backtest with optional prop-evaluation simulation. |
| `pine/mnq_liquidity_sweep_signals.pine` | **TradingView indicator that tells you when to BUY or SELL.** It gives the limit price, stop, target and size, then alerts you to fill, move to breakeven, cancel, or flatten. |
| `pine/mnq_liquidity_sweep_bot.pine` | TradingView strategy with the same rules, for backtesting in Strategy Tester with prop-evaluation simulation. |
| `mnqbot/` (Python) | A stricter backtester with worst-case fills, back-to-back evaluation simulation, Monte Carlo pass odds, and a buy-and-hold MNQ benchmark. |
| [`docs/RULES.md`](docs/RULES.md) | **Every rule written out exactly**, with a worked example and what to do for each alert. |
| [`docs/RESULTS.md`](docs/RESULTS.md) | **The multi-year test on real Nasdaq-100 data, and its verdict: no edge.** |

## Read this first

**No bot never loses.** Anything sold as one is a scam or a backtest that peeked at the future. Every real edge has losing trades, losing days and losing weeks. This bot is built to **lose small, stop when the day goes wrong, and never let one trade end the account.** On a prop evaluation, that matters more than win rate.

**Beating buy-and-hold MNQ is not guaranteed either.** The backtester reports it as a plain YES/NO, so you can check instead of trusting.

**The original sweep/breakout bot has no edge.** On 3¾ years of Nasdaq-100 1-minute data (Jan 2023 → Sep 2026), tuned on 2023–2024 and then run once on 2025–2026, it lost money after costs. Even with zero costs it sits near break-even. **Don't pay for a prop evaluation to trade those rules.**

**Noise-area momentum is the one strategy that held up.** It was tested on 16 years (Nov 2010 → Sep 2026), was positive in 14 of 16 years, and had a t-stat of 3.5 at today's costs. But it wins only 38% of trades, depends on a few big trend days, is down $3,155 so far in 2026 on 1 MNQ, and on a $25K / $1,500 evaluation passed only about 4 in 10 historical starts. Forward-test it on alerts before you pay for anything. Full numbers are in [docs/RESULTS.md](docs/RESULTS.md).

## The strategy in plain English

1. **Mark the obvious liquidity.** These are the previous day's regular-hours high and low, the overnight high and low, and the latest swing high and low. Stop orders pile up just beyond these levels.
2. **Wait for a sweep.** Between 9:35 and 11:30 New York time, price trades through one of those levels by at least 2 ticks, then closes back on the other side. The stops got run, and the move failed.
3. **Require displacement.** Within 12 bars, a strong candle the other way (body ≥ 1× ATR) leaves a **fair value gap**: a three-candle hole price skipped through.
4. **Enter on the retrace.** A limit order goes at the middle of the gap, with the stop 4 ticks beyond the sweep's extreme and the target at 2R. If it doesn't fill within 6 bars, or price reaches the target first, the order is cancelled.
5. **Manage it.** The stop moves to breakeven at +1R, and everything is flat by 15:50.

**Second setup: opening range breakout.** The opening range is the high and low of the first 5 minutes after 9:30. The first candle in the entry window that closes outside it gives a limit order back at the broken edge (the retest). The stop goes at the middle of the range and the target at 2R, with one breakout per day. It fires far more often than the sweep, with stops a $150 risk can usually cover. **Trade these setups** picks both (default), sweep only, or breakout only.

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

**The easy way: one script.** Paste `pine/mnq_liquidity_sweep_all_in_one.pine` into Pine Editor, then click **Save** and **Add to chart**.

- It draws the levels, BUY/SELL labels and every fill, breakeven, cancel and exit.
- It runs the backtest in **Strategy Tester** and shows a dashboard.
- Under **Mode → Account mode**, choose how it sizes trades:
  - **Live: my real account** (default): uses **Your room to the drawdown line $**, which you update every morning.
  - **Backtest a prop evaluation**: simulates back-to-back evaluations using the **Prop firm** settings.
- **Alerts:** Condition *MNQ Liquidity Sweep All-in-One* → **alert() function calls only**.
- The dashboard's **Setup funnel** counts, over the loaded history, how many sweeps the bot saw and how many became setups, signals and fills. It also shows where the rest dropped out (stop too wide or tight, daily limits, can't size, never filled) and the typical stop size. The Python report prints the same funnel, and the tests hold the two to identical numbers.

The separate indicator and strategy below do the same jobs split in two.

1. On tradingview.com, open an **MNQ1!** chart on **5 minutes**, with **extended trading hours ON**. The overnight levels need overnight bars, and the defaults are tuned for 5 minutes.
2. **Signals:** open **Pine Editor**, paste the whole of `pine/mnq_liquidity_sweep_signals.pine`, click **Save**, then **Add to chart**.
   - The indicator draws the levels, BUY/SELL labels with the limit price, stop, target and size, and every fill, breakeven, cancel and exit. It also shows a dashboard.
   - In its settings, set **Your room to the drawdown line $** every morning: your balance minus your firm's liquidation balance.
3. **Backtest:** do the same with `pine/mnq_liquidity_sweep_bot.pine`, then open **Strategy Tester** and read the results honestly (see below). Set your firm's actual rules under **Prop firm**, since rules change. The strategy's dashboard shows how many back-to-back evaluations would have passed or failed.
4. **Phone alerts:** on the indicator, click Alert (⏰) → Condition: *MNQ Liquidity Sweep Signals* → **Any alert() function call** → turn on *Notify in app* → Create. Each signal arrives as a ready-to-place bracket. This is the exact alert for the worked example in the rulebook:

   ```
   MNQ SELL signal (swept ONH 20010.00)
   SELL LIMIT 4 @ 19998.00
   STOP 20015.00 | TARGET 19964.00
   Risk $142.96 | cancel if not filled within 6 bars (30 min)
   ```

   You place that bracket in Tradovate yourself. Follow-up alerts tell you when it filled, when to move the stop to breakeven, when to cancel, and when to flatten. [RULES.md §10](docs/RULES.md#10-alerts-and-exactly-what-to-do) says exactly what to do for each one.

On high-impact news days (FOMC, CPI, NFP), tick **Do NOT trade today** or set a **News blackout** window.

### Automation and prop firms

**Check your firm's rules before automating anything.** Third-party summaries of Take Profit Trader's policy conflict, and most say it bans bots and automated order entry, including TradingView alerts routed into the account ([proptradingvibes](https://proptradingvibes.com/blog/takeprofittrader-copy-trading-rules), [tradingfinder](https://tradingfinder.com/props/take-profit-trader/), [PickMyTrade FAQ](https://pickmytrade.io/prop-firm-faq/take-profit-trader/), [TradersPost](https://blog.traderspost.io/article/automate-take-profit-trader-with-traderspost)). Breaking that rule can void an account that passed. That's why the default alert mode is **Phone (I place the trade)**.

The script can send **TradersPost JSON** (`Alert format` setting) for a personal account that permits automation. Paper-trade it first.

---

## Python backtester

```bash
pip install -e ".[dev]"            # pandas, numpy, pytest
python -m pytest                   # all tests (first run ~3 min: parses the .pine files)
python -m mnqbot config > my.json  # all settings, edit as you like
```

### Get data

- **TradingView export** (best match to what you trade): from an MNQ1! chart with extended hours on, open the chart menu → *Export chart data…*, if your plan includes it.
- **Yahoo Finance** (quick look, about 60 days of 5-minute bars): `pip install yfinance`, then `python -m mnqbot fetch --out data/mnq_5m.csv`.
- **HistData.com** (free, years of 1-minute `NSXUSD` bars, the Nasdaq-100 cash index): its files are semicolon-separated with no header, so run them through `research/nsx_study.py` (see [RESULTS.md](docs/RESULTS.md#reproduce)). The free files have some missing minutes, mostly in 2023.
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

### How the TradingView scripts are checked

TradingView can't be run here, so `tests/pine_interpreter.py` runs the **actual `.pine` files** bar by bar. It is a strict interpreter for the part of Pine v6 these scripts use, with a broker emulator that applies the same worst-case fill rules. `tests/test_pine_parity.py` then requires all three scripts to produce the same orders, fills, exits and P/L as the Python engine, to the cent. For the all-in-one script, that covers both account modes, plus exit reasons, exit labels and alert text. It holds on 120 sessions of test data and on 25 hand-built cases (17 sweep, 8 breakout) that sit exactly on every fill boundary. The evaluation pass/fail counts must match too.

`tests/test_noise.py` holds the noise-momentum script to `mnqbot/noise.py` the same way: same trades, alerts and noise lines, to the cent. That covers hand-built cases (including a half day and a session missing a check), 90 random sessions on 5- and 15-minute bars, and an RTH-only chart.

`python tests/mutation_check.py` plants 22 realistic bugs in the indicator, the all-in-one script and the noise-momentum script (a fill on touch, an off-by-one expiry, target before stop, a mislabeled exit, a wrong noise line, a missing reversal, and so on) and confirms the tests catch every one. The first test run parses the scripts, which takes about 2 minutes, and caches them. Skip those tests with `pytest -m "not slow"`.

---

## Is it any good?

**For the sweep/breakout rules, no.** They fail rules 2 and 3 below on 3¾ years of real data. **Noise-area momentum** passed a 16-year test at today's costs, but it fails most $25K evaluations. See [docs/RESULTS.md](docs/RESULTS.md).

Decide with data, not hope. The rules of thumb:

1. **At least 100 trades** before you believe any number. 20 trades is noise.
2. **Profit factor above about 1.3 after costs**, and a positive expectancy in R.
3. **Out-of-sample.** Tune settings on one period (`--end`), then run once, untouched, on a later period (`--start`). If it falls apart, the tuning was curve-fitting.
4. **Don't over-tune.** If it only works at `displacement_atr = 1.15`, it doesn't work.
5. **Compare to buy-and-hold** and to the Monte Carlo pass rate. A 30% pass rate means 7 in 10 evaluation fees lost.
6. **Forward-test** with alerts only (no money) for 2–4 weeks. Then trade 1–2 micros, and size up only once live results match the backtest.

If it doesn't pass these, change the idea, not just the numbers, or don't trade it.

## Where TradingView and Python can differ

- **Indicator:** it uses the same worst-case fill rules as Python, and the parity tests hold it to identical trades. The one deliberate difference is that the room to your drawdown line is your input, not simulated.
- **Strategy:** fills come from TradingView's own simulator, which can order events inside a bar differently, so its Strategy Tester numbers can differ from Python's. On a drawdown breach, TradingView exits at the bar close; Python exits at the line price.
- The strategy's sizing uses fees and slippage hardcoded at the top of the script ($0.62, 1 tick). Keep them in sync if you change them in the strategy's Properties. The indicator has them as inputs.
- Python can't know news days unless you list them in `risk.no_trade_dates` / `risk.blackout_windows`.
- `strategy.orb_entry = "close"` (enter a breakout at the next bar's open instead of waiting for the retest) exists only in Python, for research. The TradingView scripts always use the retest entry.
- ATR needs about 100 bars to settle, so the first bars of a chart can differ slightly from a backtest that started earlier.

## Files

```
pine/mnq_noise_momentum.pine              TradingView: noise-area momentum, the strategy with a tested edge
docs/NOISE.md                             its exact rules, alerts and what to expect
mnqbot/noise.py                           its Python reference (the tests hold the script to it)
research/noise_eval.py                    its odds on a $25K evaluation
research/noise_tuning.py                  whether checking more often helps it (it doesn't)
research/noise_daily.py                   whether it can trade on most days (not safely)
research/discovery.py, discovery2.py      a search of the data for new patterns (none held up)
research/afternoon.py                     the one idea from that search, on unseen years (failed)
pine/mnq_liquidity_sweep_all_in_one.pine  TradingView: signals + alerts + dashboard + backtest in one
pine/mnq_liquidity_sweep_signals.pine     TradingView indicator: BUY/SELL signals, alerts, dashboard
pine/mnq_liquidity_sweep_bot.pine         TradingView strategy: same rules, Strategy Tester backtest
docs/RULES.md                             every rule, exactly, with a worked example
docs/RESULTS.md                           multi-year test on real Nasdaq-100 data: no edge
research/nsx_study.py                     the script that runs that test on HistData.com files
research/nsx_holes.py                     how the free data's missing minutes affect that test
research/published_lab.py                 three published intraday strategies, 2010-2026
mnqbot/config.py                          every setting, with defaults
mnqbot/strategy.py                        sweep -> displacement -> FVG setup, and opening range breakout
mnqbot/engine.py                          fills, sizing, daily rails, prop evaluation simulation
mnqbot/report.py                          metrics, benchmark, Monte Carlo
mnqbot/data.py                            CSV loading, sessions, ATR, optional Yahoo download
tests/pine_interpreter.py                 strict Pine v6 interpreter used to check the .pine files
tests/                                    unit tests, Pine-vs-Python parity tests, mutation check
```

*Not financial advice. Futures are leveraged and you can lose more than you expect. Past backtest results don't predict future results.*
