// MNQ Momentum C (candidate, docs/CANDIDATE_C.md): B's signals and exits with risk-budget sizing, account protection
// for the $50K intraday-trailing evaluation, and execution-state handling that keeps signals apart from orders.
//
// Signals: B's (AddOns/MnqNoiseEngine.cs, unchanged, supplies the noise lines): at each half-hour check 10:00-15:30
// New York, once the engine has its 14 full sessions, a completed check bar closing above the upper line is a long
// signal, below the lower line a short one; none on skip dates, no short before 14:00 on Fed days. Entry at the next
// bar's open. Each check is qualified from the market data alone: the engine's own model position, which can differ
// from the account's (a refused entry, a different exit), never blocks a check while the strategy is flat
// (SignalsFromModel = true restores the earlier coupling, for comparison only).
// Orders are gated by the actual position, a pending entry order, the account's position, and the risk limits. One
// position at a time; a re-entry needs a fresh qualifying check after the previous position closed.
//
// Sizing, before each entry:
//   stop distance = B's protective stop (the closer of the noise-line stop and 25 points), whole ticks
//   risk per contract = stop distance x $2 + 2 x commission + a reserve of 2 ticks at entry and 2 at the stop
//     (= 2 x points + $3.90 at $0.95 a side)
//   contracts = floor(budget / risk per contract), at most 4; none fits: no trade
//   budget = the smallest of $200, half the room above the account's reserve line (ReserveRoomShare 0.5; the full room,
//     1.0, was tested and rejected: docs/FREQUENCY.md), and what is left of today's $400 loss backstop
// Exits: B's, unchanged: the protective stop from the fill (the noise line and the 25-point cap), the lock (at +25
// points the stop goes to entry + 2.5), the stop only ever tightens, the take-profit 1.5 noise units from the fill.
// Also: flat by 15:55 New York (5 minutes before an earlier session end); the account reserve; the evaluation target.
// Account (evaluation profile: $3,000 target, $2,000 intraday trail of the highest equity, unrealized included):
//   threshold = highest equity - $2,000; reserve line = threshold + $300; a position's stop is never below the reserve
//   line's price (closed at market if already past); no entry after 2 losing positions today, or whose planned risk
//   could take today below -$400. An open profit past the target closes the position; the evaluation counts as passed
//   only when realized net profit (the account's cash, or the closed trades) reaches the target, and only then does
//   the strategy stop (PassOnRealizedOnly = false restores the earlier rule, for comparison only).
// Orders: a rejected order while in a position closes it at market, sent again at every bar until flat; a rejected
// entry leaves no position. A partly filled entry's remainder is tracked until it fills or is cancelled; it is
// cancelled if the position closes first, or at the flat time. Losing positions are counted by their entry order,
// not by fill times. A position's equity history ends at its exit: a take-profit or an opening-gap stop adds nothing
// after the fill; for a stop filled inside a bar, whose best price may have come before or after it, the protective
// highest equity (used for the reserve) counts that price and the determined one does not; both are reported. Live, the highest equity, the pass and today's losers are kept in a file (restarts), and the
// threshold Apex shows can be entered.
// Output: one line per check whose close is past a line (taken, or why not; a refusal for room gives the room and one
// contract's planned risk), one line per session (its data, checks and outcome), and an audit at the end of the run
// (data coverage, warm-up, first and last trades, signals, entries, refusals by reason, whether trading stopped).
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
    public class MnqMomentumC : Strategy
    {
        const string LongName = "Long", ShortName = "Short";
        const double CapPoints = 25.0;      // B's max loss per trade in points ($200 / 4 MNQ / $2)
        const double LockAtPoints = 25.0;   // B's lock: at 1 cap of profit ...
        const double LockPlusPoints = 2.5;  // ... the stop to entry + 2.5 points
        const double StopBuffer = 0.24, TakeProfit = 1.5;  // B's line stop buffer and take-profit, noise units
        NoiseEngine engine;
        TimeZoneInfo newYork;
        SessionIterator sessions;
        bool badChart;
        double pv;

        // the position (from executions)
        double plannedStopPts = double.NaN;  // the stop distance the entry was sized with
        double rPts = double.NaN;            // the fill to the initial stop, fixed for the position
        double bestPx = double.NaN;          // best price since the entry (completed bars)
        double lastStop = double.NaN;        // the stop so far: it only tightens
        bool locked;
        bool mustClose;                      // an order was rejected: close at market, again at every bar until flat
        Order entryOrder;                    // an entry sent and not yet filled, cancelled or rejected (a part-filled
                                             // entry stays here until its remainder fills or is cancelled)
        bool entryPartFilled, cancelSent;
        int tradesAtLastBar;                 // trade records already seen, for a position that closed within a bar

        // the account
        double peak = double.NaN;            // highest equity since the evaluation start (unrealized included), protective:
                                             // a bar's best price counts when it may have come before a stop in the bar
        double peakLow = double.NaN;         // the same, counting only prices known to have come before each exit
        bool passed;
        DateTime evalStart = DateTime.MinValue;
        DateTime lastDay = DateTime.MinValue;
        double dayStartEq;
        int dayLosers;
        readonly Dictionary<string, bool> countedTrades = new Dictionary<string, bool>();
        string notSent = "";

        // the audit
        int bars, rthSessions, fullSessions, sessionBars, checks, crosses, qualifying, entries;
        DateTime firstBar = DateTime.MinValue, lastBar, readyAt = DateTime.MinValue, auditDay = DateTime.MinValue;
        DateTime lastEntrySignal = DateTime.MinValue;
        bool sessionOpenBar, sessionSkip;
        int sessChecks, sessNotReady, sessCross, sessQual, sessEntries;
        readonly Dictionary<string, int> sessRefused = new Dictionary<string, int>();
        readonly Dictionary<string, int> refused = new Dictionary<string, int>();
        readonly List<string> sinceLastEntry = new List<string>();  // why each qualifying signal after the last entry was refused

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqMomentumC";
                Description = "MNQ momentum (B's signals and exits) with risk-budget sizing, evaluation account protection and signals kept apart from orders.";
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
                SignalsFromModel = false;
                PassOnRealizedOnly = true;
                MaxRisk = 200;
                MaxContracts = 4;
                SizingCommission = 0.95;
                ReserveTicks = 4;
                FlatMinute = 955;      // 15:55 New York
                EvalTarget = 3000;
                EvalTrail = 2000;
                AccountReserve = 300;
                DailyLossBackstop = 400;
                MaxLosingPositions = 2;
                AccountStart = 50000;
                LiquidationThreshold = 0;
                EvaluationStart = "";
                AccountFromBroker = true;
                SkipDates = NoiseEngine.SkipDatesDefault;
                FedDates = NoiseEngine.FedDatesDefault;
                RememberAccount = true;
                CheckLines = true;
                ReserveRoomShare = 0.5;  // C1, as tested; 1.0 (C2) was rejected: docs/FREQUENCY.md
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                badChart = BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1;
                pv = Instrument.MasterInstrument.PointValue;
                NoiseSettings settings = new NoiseSettings();  // B's settings, so the lines and signals are B's
                settings.Qty = 4;
                settings.Tick = TickSize;
                settings.PointValue = pv;
                settings.MaxLoss = 200;
                settings.TakeProfit = TakeProfit;
                settings.StopBuffer = StopBuffer;
                settings.LockAt = 1.0;
                settings.LockPlus = LockPlusPoints;
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
                Print("C settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", PlaceOrders " + PlaceOrders +
                      ", SignalsFromModel " + SignalsFromModel + ", PassOnRealizedOnly " + PassOnRealizedOnly +
                      ", MaxRisk " + MaxRisk + ", MaxContracts " + MaxContracts + ", commission " + SizingCommission +
                      ", reserve ticks " + ReserveTicks + ", room share " + ReserveRoomShare + ", target " + EvalTarget + ", trail " + EvalTrail + ", reserve " +
                      AccountReserve + ", daily backstop " + DailyLossBackstop + ", losers " + MaxLosingPositions +
                      ", flat at " + NoiseEngine.Hhmm(FlatMinute) + ", evaluation start " +
                      (evalStart == DateTime.MinValue ? "(the first bar)" : evalStart.ToString("yyyy-MM-dd")));
            }
            else if (State == State.Realtime)
                LoadAccount();
            else if (State == State.Terminated && engine != null)
                Audit();
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        static string F0(double x) { return double.IsNaN(x) ? "-" : x.ToString("0.00", CultureInfo.InvariantCulture); }

        static string Ts(DateTime t) { return t == DateTime.MinValue ? "-" : t.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture); }

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
                string key = PositionKey(tr);
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
                return Path.Combine(Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "MnqNoiseMomentum"), "c-account-" + name + ".txt");
            }
        }

        void LoadAccount()
        {
            // going live: the account's own numbers, not the simulated history's
            peak = peakLow = double.NaN;
            passed = false;
            lastDay = DateTime.MinValue;
            dayLosers = 0;
            countedTrades.Clear();
            entryOrder = null;
            if (!RememberAccount) return;
            try
            {
                if (!File.Exists(AccountFile)) return;
                foreach (string line in File.ReadAllLines(AccountFile))
                {
                    string[] kv = line.Split('=');
                    if (kv.Length != 2) continue;
                    if (kv[0] == "peak") peak = double.Parse(kv[1], CultureInfo.InvariantCulture);
                    else if (kv[0] == "peakDetermined") peakLow = double.Parse(kv[1], CultureInfo.InvariantCulture);
                    else if (kv[0] == "passed") passed = kv[1] == "1";
                    else if (kv[0] == "day") lastDay = DateTime.ParseExact(kv[1], "yyyy-MM-dd", CultureInfo.InvariantCulture);
                    else if (kv[0] == "losers") dayLosers = int.Parse(kv[1], CultureInfo.InvariantCulture);
                    else if (kv[0] == "dayStart") dayStartEq = double.Parse(kv[1], CultureInfo.InvariantCulture);
                }
                Print("C: account state from " + AccountFile + ": highest equity " + F0(peak) + (passed ? ", target reached" : ""));
            }
            catch (Exception e)
            {
                Print("C: could not read " + AccountFile + " (" + e.Message + ").");
            }
        }

        void SaveAccount()
        {
            if (!RememberAccount || State != State.Realtime) return;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(AccountFile));
                File.WriteAllText(AccountFile, "peak=" + peak.ToString("R", CultureInfo.InvariantCulture) +
                    "\npeakDetermined=" + peakLow.ToString("R", CultureInfo.InvariantCulture) + "\npassed=" + (passed ? "1" : "0") +
                    "\nday=" + lastDay.ToString("yyyy-MM-dd") + "\nlosers=" + dayLosers + "\ndayStart=" +
                    dayStartEq.ToString("R", CultureInfo.InvariantCulture) + "\n");
            }
            catch (Exception e)
            {
                Print("C: could not write " + AccountFile + " (" + e.Message + ").");
            }
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

        // ── The audit: data coverage, signals and what became of them
        void CountBar(DateTime start, int tMin)
        {
            bars++;
            if (firstBar == DateTime.MinValue) firstBar = start;
            lastBar = start;
            DateTime day = TradingDay(start);
            if (day != auditDay)
            {
                EndSession();
                auditDay = day;
            }
            if (tMin >= NoiseEngine.RthOpen && tMin < NoiseEngine.RthClose)
            {
                sessionBars++;
                if (tMin == NoiseEngine.RthOpen) sessionOpenBar = true;
            }
            if (readyAt == DateTime.MinValue && engine.Ready) readyAt = start;
        }

        void EndSession()
        {
            if (sessionBars > 0)
            {
                rthSessions++;
                string why = "";
                foreach (KeyValuePair<string, int> kv in sessRefused)
                    why += (why.Length > 0 ? ", " : "") + kv.Key + " " + kv.Value;
                string status = !sessionOpenBar ? "missing data (no 09:30 bar)" :
                                sessChecks == 0 && sessNotReady > 0 ? "warm-up" :
                                sessionSkip ? "skip date" :
                                sessEntries > 0 ? "active" :
                                sessQual == 0 ? "no qualifying setup" : "all refused: " + why;
                if (CheckLines)
                    Print("C session " + auditDay.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + ": " + status + "; " +
                          sessionBars + " minutes 09:30-16:00" + (sessionBars < 390 ? " (short)" : "") + ", checks " + sessChecks +
                          ", past a line " + sessCross + ", qualifying " + sessQual + ", entries " + sessEntries +
                          ", losing positions " + dayLosers + ", not taken " + (why.Length > 0 ? why : "none"));
            }
            if (sessionBars >= 390 && sessionOpenBar) fullSessions++;
            sessionBars = 0;
            sessionOpenBar = sessionSkip = false;
            sessChecks = sessNotReady = sessCross = sessQual = sessEntries = 0;
            sessRefused.Clear();
        }

        void Refuse(DateTime t, int dir, string why)
        {
            Refuse(t, dir, why, "");
        }

        void Refuse(DateTime t, int dir, string why, string detail)
        {
            int n;
            refused[why] = (refused.TryGetValue(why, out n) ? n : 0) + 1;
            sessRefused[why] = (sessRefused.TryGetValue(why, out n) ? n : 0) + 1;
            sinceLastEntry.Add(why);
            notSent = why;
            if (CheckLines)
                Print("C check " + Ts(t) + " " + (dir > 0 ? "long" : "short") + ": not taken: " + why +
                      (detail.Length > 0 ? " [" + detail + "]" : ""));
        }

        void Audit()
        {
            EndSession();
            Print("C audit: bars " + bars + ", first " + Ts(firstBar) + ", last " + Ts(lastBar) + " (New York, bar start)");
            Print("C audit: sessions with 09:30-16:00 data " + rthSessions + ", complete (09:30 bar and 390 minutes) " + fullSessions);
            Print("C audit: engine ready (14 full sessions) " + (readyAt == DateTime.MinValue ? "never" : "from " + Ts(readyAt)));
            int nt = SystemPerformance.AllTrades.Count;
            Print("C audit: trades " + nt + (nt > 0 ? ", first entry " + Ts(ToNy(SystemPerformance.AllTrades[0].Entry.Time)) +
                  ", last exit " + Ts(ToNy(SystemPerformance.AllTrades[nt - 1].Exit.Time)) : ""));
            Print("C audit: checks with lines " + checks + ", closes past a line " + crosses + ", qualifying signals " + qualifying +
                  ", entries sent " + entries);
            string s = "";
            foreach (KeyValuePair<string, int> kv in refused)
                s += (s.Length > 0 ? "; " : "") + kv.Key + " " + kv.Value;
            Print("C audit: not taken: " + (s.Length > 0 ? s : "none"));
            string stopped = "trading active to the end";
            if (passed)
                stopped = "evaluation passed (realized), no entries after it";
            else if (sinceLastEntry.Count > 0)
            {
                bool allRoom = true;
                foreach (string w in sinceLastEntry) allRoom = allRoom && w == "account reserve room";
                stopped = (allRoom ? "STOPPED: " : "") + sinceLastEntry.Count + " qualifying signal(s) after the last entry (" +
                          Ts(lastEntrySignal) + "), none taken" + (allRoom ? ", all for lack of room above the reserve" : "");
            }
            Print("C audit: " + stopped + "; highest equity " + F0(peak) + " (determined " + F0(peakLow) +
                  "; the difference is bars' best prices that may have come before a stop in them), equity " + F0(Closed()));
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;
            if (badChart || Calculate != Calculate.OnBarClose)
            {
                Draw.TextFixed(this, "c_dash", "MNQ Momentum C: use a 1-minute chart, Calculate on bar close. Not trading.",
                               TextPosition.TopRight);
                return;
            }
            DateTime endNy = ToNy(Time[0]);
            DateTime start = endNy.AddMinutes(-1);
            int tMin = start.Hour * 60 + start.Minute, endMin = tMin + 1;
            int nOrders = engine.Orders.Count;
            engine.ExternalLosers = dayLosers;
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            CountBar(start, tMin);

            // the check: B's qualification from the lines, the close and the dates (not from the model's position)
            int signal = 0;
            string note = engine.CheckNote;
            if (note == "not ready") sessNotReady++;
            if (note != "" && note != "not ready")
            {
                checks++;
                sessChecks++;
                if (engine.SkipToday) sessionSkip = true;
                int cross = Close[0] > engine.Upper ? 1 : Close[0] < engine.Lower ? -1 : 0;
                if (cross != 0)
                {
                    crosses++;
                    sessCross++;
                    if (engine.SkipToday) { }
                    else if (cross < 0 && engine.FedToday && endMin < NoiseEngine.FedCutoff) { }
                    else
                    {
                        qualifying++;
                        sessQual++;
                        signal = cross;
                    }
                }
            }

            bool inEval = evalStart == DateTime.MinValue || start.Date >= evalStart;
            if (!PlaceOrders || !inEval)
            {
                if (signal != 0) Refuse(start, signal, PlaceOrders ? "before the evaluation start" : "orders off");
                Draw.TextFixed(this, "c_dash", Dashboard(), TextPosition.TopRight);
                return;
            }

            // the account at this bar: closed, open at the bar's best and at its close, the peak, the reserve line
            int d = Dir;
            double closed = Closed();
            double best = d == 0 ? 0 : OpenAt(d > 0 ? High[0] : Low[0]);
            double now = d == 0 ? 0 : OpenAt(Close[0]);
            if (double.IsNaN(peak)) peak = Math.Max(0, closed);
            peak = Math.Max(peak, Math.Max(closed + best, closed));
            if (double.IsNaN(peakLow)) peakLow = Math.Max(0, closed);
            peakLow = Math.Max(peakLow, Math.Max(closed + best, closed));
            // A position that closed during this bar. Its equity history ends at its exit:
            //   take-profit: its best price before the exit is the exit itself (realized; prices beyond came after);
            //   a stop the bar opened past, or a market exit: filled at the open, nothing later in the bar counts;
            //   a stop filled inside the bar: the bar's open is certain; its best price may have come before the stop
            //   or after it (bars carry no order). The determined peak takes the open, the protective one the best price.
            int nRec = SystemPerformance.AllTrades.Count;
            double later = 0;
            for (int k = tradesAtLastBar; k < nRec; k++) later += SystemPerformance.AllTrades[k].ProfitCurrency;
            int g = tradesAtLastBar;
            while (g < nRec)
            {
                Trade first = SystemPerformance.AllTrades[g];
                string key = PositionKey(first);
                double q = 0, cost = 0, profit = 0;
                int h = g;
                for (; h < nRec && PositionKey(SystemPerformance.AllTrades[h]) == key; h++)
                {
                    Trade tr = SystemPerformance.AllTrades[h];
                    q += tr.Quantity;
                    cost += tr.Entry.Price * tr.Quantity;
                    profit += tr.ProfitCurrency;
                }
                int td = first.Entry.Name == ShortName ? -1 : 1;
                bool counted = evalStart == DateTime.MinValue || ToNy(first.Entry.Time).Date >= evalStart;
                bool gapped = !double.IsNaN(lastStop) && td * (Open[0] - lastStop) <= 0;
                if (first.Exit.Name == "Stop loss" && !gapped && counted && q > 0)
                {
                    double before = closed - later, avg = cost / q, fees = 2 * SizingCommission * q;
                    peakLow = Math.Max(peakLow, before + td * (Open[0] - avg) * q * pv - fees);
                    peak = Math.Max(peak, before + td * ((td > 0 ? High[0] : Low[0]) - avg) * q * pv - fees);
                }
                later -= profit;
                g = h;
            }
            tradesAtLastBar = SystemPerformance.AllTrades.Count;
            if (LiquidationThreshold > 0)  // the threshold Apex shows: the highest equity is at least it + the trail
            {
                peak = Math.Max(peak, LiquidationThreshold - AccountStart + EvalTrail);
                peakLow = Math.Max(peakLow, LiquidationThreshold - AccountStart + EvalTrail);
            }
            DayLedger(start, closed);
            int flatBy = FlatBy(Time[0]);
            bool inRth = tMin >= NoiseEngine.RthOpen && endMin <= NoiseEngine.RthClose;

            // the evaluation's target: passed only on realized net profit
            if (!passed && EvalTarget > 0 && closed >= EvalTarget)
            {
                passed = true;
                Print("C: evaluation target reached on realized net profit " + F0(closed) + " at " + Ts(start) + "; no more entries.");
            }
            if (d == 0) mustClose = false;
            if (d == 0 && entryOrder != null && !cancelSent && (entryPartFilled || endMin >= flatBy))
            {
                // the guard stays until NinjaTrader confirms the cancellation (or a fill or a rejection)
                Print("C: cancelling the entry's unfilled " + (entryPartFilled ? "remainder" : "order") + " at " + Ts(start) +
                      (entryPartFilled ? " (the position closed before it filled)" : " (the flat time)") + ".");
                cancelSent = true;
                CancelOrder(entryOrder);
            }
            if (d != 0 && mustClose)
            {
                Print(Time[0] + "  the position is closed again at market after a rejected order.");
                Flatten(d, "Close: retry");
                Finish(signal, start, "open position");
                return;
            }
            bool openPast = EvalTarget > 0 && d != 0 && closed + now >= EvalTarget + 25;
            if (!PassOnRealizedOnly && openPast)
                passed = true;  // the earlier rule: the open profit alone marked the pass
            if (passed || openPast)
            {
                if (d != 0) Flatten(d, "Evaluation target");
                Finish(signal, start, passed ? "evaluation passed" : "open position");
                return;
            }
            if (d != 0 && (endMin >= flatBy || !inRth || tMin == NoiseEngine.RthOpen))
            {
                Flatten(d, "Flat " + NoiseEngine.Hhmm(Math.Min(flatBy, NoiseEngine.RthClose)));
                Finish(signal, start, "open position");
                return;
            }
            if (d != 0)
            {
                ManagePosition(d, closed);
                Finish(signal, start, "open position");
                return;
            }

            // flat: reset, then a new entry on a fresh qualifying check if the account allows it
            plannedStopPts = rPts = bestPx = lastStop = double.NaN;
            locked = false;
            if (signal != 0)
            {
                if (SignalsFromModel && engine.Orders.Count == nOrders)
                    Refuse(start, signal, note == "in a trade" ? "the model's hypothetical position" :
                                          note == "loser limit" ? "the model's loser limit" : "the model gave no order");
                else
                    TryEnter(start, signal, closed, endMin, flatBy);
            }
            Finish(0, start, "");
        }

        void Finish(int signal, DateTime start, string why)
        {
            if (signal != 0) Refuse(start, signal, why);
            SaveAccount();
            Draw.TextFixed(this, "c_dash", Dashboard(), TextPosition.TopRight);
        }

        void TryEnter(DateTime start, int dir, double closed, int endMin, int flatBy)
        {
            if (entryOrder != null) { Refuse(start, dir, "pending entry order"); return; }
            if (endMin >= flatBy) { Refuse(start, dir, "after the flat time"); return; }
            if (dayLosers >= MaxLosingPositions) { Refuse(start, dir, "losing positions today"); return; }
            if (State == State.Realtime && PositionAccount != null && PositionAccount.MarketPosition != MarketPosition.Flat)
            {
                Refuse(start, dir, "the account holds a position the strategy does not");
                return;
            }
            // B's bracket for this check: expected fill one tick through the close, stop the closer of the line and 25
            // points, take-profit 1.5 noise units
            double expected = Close[0] + dir * TickSize;
            double line = dir > 0 ? engine.Upper * (1 - StopBuffer * engine.Sigma) : engine.Lower * (1 + StopBuffer * engine.Sigma);
            double stop = Tighter(dir, line, expected - dir * CapPoints);
            double target = expected * (1 + dir * TakeProfit * engine.Sigma);
            double stopPts = StopTicks(dir * (expected - stop)) * TickSize;
            if (stopPts > CapPoints + 1e-9) stopPts = Math.Floor(CapPoints / TickSize + 1e-9) * TickSize;
            double rpc = RiskPerContract(stopPts);
            double room = closed - (peak - EvalTrail + AccountReserve);
            double dayNet = closed - dayStartEq;
            double dayRoom = DailyLossBackstop + dayNet;
            double roomBudget = room * ReserveRoomShare;
            double budget = Math.Min(MaxRisk, Math.Min(roomBudget, dayRoom));
            int qty = (int)Math.Min(MaxContracts, Math.Floor(budget / rpc + 1e-9));
            if (qty < 1)
            {
                if (roomBudget < rpc)
                    Refuse(start, dir, "account reserve room", "room " + F0(room) + ", usable " + F0(roomBudget) +
                           ", one contract " + F0(rpc));
                else
                    Refuse(start, dir, dayRoom < rpc ? "daily backstop" : "risk budget");
                return;
            }
            string name = dir > 0 ? LongName : ShortName;
            SetStopLoss(name, CalculationMode.Ticks, stopPts / TickSize, false);
            double tpPts = dir * (target - expected);
            if (EvalTarget > 0)
            {
                double evalPts = (EvalTarget + 25 - closed + 2 * SizingCommission * qty) / (qty * pv);
                if (evalPts < tpPts) tpPts = evalPts;
            }
            SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Ceiling(tpPts / TickSize - 1e-7)));
            Order o = dir > 0 ? EnterLong(qty, name) : EnterShort(qty, name);
            if (o != null && o.OrderState != OrderState.Filled && o.OrderState != OrderState.Rejected &&
                o.OrderState != OrderState.Cancelled)
                entryOrder = o;
            plannedStopPts = stopPts;
            entries++;
            sessEntries++;
            sinceLastEntry.Clear();
            lastEntrySignal = start;
            if (CheckLines)
                Print("C check " + Ts(start) + " " + (dir > 0 ? "long" : "short") + ": entry sent, " + qty + " MNQ, stop " +
                      F0(stopPts) + " points, planned risk " + F0(qty * rpc));
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
            if (!locked && d * (bestPx - avg) >= LockAtPoints) locked = true;

            // B's stop: the noise line, the 25-point cap from the fill, the lock
            double stop = double.NaN;
            if (!double.IsNaN(engine.Upper))
                stop = d > 0 ? engine.Upper * (1 - StopBuffer * engine.Sigma) : engine.Lower * (1 + StopBuffer * engine.Sigma);
            stop = Tighter(d, stop, avg - d * CapPoints);
            if (locked) stop = Tighter(d, stop, avg + d * LockPlusPoints);
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
            if (!double.IsNaN(engine.Sigma))
                tp = avg * (1 + d * TakeProfit * engine.Sigma);
            if (EvalTarget > 0)
            {
                double et = PriceForEquity(closed, EvalTarget + 25);
                if (double.IsNaN(tp) || (d > 0 && et < tp) || (d < 0 && et > tp)) tp = et;
            }
            if (!double.IsNaN(tp))
                SetProfitTarget(name, CalculationMode.Price, RoundStop(d, tp));
        }

        static double Tighter(int d, double a, double b)
        {
            if (double.IsNaN(a)) return b;
            if (double.IsNaN(b)) return a;
            return d > 0 ? Math.Max(a, b) : Math.Min(a, b);
        }

        void Flatten(int d, string why)
        {
            if (d > 0) ExitLong(why, ""); else if (d < 0) ExitShort(why, "");
        }

        double RoundStop(int d, double price)
        {
            double n = price / TickSize;
            return (d > 0 ? Math.Ceiling(n - 1e-7) : Math.Floor(n + 1e-7)) * TickSize;
        }

        double StopTicks(double points)
        {
            return Math.Max(1, Math.Floor(points / TickSize + 1e-7));
        }

        // the position a trade record belongs to: its entry order (a position filled in parts has several records)
        static string PositionKey(Trade tr)
        {
            return tr.Entry.Order != null && !string.IsNullOrEmpty(tr.Entry.Order.OrderId)
                ? "order " + tr.Entry.Order.OrderId : tr.Entry.Time.Ticks + "|" + tr.Entry.Name;
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time,
                                              ErrorCode error, string comment)
        {
            // the pending entry: until it is filled, cancelled or rejected, no other entry is sent
            if (order.Name == LongName || order.Name == ShortName)
            {
                if (orderState == OrderState.Filled || orderState == OrderState.Cancelled || orderState == OrderState.Rejected)
                {
                    if (entryOrder == null || entryOrder == order)
                    {
                        if (orderState == OrderState.Cancelled)
                            Print("C: the entry order's cancellation is confirmed.");
                        entryOrder = null;
                        entryPartFilled = cancelSent = false;
                    }
                }
                else
                {
                    // working, part filled, or a cancel pending: the order is live until a final state is confirmed
                    if (entryOrder != order) cancelSent = false;
                    entryOrder = order;
                    if (orderState == OrderState.PartFilled) entryPartFilled = true;
                }
            }
            if (orderState != OrderState.Rejected) return;
            Print(Time[0] + "  ORDER REJECTED: " + order.Name + " (" + comment + ").");
            int d = Dir;
            if (d == 0) return;  // a rejected entry: no position, and no hypothetical one
            bool ours = order.Name == "Close: rejected" || order.Name == "Close: retry";
            mustClose = true;  // never left without protection: closed now, and again at each bar until flat
            if (!ours) Flatten(d, "Close: rejected");
        }

        string Dashboard()
        {
            int d = Dir;
            string s = "MNQ Momentum C, " + (PlaceOrders ? "orders ON" : "orders OFF") + "\n";
            s += "Equity since start " + F0(Closed()) + ", highest " + F0(peak) + ", liquidation line " + F0(peak - EvalTrail) +
                 ", reserve line " + F0(peak - EvalTrail + AccountReserve) + (passed ? " - TARGET REACHED (realized), no more trades" : "") + "\n";
            s += "Today: " + dayLosers + " losing positions, net " + F0(Closed() - dayStartEq) + "\n";
            s += (d != 0 ? "Position " + (d > 0 ? "LONG " : "SHORT ") + Position.Quantity + " @ " + F0(Position.AveragePrice) +
                  ", stop " + F0(lastStop) + (locked ? " (locked)" : "") : "Flat") +
                 (notSent.Length > 0 ? "\nLast signal not taken: " + notSent : "");
            return s;
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 1, GroupName = "1. Trading")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 10000.0)]
        [Display(Name = "Max planned loss per position, $ (costs included)", Order = 2, GroupName = "1. Trading")]
        public double MaxRisk { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max contracts", Order = 3, GroupName = "1. Trading")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 20.0)]
        [Display(Name = "Commission per side per contract, $ (for sizing)", Order = 4, GroupName = "1. Trading")]
        public double SizingCommission { get; set; }

        [NinjaScriptProperty]
        [Range(0, 40)]
        [Display(Name = "Sizing reserve, ticks (2 at entry + 2 at the stop)", Order = 5, GroupName = "1. Trading")]
        public int ReserveTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Flat by, minute of day New York (955 = 15:55)", Order = 6, GroupName = "1. Trading")]
        public int FlatMinute { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output: a line for every check past a line", Order = 7, GroupName = "1. Trading")]
        public bool CheckLines { get; set; }

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
        [Range(0.1, 1.0)]
        [Display(Name = "Share of the room above the reserve an entry may risk (0.5 as tested)", Order = 11, GroupName = "2. Account")]
        public double ReserveRoomShare { get; set; }

        [NinjaScriptProperty]
        [Range(1000.0, 1000000.0)]
        [Display(Name = "Account starting balance, $", Order = 6, GroupName = "2. Account")]
        public double AccountStart { get; set; }

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
        [Range(0.0, 1000000.0)]
        [Display(Name = "Live: the account's liquidation threshold now, $ (0 = unknown)", Order = 10, GroupName = "2. Account")]
        public double LiquidationThreshold { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Skip dates (yyyy-MM-dd,...)", Order = 1, GroupName = "3. Entries (B's)")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed dates (yyyy-MM-dd,...)", Order = 2, GroupName = "3. Entries (B's)")]
        public string FedDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Comparison only: signals from B's model position (the earlier coupling)", Order = 1, GroupName = "4. Comparison")]
        public bool SignalsFromModel { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Pass only on realized profit (off: the earlier rule, comparison only)", Order = 2, GroupName = "4. Comparison")]
        public bool PassOnRealizedOnly { get; set; }
        #endregion
    }
}
