// MNQ Momentum Runner (candidate, docs/RUNNER.md): B's momentum entries with risk-budget sizing, account protection for
// the $50K intraday-trailing evaluation, and (optionally) a volatility-trailing runner exit in place of B's take-profit.
//
// Entries: exactly B's (AddOns/MnqNoiseEngine.cs, unchanged): the noise band, its 14-session warm-up, the half-hour
// checks 10:00-15:30 New York, both directions, B's skip and Fed dates and its 3-loser model limit. One position at a
// time, taken from the strategy's own executions (NinjaTrader's Position: quantity and average fill).
//
// Sizing, before each entry:
//   stop distance = B's protective stop (the closer of the noise-line stop and 25 points), whole ticks
//   risk per contract = stop distance x $2 + 2 x commission + a reserve of 2 ticks at entry and 2 at the stop
//     (= 2 x points + $3.90 at $0.95 a side)
//   contracts = floor(budget / risk per contract), at most 4; none fits: no trade
//   budget = the smallest of $200, half the room above the account's reserve, and what is left of today's $400
//     loss backstop
// Exits (both versions): B's protective stop from the fill (the noise line and the 25-point cap), its lock (at +25
// points the stop goes to entry + 2.5), the stop only ever tightens; flat by 15:55 New York (5 minutes before an
// earlier session end); the evaluation target as a take-profit; the account reserve below.
//   RunnerExit off ("B-protected"): B's take-profit, 1.5 noise units from the fill.
//   RunnerExit on ("runner"): no take-profit of its own; once the best price since the entry is 2R past it (R = the
//     entry to the initial stop, fixed for the position), a trail 3 x ATR(14) of completed 5-minute bars behind the
//     best price; the tighter of it and B's stop.
// Account (evaluation profile: $3,000 target, $2,000 intraday trail of the highest equity, unrealized included):
//   threshold = highest equity - $2,000; reserve line = threshold + $300; no entry once the budget is under one
//   contract's risk; a position's stop is never below the reserve line's price (closed at market if already past);
//   no entry after 2 losing positions today, or whose planned risk could take today below -$400; once realized profit
//   reaches the target, everything is closed and the strategy stops.
// Orders: a rejected order while in a position closes it at market, sent again at every bar until flat. Live, the
// highest equity, the pass and today's losers are kept in a file (restarts), and the threshold Apex shows can be entered.
// These are planned limits: a gap or a failed order can exceed them.
// Written in C# 5 for NinjaTrader 8's compiler.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.AddOns.MnqBot;
using NinjaTrader.NinjaScript.DrawingTools;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqMomentumRunner : Strategy
    {
        const string LongName = "Long", ShortName = "Short";
        const double CapPoints = 25.0;      // B's max loss per trade in points ($200 / 4 MNQ / $2)
        const double LockAtPoints = 25.0;   // B's lock: at 1 cap of profit ...
        const double LockPlusPoints = 2.5;  // ... the stop to entry + 2.5 points
        NoiseEngine engine;
        NoiseSettings settings;
        TimeZoneInfo newYork;
        SessionIterator sessions;
        bool badChart;
        double pv;

        // the position (from executions)
        double plannedStopPts = double.NaN;  // the stop distance the entry was sized with
        double rPts = double.NaN;            // R: entry fill to the initial stop, fixed for the position
        double bestPx = double.NaN;          // best price since the entry (completed bars)
        double lastStop = double.NaN;        // the stop so far: it only tightens
        bool locked, trailOn;
        bool mustClose;                      // an order was rejected: close at market, again at every bar until flat
        string lastExit = "";

        // 5-minute ATR(14), Wilder, from completed 5-minute bars of 09:30-16:00
        double atr = double.NaN, fiveH = double.NaN, fiveL = double.NaN, fiveC = double.NaN, prevFiveC = double.NaN;
        int fiveKey = -1, atrCount;
        double atrSum;

        // the account
        double peak = double.NaN;            // highest equity since the evaluation start (unrealized included)
        bool passed;
        DateTime evalStart = DateTime.MinValue;
        DateTime lastDay = DateTime.MinValue;
        double dayStartEq;
        int dayLosers;
        readonly Dictionary<string, bool> countedTrades = new Dictionary<string, bool>();
        string notSent = "";
        int entries, skipped;
        readonly Dictionary<string, int> skipWhy = new Dictionary<string, int>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqMomentumRunner";
                Description = "MNQ momentum (B's entries) with risk-budget sizing, evaluation account protection and an optional ATR runner exit.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.IgnoreAllErrors;
                TraceOrders = false;
                IsInstantiatedOnEachOptimizationIteration = true;

                PlaceOrders = true;
                RunnerExit = true;
                MaxRisk = 200;
                MaxContracts = 4;
                SizingCommission = 0.95;
                ReserveTicks = 4;
                TrailAtr = 3.0;
                TrailActivateR = 2.0;
                AtrBars = 14;
                TakeProfit = 1.5;
                EvalTarget = 3000;
                EvalTrail = 2000;
                AccountReserve = 300;
                DailyLossBackstop = 400;
                MaxLosingPositions = 2;
                FlatMinute = 955;      // 15:55 New York
                AccountStart = 50000;
                LiquidationThreshold = 0;
                EvaluationStart = "";
                AccountFromBroker = true;
                SkipDates = NoiseEngine.SkipDatesDefault;
                FedDates = NoiseEngine.FedDatesDefault;
                RememberAccount = true;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                badChart = BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1;
                pv = Instrument.MasterInstrument.PointValue;
                settings = new NoiseSettings();  // B's settings, so the signals are B's
                settings.Qty = 4;
                settings.Tick = TickSize;
                settings.PointValue = pv;
                settings.MaxLoss = 200;
                settings.TakeProfit = 1.5;
                settings.StopBuffer = 0.24;
                settings.LockAt = 1.0;
                settings.LockPlus = 2.5;
                settings.MaxLosers = 3;
                settings.TightenOnly = true;
                settings.Lookback = 14;
                settings.FedNoShorts = true;
                settings.SkipDates = SkipDates ?? "";
                settings.FedDates = FedDates ?? "";
                engine = new NoiseEngine(settings, 1);
                sessions = new SessionIterator(Bars);
                DateTime d0;
                if (DateTime.TryParseExact(EvaluationStart ?? "", "yyyy-MM-dd", CultureInfo.InvariantCulture,
                                           DateTimeStyles.None, out d0))
                    evalStart = d0;
                Print("MNQ runner settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", PlaceOrders " + PlaceOrders + ", RunnerExit " +
                      RunnerExit + ", MaxRisk " + MaxRisk + ", MaxContracts " + MaxContracts + ", trail " + TrailAtr + " x ATR(" +
                      AtrBars + ", 5 min) after " + TrailActivateR + "R, TakeProfit " + (RunnerExit ? "none" : TakeProfit.ToString()) +
                      ", target " + EvalTarget + ", trail " + EvalTrail + ", reserve " + AccountReserve + ", daily backstop " +
                      DailyLossBackstop + ", losers " + MaxLosingPositions + ", flat at " + NoiseEngine.Hhmm(FlatMinute) +
                      ", evaluation start " + (evalStart == DateTime.MinValue ? "(the first bar)" : evalStart.ToString("yyyy-MM-dd")));
            }
            else if (State == State.Realtime)
                LoadAccount();
            else if (State == State.Terminated && engine != null)
            {
                string s = "";
                foreach (KeyValuePair<string, int> kv in skipWhy)
                    s += (s.Length > 0 ? "; " : "") + kv.Key + " x" + kv.Value;
                Print("MNQ runner: " + entries + " entries; signals skipped " + skipped + (s.Length > 0 ? " (" + s + ")" : "") +
                      "; evaluation " + (passed ? "target reached" : "not passed") + "; highest equity " + F0(peak));
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        static string F0(double x) { return double.IsNaN(x) ? "-" : x.ToString("0.00", CultureInfo.InvariantCulture); }

        static DateTime TradingDay(DateTime ny) { return ny.AddHours(6).Date; }

        int Dir
        {
            get
            {
                if (Position.MarketPosition == MarketPosition.Long) return 1;
                if (Position.MarketPosition == MarketPosition.Short) return -1;
                return 0;
            }
        }

        DateTime ToNy(DateTime t)
        {
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            return TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), platform, newYork);
        }

        // ── Sizing (public for the tests through the dashboard line; the rule itself is in the header)
        double RiskPerContract(double stopPts)
        {
            return stopPts * pv + 2 * SizingCommission + ReserveTicks * TickSize * pv;
        }

        // ── The account: equity since the evaluation start (closed + open), its peak, the reserve line
        double Closed()
        {
            if (State == State.Realtime && AccountFromBroker && Account != null)
            {
                double cash = Account.Get(AccountItem.CashValue, Currency.UsDollar);
                if (cash > 0) return cash - AccountStart;
            }
            double sum = 0;
            for (int k = 0; k < SystemPerformance.AllTrades.Count; k++)
            {
                Trade tr = SystemPerformance.AllTrades[k];
                if (evalStart == DateTime.MinValue || ToNy(tr.Entry.Time).Date >= evalStart)
                    sum += tr.ProfitCurrency;
            }
            return sum;
        }

        // the open P/L at a price, both commissions charged (the exit's is due when it closes)
        double OpenAt(double price)
        {
            int d = Dir;
            if (d == 0) return 0;
            return d * (price - Position.AveragePrice) * Position.Quantity * pv - 2 * SizingCommission * Position.Quantity;
        }

        double Threshold { get { return peak - EvalTrail; } }
        double ReserveLine { get { return Threshold + AccountReserve; } }

        // the price at which equity (closed + this position, both fees) would stand at `level`
        double PriceForEquity(double closed, double level)
        {
            int d = Dir;
            return Position.AveragePrice + d * (level - closed + 2 * SizingCommission * Position.Quantity) /
                   (Position.Quantity * pv);
        }

        void DayLedger(DateTime nyNow, double closed)
        {
            DateTime day = TradingDay(nyNow);
            if (day != lastDay)
            {
                lastDay = day;
                dayStartEq = closed;
                dayLosers = 0;
            }
            // completed positions (one per entry time and name) closed today: count the losers once each. Live, only the
            // account's real fills (the simulated history before going live is not the account's)
            TradeCollection src = State == State.Realtime ? SystemPerformance.RealTimeTrades : SystemPerformance.AllTrades;
            Dictionary<string, double> pos = new Dictionary<string, double>();
            for (int k = src.Count - 1; k >= 0; k--)
            {
                Trade tr = src[k];
                if (TradingDay(ToNy(tr.Exit.Time)) != day) break;
                string key = tr.Entry.Time.Ticks + "|" + tr.Entry.Name;
                double v;
                pos[key] = (pos.TryGetValue(key, out v) ? v : 0) + tr.ProfitCurrency;
            }
            if (Dir == 0)
                foreach (KeyValuePair<string, double> kv in pos)
                    if (kv.Value < 0 && !countedTrades.ContainsKey(kv.Key))
                    {
                        countedTrades[kv.Key] = true;
                        dayLosers++;
                    }
        }

        // ── Live: the peak, the pass and today's losers survive a restart
        string AccountFile
        {
            get
            {
                string name = Account == null || string.IsNullOrEmpty(Account.Name) ? "account" : Account.Name;
                foreach (char c in Path.GetInvalidFileNameChars()) name = name.Replace(c, '_');
                return Path.Combine(Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "MnqNoiseMomentum"), "runner-account-" + name + ".txt");
            }
        }

        void LoadAccount()
        {
            // going live: the account's own numbers, not the simulated history's
            peak = double.NaN;
            passed = false;
            lastDay = DateTime.MinValue;
            dayLosers = 0;
            countedTrades.Clear();
            if (!RememberAccount) return;
            try
            {
                if (!File.Exists(AccountFile)) return;
                foreach (string line in File.ReadAllLines(AccountFile))
                {
                    string[] kv = line.Split('=');
                    if (kv.Length != 2) continue;
                    if (kv[0] == "peak") peak = double.Parse(kv[1], CultureInfo.InvariantCulture);
                    else if (kv[0] == "passed") passed = kv[1] == "1";
                    else if (kv[0] == "day") lastDay = DateTime.ParseExact(kv[1], "yyyy-MM-dd", CultureInfo.InvariantCulture);
                    else if (kv[0] == "losers") dayLosers = int.Parse(kv[1], CultureInfo.InvariantCulture);
                    else if (kv[0] == "dayStart") dayStartEq = double.Parse(kv[1], CultureInfo.InvariantCulture);
                }
                Print("MNQ runner: account state from " + AccountFile + ": highest equity " + F0(peak) + (passed ? ", target reached" : ""));
            }
            catch (Exception e)
            {
                Print("MNQ runner: could not read " + AccountFile + " (" + e.Message + ").");
            }
        }

        void SaveAccount()
        {
            if (!RememberAccount || State != State.Realtime) return;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(AccountFile));
                File.WriteAllText(AccountFile, "peak=" + peak.ToString("R", CultureInfo.InvariantCulture) + "\npassed=" + (passed ? "1" : "0") +
                    "\nday=" + lastDay.ToString("yyyy-MM-dd") + "\nlosers=" + dayLosers + "\ndayStart=" +
                    dayStartEq.ToString("R", CultureInfo.InvariantCulture) + "\n");
            }
            catch (Exception e)
            {
                Print("MNQ runner: could not write " + AccountFile + " (" + e.Message + ").");
            }
        }

        // ── 5-minute ATR from the completed 1-minute bars of 09:30-16:00
        void UpdateAtr(int tMin)
        {
            if (tMin < NoiseEngine.RthOpen || tMin >= NoiseEngine.RthClose) return;
            int key = tMin / 5;
            if (key != fiveKey && fiveKey >= 0 && !double.IsNaN(fiveC))
                CloseFive();  // the previous 5-minute bar ended with a missing minute
            if (key != fiveKey)
            {
                fiveKey = key;
                fiveH = High[0];
                fiveL = Low[0];
            }
            else
            {
                fiveH = Math.Max(fiveH, High[0]);
                fiveL = Math.Min(fiveL, Low[0]);
            }
            fiveC = Close[0];
            if ((tMin + 1) % 5 == 0)
                CloseFive();
        }

        void CloseFive()
        {
            double tr = double.IsNaN(prevFiveC) ? fiveH - fiveL :
                        Math.Max(fiveH, prevFiveC) - Math.Min(fiveL, prevFiveC);
            prevFiveC = fiveC;
            fiveC = double.NaN;
            fiveKey = -1;
            atrCount++;
            if (atrCount <= AtrBars)
            {
                atrSum += tr;
                if (atrCount == AtrBars) atr = atrSum / AtrBars;
            }
            else
                atr = (atr * (AtrBars - 1) + tr) / AtrBars;
        }

        // the minute (New York) by which to be flat: FlatMinute, or 5 minutes before an earlier session end
        DateTime flatDay = DateTime.MinValue;
        int flatCached;

        int FlatBy(DateTime barEndPlatform)
        {
            DateTime dayNy = ToNy(barEndPlatform).Date;
            if (dayNy == flatDay) return flatCached;
            int flat = Math.Min(FlatMinute, NoiseEngine.RthClose);  // never past 16:00, the last bar the strategy trades
            try
            {
                if (sessions != null && sessions.GetNextSession(barEndPlatform, true))
                {
                    DateTime end = ToNy(sessions.ActualSessionEnd);
                    DateTime endNy = ToNy(barEndPlatform);
                    if (end.Date == endNy.Date)
                        flat = Math.Min(flat, end.Hour * 60 + end.Minute - 5);
                }
            }
            catch (Exception)
            {
                // no session information: 15:55
            }
            flatDay = dayNy;
            flatCached = flat;
            return flat;
        }

        void Skip(string why)
        {
            skipped++;
            int n;
            skipWhy[why] = (skipWhy.TryGetValue(why, out n) ? n : 0) + 1;
            notSent = why;
            Print("MNQ runner: signal " + ToNy(Time[0]).AddMinutes(-1).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) +
                  " not taken: " + why);
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;
            if (badChart || Calculate != Calculate.OnBarClose)
            {
                Draw.TextFixed(this, "runner_dash", "MNQ Momentum Runner: use a 1-minute chart, Calculate on bar close. Not trading.",
                               TextPosition.TopRight);
                return;
            }
            DateTime endNy = ToNy(Time[0]);
            DateTime start = endNy.AddMinutes(-1);
            int tMin = start.Hour * 60 + start.Minute, endMin = tMin + 1;
            int nOrders = engine.Orders.Count;
            engine.ExternalLosers = dayLosers;  // B's model limit counts real losing positions (ours stops at 2 anyway)
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            UpdateAtr(tMin);
            bool inEval = evalStart == DateTime.MinValue || start.Date >= evalStart;
            if (!PlaceOrders || !inEval)
            {
                Draw.TextFixed(this, "runner_dash", Dashboard(), TextPosition.TopRight);
                return;
            }

            // the account at this bar: closed, open at the bar's best and at its close, the peak, the reserve line
            int d = Dir;
            double closed = Closed();
            double best = d == 0 ? 0 : OpenAt(d > 0 ? High[0] : Low[0]);
            double now = d == 0 ? 0 : OpenAt(Close[0]);
            if (double.IsNaN(peak)) peak = Math.Max(0, closed);
            peak = Math.Max(peak, Math.Max(closed + best, closed));
            if (LiquidationThreshold > 0)  // the threshold Apex shows: the highest equity is at least it + the trail
                peak = Math.Max(peak, LiquidationThreshold - AccountStart + EvalTrail);
            DayLedger(start, closed);
            int flatBy = FlatBy(Time[0]);
            bool inRth = tMin >= NoiseEngine.RthOpen && endMin <= NoiseEngine.RthClose;

            // the evaluation's target: realized, then everything closed and no more trades
            if (!passed && EvalTarget > 0 && closed >= EvalTarget)
                passed = true;
            if (d == 0) mustClose = false;
            if (d != 0 && mustClose)
            {
                Print(Time[0] + "  the position is closed again at market after a rejected order.");
                Flatten(d, "Close: retry");
                Finish(d);
                return;
            }
            if (passed || (EvalTarget > 0 && d != 0 && closed + now >= EvalTarget + 25))
            {
                if (d != 0) Flatten(d, "Evaluation target");
                passed = passed || closed + now >= EvalTarget + 25;
                Finish(d);
                return;
            }
            if (d != 0 && (endMin >= flatBy || !inRth || tMin == NoiseEngine.RthOpen))
            {
                Flatten(d, "Flat " + NoiseEngine.Hhmm(Math.Min(flatBy, NoiseEngine.RthClose)));
                Finish(d);
                return;
            }
            if (d != 0)
            {
                ManagePosition(d, closed);
                Finish(d);
                return;
            }

            // flat: reset, then a new entry if B signals and the account allows it
            plannedStopPts = rPts = bestPx = lastStop = double.NaN;
            locked = trailOn = false;
            if (engine.Orders.Count > nOrders)
            {
                NoiseOrder o = engine.Orders[engine.Orders.Count - 1];
                TryEnter(o, closed, endMin, flatBy);
            }
            Finish(0);
        }

        void Finish(int d)
        {
            SaveAccount();
            Draw.TextFixed(this, "runner_dash", Dashboard(), TextPosition.TopRight);
        }

        void TryEnter(NoiseOrder o, double closed, int endMin, int flatBy)
        {
            if (endMin >= flatBy) { Skip("after the flat time"); return; }
            if (dayLosers >= MaxLosingPositions) { Skip("losing positions today"); return; }
            if (State == State.Realtime && PositionAccount != null && PositionAccount.MarketPosition != MarketPosition.Flat)
            {
                Skip("the account holds a position the strategy does not");
                return;
            }
            double stopPts = StopTicks(o.Direction * (o.Expected - o.Stop)) * TickSize;
            if (stopPts > CapPoints + 1e-9) stopPts = Math.Floor(CapPoints / TickSize + 1e-9) * TickSize;
            double rpc = RiskPerContract(stopPts);
            double room = closed - (peak - EvalTrail + AccountReserve);
            double dayNet = closed - dayStartEq;
            double dayRoom = DailyLossBackstop + dayNet;
            double budget = Math.Min(MaxRisk, Math.Min(room / 2, dayRoom));
            int qty = (int)Math.Min(MaxContracts, Math.Floor(budget / rpc + 1e-9));
            if (qty < 1)
            {
                Skip(room / 2 < rpc ? "account reserve room" : dayRoom < rpc ? "daily backstop" : "risk budget");
                return;
            }
            string name = o.Direction > 0 ? LongName : ShortName;
            SetStopLoss(name, CalculationMode.Ticks, stopPts / TickSize, false);
            double tpPts = double.NaN;
            if (!RunnerExit && TakeProfit > 0 && !double.IsNaN(o.Target))
                tpPts = o.Direction * (o.Target - o.Expected);
            if (EvalTarget > 0)
            {
                double evalPts = (EvalTarget + 25 - closed + 2 * SizingCommission * qty) / (qty * pv);
                if (double.IsNaN(tpPts) || evalPts < tpPts) tpPts = evalPts;
            }
            if (!double.IsNaN(tpPts))
                SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Ceiling(tpPts / TickSize - 1e-7)));
            if (o.Direction > 0) EnterLong(qty, name); else EnterShort(qty, name);
            plannedStopPts = stopPts;
            entries++;
        }

        void ManagePosition(int d, double closed)
        {
            double avg = Position.AveragePrice;
            if (double.IsNaN(rPts))
            {
                rPts = double.IsNaN(plannedStopPts) ? CapPoints : plannedStopPts;  // fixed for the position
                lastStop = avg - d * rPts;   // the bracket sent with the entry, in ticks from the fill
                bestPx = avg;
            }
            bestPx = d > 0 ? Math.Max(bestPx, High[0]) : Math.Min(bestPx, Low[0]);
            double fav = d * (bestPx - avg);
            if (!locked && fav >= LockAtPoints) locked = true;
            if (RunnerExit && !trailOn && fav >= TrailActivateR * rPts) trailOn = true;

            // B's stop: the noise line, the 25-point cap from the fill, the lock
            double stop = double.NaN;
            if (!double.IsNaN(engine.Upper))
                stop = d > 0 ? engine.Upper * (1 - 0.24 * engine.Sigma) : engine.Lower * (1 + 0.24 * engine.Sigma);
            double cap = avg - d * CapPoints;
            stop = Tighter(d, stop, cap);
            if (locked) stop = Tighter(d, stop, avg + d * LockPlusPoints);
            if (trailOn && !double.IsNaN(atr)) stop = Tighter(d, stop, bestPx - d * TrailAtr * atr);
            // the account: never let the position take equity below the reserve line
            double reservePx = PriceForEquity(closed, ReserveLine);
            stop = Tighter(d, stop, reservePx);
            stop = Tighter(d, stop, lastStop);  // never loosens
            stop = RoundStop(d, stop);
            lastStop = stop;
            if ((d > 0 && stop >= Close[0]) || (d < 0 && stop <= Close[0]))
            {
                Flatten(d, (d > 0 ? reservePx >= Close[0] : reservePx <= Close[0]) ? "Account reserve" : "Stop passed");
                return;
            }
            string name = d > 0 ? LongName : ShortName;
            SetStopLoss(name, CalculationMode.Price, stop, false);
            double tp = double.NaN;
            if (!RunnerExit && TakeProfit > 0 && !double.IsNaN(engine.Sigma))
                tp = avg * (1 + d * TakeProfit * engine.Sigma);
            if (EvalTarget > 0)
            {
                double et = PriceForEquity(closed, EvalTarget + 25);
                if (double.IsNaN(tp) || (d > 0 && et < tp) || (d < 0 && et > tp)) tp = et;
            }
            if (!double.IsNaN(tp))
                SetProfitTarget(name, CalculationMode.Price, RoundTarget(d, tp));
        }

        static double Tighter(int d, double a, double b)
        {
            if (double.IsNaN(a)) return b;
            if (double.IsNaN(b)) return a;
            return d > 0 ? Math.Max(a, b) : Math.Min(a, b);
        }

        void Flatten(int d, string why)
        {
            lastExit = why;
            if (d > 0) ExitLong(why, ""); else if (d < 0) ExitShort(why, "");
        }

        double RoundStop(int d, double price)
        {
            double n = price / TickSize;
            return (d > 0 ? Math.Ceiling(n - 1e-7) : Math.Floor(n + 1e-7)) * TickSize;  // toward the price
        }

        double RoundTarget(int d, double price) { return RoundStop(d, price); }  // away from the price

        double StopTicks(double points)
        {
            return Math.Max(1, Math.Floor(points / TickSize + 1e-7));
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time,
                                              ErrorCode error, string comment)
        {
            if (orderState != OrderState.Rejected) return;
            Print(Time[0] + "  ORDER REJECTED: " + order.Name + " (" + comment + ").");
            int d = Dir;
            if (d == 0) return;
            bool ours = order.Name == "Close: rejected" || order.Name == "Close: retry";
            mustClose = true;  // never left without protection: closed now, and again at each bar until flat
            if (!ours) Flatten(d, "Close: rejected");
        }

        string Dashboard()
        {
            int d = Dir;
            string s = "MNQ Momentum Runner (" + (RunnerExit ? "runner exit" : "B exits") + "), " + (PlaceOrders ? "orders ON" : "orders OFF") + "\n";
            s += "Equity since start " + F0(Closed()) + ", highest " + F0(peak) + ", liquidation line " + F0(peak - EvalTrail) +
                 ", reserve line " + F0(peak - EvalTrail + AccountReserve) + (passed ? " - TARGET REACHED, no more trades" : "") + "\n";
            s += "Today: " + dayLosers + " losing positions, net " + F0(Closed() - dayStartEq) + "\n";
            s += "ATR(5 min) " + F0(atr) + (d != 0 ? ", position " + (d > 0 ? "LONG " : "SHORT ") + Position.Quantity + " @ " +
                 F0(Position.AveragePrice) + ", stop " + F0(lastStop) + (trailOn ? " (trailing)" : locked ? " (locked)" : "") : ", flat") +
                 (notSent.Length > 0 ? "\nLast skipped signal: " + notSent : "");
            return s;
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 1, GroupName = "1. Trading")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Runner exit (off: B's take-profit)", Order = 2, GroupName = "1. Trading")]
        public bool RunnerExit { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 10000.0)]
        [Display(Name = "Max planned loss per position, $ (costs included)", Order = 3, GroupName = "1. Trading")]
        public double MaxRisk { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max contracts", Order = 4, GroupName = "1. Trading")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 20.0)]
        [Display(Name = "Commission per side per contract, $ (for sizing)", Order = 5, GroupName = "1. Trading")]
        public double SizingCommission { get; set; }

        [NinjaScriptProperty]
        [Range(0, 40)]
        [Display(Name = "Sizing reserve, ticks (2 at entry + 2 at the stop)", Order = 6, GroupName = "1. Trading")]
        public int ReserveTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "B exits: take-profit, noise units", Order = 7, GroupName = "1. Trading")]
        public double TakeProfit { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 20.0)]
        [Display(Name = "Runner: trail, x ATR", Order = 8, GroupName = "1. Trading")]
        public double TrailAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 20.0)]
        [Display(Name = "Runner: trail starts at this many R", Order = 9, GroupName = "1. Trading")]
        public double TrailActivateR { get; set; }

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Runner: ATR length, 5-minute bars", Order = 10, GroupName = "1. Trading")]
        public int AtrBars { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Flat by, minute of day New York (955 = 15:55)", Order = 11, GroupName = "1. Trading")]
        public int FlatMinute { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Evaluation: profit target, $ (0 = off)", Order = 1, GroupName = "2. Account")]
        public double EvalTarget { get; set; }

        [NinjaScriptProperty]
        [Range(100.0, 100000.0)]
        [Display(Name = "Evaluation: trailing drawdown, $", Order = 2, GroupName = "2. Account")]
        public double EvalTrail { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10000.0)]
        [Display(Name = "Reserve above the liquidation line, $", Order = 3, GroupName = "2. Account")]
        public double AccountReserve { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Daily net-loss backstop, $ (planned risk included)", Order = 4, GroupName = "2. Account")]
        public double DailyLossBackstop { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "No entries after this many losing positions today", Order = 5, GroupName = "2. Account")]
        public int MaxLosingPositions { get; set; }

        [NinjaScriptProperty]
        [Range(1000.0, 1000000.0)]
        [Display(Name = "Account starting balance, $", Order = 6, GroupName = "2. Account")]
        public double AccountStart { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 1000000.0)]
        [Display(Name = "Live: the account's liquidation threshold now, $ (0 = unknown)", Order = 10, GroupName = "2. Account")]
        public double LiquidationThreshold { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Evaluation start (yyyy-MM-dd; empty: the first bar)", Order = 7, GroupName = "2. Account")]
        public string EvaluationStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Live: read the account's balance from the broker", Order = 8, GroupName = "2. Account")]
        public bool AccountFromBroker { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Live: remember the highest equity, the pass and today's losers in a file", Order = 9, GroupName = "2. Account")]
        public bool RememberAccount { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Skip dates (yyyy-MM-dd,...)", Order = 1, GroupName = "3. Entries (B's)")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed dates (yyyy-MM-dd,...)", Order = 2, GroupName = "3. Entries (B's)")]
        public string FedDates { get; set; }
        #endregion
    }
}
