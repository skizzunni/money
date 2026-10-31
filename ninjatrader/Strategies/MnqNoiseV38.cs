// MNQ Noise-Area Momentum v3.8 for NinjaTrader 8: the 50K evaluation version (docs/CANDIDATE_E50.md).
//
// The same rules as pine/mnq_noise_momentum.pine v3.8 and mnqbot/noise.py with those settings, in one file:
//   * the noise area: at each half-hour check 10:00-15:00 New York, the day's open (and the previous close) plus or
//     minus the average move from the 09:30 open to that time over the last 14 sessions;
//   * a check that closes above the upper line buys 1 MNQ at market, below the lower line sells, unless a filter says
//     no: no entries after the 15:00 check; after a big day (range over 1.5x the 10-session average) none in its
//     direction; none after a calm stretch (the last 10 sessions' average range under 0.7x the last 40's); the close
//     must sit in the top (bottom) 35% of the day's range so far; no shorts while yesterday's close is above its
//     50-session average; no shorts before 14:00 on Fed days; no trades on holidays and half days;
//   * the stop, sent with the entry: the closer of 0.24 noise units past the line and $260 from the fill (the whole
//     position), then moved with the line at every bar close, never back toward the price; once price has gone
//     0.35 x the max loss in the trade's favour, the stop moves to the entry + 2.5 points;
//   * a take-profit 2 noise units from the fill;
//   * no limit on trades a day, but no new trade may risk more than what is left of $900 lost today: when not even a
//     full trade fits, 1 contract with its stop cut to the room left, if that leaves at least 20 points;
//   * everything closed at market at 16:00.
// Orders follow NinjaTrader's execution as tested (docs/PARITY.md): the bracket goes in with the entry in ticks from
// the fill; a stop the bar's close has already passed is a market exit at the next bar's open ("Stop passed"); the
// 16:00 exit is a market order filled at the next bar's open. ninjatrader/tests/Sim runs this file on bars and
// tests/test_ninjatrader_v38.py holds it to the Python model trade for trade.
//
// Setup: an MNQ chart of 5 or 30 minutes (any length that divides 30), Trading hours "CME US Index Futures ETH" (so a
// bar starts at 16:00 for the 16:00 exit to fill in), Days to load 120 or more (the noise needs 14 full sessions, the
// trend filter 50, the calm filter 40), Calculate On bar close. Written in C# 5 for NinjaTrader 8's compiler.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public sealed class V38Settings
    {
        public int Lookback = 14;
        public int Qty = 1;
        public double Tick = 0.25, PointValue = 2.0, CommissionPerSide = 0.62;
        public int SlippageTicks = 1;
        public double StopBuffer = 0.24, MaxLoss = 260.0, TakeProfit = 2.0, LockAt = 0.35, LockPlus = 2.5;
        public double DailyLoss = 900.0, SqueezeMin = 20.0, RangePosMin = 0.65;
        public int LastEntryEnd = 900, BigDayN = 10, CalmShort = 10, CalmLong = 40, TrendN = 50;
        public double BigDayK = 1.5, CalmK = 0.7;
        public bool FedNoShorts = true, TightenOnly = true, RoundPrices = true;
        public string SkipDates = "", FedDates = "";
        // funded growth (pine v3.6's sizing; off in the evaluation): the trade after a loser risks AfterLossMaxLoss;
        // an end-of-day trailing drawdown from TrailFrom that stops at the starting balance; one more contract per
        // ProfitStep of closed profit since then, up to MaxContracts; each trade sized by its own stop
        public double AfterLossMaxLoss = 0.0, TrailDD = 0.0, ProfitStep = 0.0;
        public int MaxContracts = 0;
        public bool SizeByOwnStop = false;
        public string TrailFrom = "";
    }

    public sealed class V38Trade
    {
        public int Direction, Qty, EntryBar, ExitBar;
        public double Entry, Exit, Pnl;
        public string Reason;
    }

    // The rules, with no NinjaTrader code in them: mnqbot/noise.py with v3.8's settings and nt_execution,
    // round_prices and target_on_fill_bar on. Feed finished bars in order with their START time in New York time.
    public sealed class V38Engine
    {
        public const int NChecks = 12, FirstCheck = 600, LastCheck = 930, Step = 30, RthOpen = 570, RthClose = 960;
        public const int FedCutoff = 840;
        readonly V38Settings s;
        readonly int minutes;
        readonly double slip;
        readonly double[] ring;
        double[] today = NewToday();
        int filled, slot;
        double dayOpen = double.NaN, prevClose = double.NaN, lastRthClose = double.NaN, lastBarClose = double.NaN;
        double dayHi = double.NaN, dayLo = double.NaN;
        readonly List<double> dayRanges = new List<double>(), dayCloses = new List<double>();
        readonly List<int> dayDirs = new List<int>();
        int blockDir, trend;
        bool calm;
        int pendingKind, pendingDir;  // 1: an entry in pendingDir, 3: the 16:00 exit; filled at the next bar's open
        double estPx = double.NaN;
        int qNext, qTrade;
        double mlNext, mlTrade;
        double brStopNext, brTpNext, brStopTrade, brTpTrade;  // the bracket: points from the fill
        string brWhyNext = "", brWhyTrade = "";
        double held = double.NaN, fav = double.NaN;
        string heldWhy = "";
        int consec;                       // losing trades in a row, across days
        double equity;                    // the closed P/L so far
        double trailBase = double.NaN, trailPeak = double.NaN;

        public readonly List<V38Trade> Trades = new List<V38Trade>();
        public int Bar = -1;
        public int Position, EntryBar;
        public double EntryPrice;
        public double Upper = double.NaN, Lower = double.NaN, Sigma = double.NaN;
        public bool Locked, SkipToday, FedToday;
        public double DayPnl;
        public int NewEntry;          // this bar's signal: +1 / -1 to send now (0: none)
        public int NewQty;
        public double NewStopPts, NewTpPts;
        public bool FlatNow;          // this bar is the 16:00 bar: close at market
        public string Note = "";      // what this bar's check found, for the dashboard

        public V38Engine(V38Settings settings, int barMinutes)
        {
            if (barMinutes <= 0 || 30 % barMinutes != 0)
                throw new ArgumentException("bar length must divide 30 minutes, not " + barMinutes);
            s = settings;
            minutes = barMinutes;
            slip = s.SlippageTicks * s.Tick;
            ring = new double[s.Lookback * NChecks];
            for (int i = 0; i < ring.Length; i++)
                ring[i] = double.NaN;
        }

        static double[] NewToday()
        {
            double[] t = new double[NChecks];
            for (int i = 0; i < NChecks; i++)
                t[i] = double.NaN;
            return t;
        }

        public bool Ready { get { return filled >= s.Lookback && !double.IsNaN(prevClose); } }
        public int SessionsLoaded { get { return Math.Min(filled, s.Lookback); } }

        double LineStop(int d)
        {
            return d > 0 ? Upper * (1 - s.StopBuffer * Sigma) : Lower * (1 + s.StopBuffer * Sigma);
        }

        // a long's stop and take-profit both round up (the stop toward the price, the take-profit away from it), a
        // short's both down: a loss never goes past the max loss, a target never takes less than tested
        public double OnGrid(int d, double price)
        {
            if (!s.RoundPrices || double.IsNaN(price))
                return price;
            double n = price / s.Tick;
            return (d > 0 ? Math.Ceiling(n - 1e-7) : Math.Floor(n + 1e-7)) * s.Tick;
        }

        double TicksDown(double points)
        {
            return s.RoundPrices ? Math.Max(s.Tick, Math.Floor(points / s.Tick + 1e-7) * s.Tick) : points;
        }

        double TicksUp(double points)
        {
            return s.RoundPrices && !double.IsNaN(points) ? Math.Max(s.Tick, Math.Ceiling(points / s.Tick - 1e-7) * s.Tick) : points;
        }

        static bool InList(string list, DateTime t)
        {
            return !string.IsNullOrEmpty(list) && list.Contains(t.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        }

        // The stop that rests for the next bar, measured from entry (the real fill): the closest of the line stop,
        // the max loss and the lock, on the tick grid, never back toward the price. NaN when flat.
        public double PeekStop(double entry)
        {
            if (Position == 0 || double.IsNaN(Upper))
                return double.NaN;
            int p = Position;
            double line = LineStop(p);
            double cap = entry - p * mlTrade / qTrade / s.PointValue;
            if ((p > 0 && cap > line) || (p < 0 && cap < line)) line = cap;
            if (Locked)
            {
                double lk = entry + p * s.LockPlus;
                if ((p > 0 && lk > line) || (p < 0 && lk < line)) line = lk;
            }
            line = OnGrid(p, line);
            if (s.TightenOnly && !double.IsNaN(held) && ((p > 0 && held > line) || (p < 0 && held < line)))
                line = held;
            return line;
        }

        public double PeekTarget(double entry)
        {
            if (Position == 0 || s.TakeProfit <= 0 || double.IsNaN(Sigma))
                return double.NaN;
            return OnGrid(Position, entry * (1 + Position * s.TakeProfit * Sigma));
        }

        public int TradeQty { get { return qTrade; } }

        void Open(int i, double o, int d)
        {
            Position = d;
            EntryPrice = o + d * slip;
            EntryBar = i;
            qTrade = qNext;
            mlTrade = mlNext;
            brStopTrade = brStopNext;
            brTpTrade = brTpNext;
            brWhyTrade = brWhyNext;
        }

        void Close(int i, double price, string reason)
        {
            double pnl = Position * (price - EntryPrice) * qTrade * s.PointValue - 2 * s.CommissionPerSide * qTrade;
            V38Trade t = new V38Trade();
            t.Direction = Position; t.Qty = qTrade; t.EntryBar = EntryBar; t.Entry = EntryPrice;
            t.ExitBar = i; t.Exit = price; t.Reason = reason; t.Pnl = pnl;
            Trades.Add(t);
            DayPnl += pnl;
            equity += pnl;
            if (pnl < 0 && reason != "Session ended") consec++;
            else if (pnl >= 0) consec = 0;
            Position = 0;
            Locked = false;
            held = double.NaN;
            heldWhy = "";
            fav = double.NaN;
        }

        bool StudyOk(int d, int end, double c)
        {
            if (s.LastEntryEnd > 0 && end > s.LastEntryEnd) { Note = "after the last entry check"; return false; }
            if (blockDir != 0 && d == blockDir) { Note = "after a big day, not its way"; return false; }
            if (s.TrendN > 0 && d < 0 && trend == 1) { Note = "no shorts in the uptrend"; return false; }
            if (calm) { Note = "calm stretch"; return false; }
            if (s.RangePosMin > 0 && dayHi > dayLo)
            {
                double rp = d > 0 ? (c - dayLo) / (dayHi - dayLo) : (dayHi - c) / (dayHi - dayLo);
                if (rp < s.RangePosMin) { Note = "not near the day's extreme"; return false; }
            }
            return true;
        }

        public void OnBar(DateTime nyStart, double o, double h, double l, double c)
        {
            int i = ++Bar;
            int tMin = nyStart.Hour * 60 + nyStart.Minute;
            int end = tMin + minutes;
            bool inRth = tMin >= RthOpen && end <= RthClose;
            NewEntry = 0;
            FlatNow = false;
            Note = "";

            if (pendingKind != 0)  // market orders from the last bar fill at this bar's open
            {
                int kind = pendingKind, d = pendingDir;
                pendingKind = 0;
                if (kind == 3 && Position != 0)
                    Close(i, o - Position * slip, "16:00 close");
                else if (kind == 1 && Position == 0)
                    Open(i, o, d);
            }

            if (Position != 0 && !double.IsNaN(Upper))  // the resting stop, then the take-profit
            {
                int p = Position;
                double line = LineStop(p);
                string reason = "Back inside";
                double basePx = EntryBar != i ? EntryPrice : estPx;
                double cap = basePx - p * mlTrade / qTrade / s.PointValue;
                if ((p > 0 && cap > line) || (p < 0 && cap < line)) { line = cap; reason = "Max loss"; }
                if (Locked)
                {
                    double lk = EntryPrice + p * s.LockPlus;
                    if ((p > 0 && lk > line) || (p < 0 && lk < line)) { line = lk; reason = "Lock"; }
                }
                if (EntryBar == i) { line = EntryPrice - p * brStopTrade; reason = brWhyTrade; }  // the bracket
                else line = OnGrid(p, line);
                if (s.TightenOnly)
                {
                    if (EntryBar != i && ((p > 0 && held > line) || (p < 0 && held < line))) { line = held; reason = heldWhy; }
                    held = line;
                    heldWhy = reason;
                }
                bool hit;
                double price;
                if (EntryBar != i && p * (lastBarClose - line) <= 0)
                {
                    hit = true; price = o - p * slip; reason = "Stop passed";  // sent at the last close, filled now
                }
                else if (EntryBar == i)
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = (p > 0 ? Math.Min(o, line) : Math.Max(o, line)) - p * slip;
                }
                else if ((p > 0 && o <= line) || (p < 0 && o >= line))
                {
                    hit = true; price = o - p * slip;
                }
                else
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = line - p * slip;
                }
                if (hit)
                    Close(i, price, reason);
                else if (s.TakeProfit > 0)
                {
                    double tp = EntryBar == i ? EntryPrice + p * brTpTrade
                                              : OnGrid(p, EntryPrice * (1 + p * s.TakeProfit * Sigma));
                    if ((p > 0 && h >= tp + s.Tick) || (p < 0 && l <= tp - s.Tick))
                        Close(i, tp, "Target");
                }
            }

            if (Position != 0 && !Locked && s.LockAt > 0 && s.MaxLoss > 0)  // the lock arms from the next bar
            {
                double trigger = s.LockAt * mlTrade / qTrade / s.PointValue;
                double x = Position > 0 ? h : l;
                fav = double.IsNaN(fav) ? x : (Position > 0 ? Math.Max(fav, x) : Math.Min(fav, x));
                Locked = Position * (fav - EntryPrice) >= trigger;
            }

            if (Position != 0 && (!inRth || tMin == RthOpen))  // a session that ended early
                Close(i, c - Position * slip, "Session ended");

            if (tMin == RthOpen)
            {
                blockDir = 0;
                DayPnl = 0;
                if (s.TrailDD > 0 && string.CompareOrdinal(nyStart.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), s.TrailFrom ?? "") >= 0)
                {
                    if (double.IsNaN(trailBase)) trailBase = trailPeak = equity;  // yesterday's end-of-day equity
                    trailPeak = Math.Max(trailPeak, equity);
                }
                if (s.CalmK > 0 && dayRanges.Count >= s.CalmLong)
                    calm = Avg(dayRanges, s.CalmShort) < s.CalmK * Avg(dayRanges, s.CalmLong);
                if (s.TrendN > 0 && dayCloses.Count >= s.TrendN)
                {
                    double ma = Avg(dayCloses, s.TrendN), last = dayCloses[dayCloses.Count - 1];
                    trend = last > ma ? 1 : last < ma ? -1 : 0;
                }
                if (s.BigDayK > 0 && dayRanges.Count >= s.BigDayN &&
                    dayRanges[dayRanges.Count - 1] > s.BigDayK * Avg(dayRanges, s.BigDayN))
                    blockDir = dayDirs[dayDirs.Count - 1];
                dayHi = dayLo = double.NaN;
                prevClose = lastRthClose;
                dayOpen = o;
                Upper = Lower = Sigma = double.NaN;
                today = NewToday();
                SkipToday = InList(s.SkipDates, nyStart);
                FedToday = s.FedNoShorts && InList(s.FedDates, nyStart);
            }
            if (inRth)
            {
                lastRthClose = c;
                dayHi = double.IsNaN(dayHi) ? h : Math.Max(dayHi, h);
                dayLo = double.IsNaN(dayLo) ? l : Math.Min(dayLo, l);
            }

            if (inRth && !double.IsNaN(dayOpen) && end >= FirstCheck && end <= LastCheck && (end - FirstCheck) % Step == 0)
            {
                int k = (end - FirstCheck) / Step;
                today[k] = Math.Abs(c / dayOpen - 1);
                Note = "not ready";
                if (filled >= s.Lookback && !double.IsNaN(prevClose))
                {
                    double sum = 0.0;
                    for (int d = 0; d < s.Lookback; d++)  // same summation order as the Python and Pine loops
                        sum += ring[d * NChecks + k];
                    Sigma = sum / s.Lookback;
                    Upper = Math.Max(dayOpen, prevClose) * (1 + Sigma);
                    Lower = Math.Min(dayOpen, prevClose) * (1 - Sigma);
                    bool shortOk = !(FedToday && end < FedCutoff);
                    int dir = 0;
                    Note = c > Upper || c < Lower ? "" : "inside the noise area";
                    if (SkipToday) Note = "holiday / half day";
                    else if (Position != 0) Note = "in a trade";
                    else if (c > Upper && StudyOk(1, end, c)) dir = 1;
                    else if (c < Lower && !shortOk) Note = "Fed day: no shorts before 14:00";
                    else if (c < Lower && StudyOk(-1, end, c)) dir = -1;
                    if (dir != 0)
                        Entry(dir, c);
                }
            }

            if (inRth && end == RthClose)
            {
                if (Position != 0)
                {
                    pendingKind = 3;
                    FlatNow = true;
                }
                if (!double.IsNaN(dayOpen) && !double.IsNaN(dayHi))
                {
                    dayRanges.Add((dayHi - dayLo) / dayOpen);
                    dayDirs.Add(c > dayOpen ? 1 : c < dayOpen ? -1 : 0);
                    dayCloses.Add(c);
                }
                bool complete = !double.IsNaN(dayOpen);
                for (int k = 0; k < NChecks && complete; k++)
                    complete = !double.IsNaN(today[k]);
                if (complete)
                {
                    Array.Copy(today, 0, ring, slot * NChecks, NChecks);
                    slot = (slot + 1) % s.Lookback;
                    filled++;
                }
                dayOpen = double.NaN;
            }
            lastBarClose = c;
        }

        // What a new trade may risk: the rest of today's loss limit and the room above the trailing floor
        double MoneyRoom()
        {
            double room = double.PositiveInfinity;
            if (s.DailyLoss > 0)
                room = s.DailyLoss + DayPnl;
            if (s.TrailDD > 0 && !double.IsNaN(trailPeak))
            {
                double floor = Math.Min(trailPeak - s.TrailDD, trailBase);  // it stops at the starting balance
                room = Math.Min(room, equity - floor);
            }
            return room;
        }

        public double TrailFloorRoom { get { return s.TrailDD > 0 && !double.IsNaN(trailPeak) ? equity - Math.Min(trailPeak - s.TrailDD, trailBase) : double.NaN; } }

        void Entry(int d, double c)
        {
            int q = s.Qty;
            bool afterLoss = consec > 0;
            double ml = afterLoss && s.AfterLossMaxLoss > 0 ? s.AfterLossMaxLoss : s.MaxLoss;
            if (s.ProfitStep > 0 && !double.IsNaN(trailBase))  // a contract more per step of profit
            {
                int qUp = q + (int)Math.Floor(Math.Max(0.0, equity - trailBase) / s.ProfitStep);
                if (s.MaxContracts > 0) qUp = Math.Min(qUp, s.MaxContracts);
                ml = ml / q * qUp;
                q = qUp;
            }
            if ((s.DailyLoss > 0 || s.TrailDD > 0) && ml > 0)  // the loss budget
            {
                double costs = 2 * s.CommissionPerSide + 2 * slip * s.PointValue;
                double perC = ml / q + costs;
                if (s.SizeByOwnStop)  // a contract's risk is its initial stop: the line's or the max loss
                {
                    double pts = Math.Min(Math.Abs(c + d * slip - LineStop(d)), ml / q / s.PointValue);
                    perC = pts * s.PointValue + costs;
                }
                double room = MoneyRoom();
                int fit = double.IsInfinity(room) ? q : (int)Math.Floor(room / perC + 1e-9);
                if (fit < 1 && s.SqueezeMin > 0 && !double.IsInfinity(room) && room - costs >= s.SqueezeMin * s.PointValue)
                {
                    fit = 1; q = 1; ml = room - costs;  // 1 contract, the stop cut to the room left
                }
                if (fit < 1) { Note = "today's loss budget is used up"; return; }
                if (fit < q) { ml = ml / q * fit; q = fit; }
            }
            Note = d > 0 ? "BUY" : "SELL";
            pendingKind = 1;
            pendingDir = d;
            qNext = q;
            mlNext = ml;
            estPx = c + d * slip;
            double stop = LineStop(d), atLine = stop;
            double cap = estPx - d * ml / q / s.PointValue;
            stop = d > 0 ? Math.Max(stop, cap) : Math.Min(stop, cap);
            double tp = s.TakeProfit > 0 ? estPx * (1 + d * s.TakeProfit * Sigma) : double.NaN;
            brStopNext = TicksDown(d * (estPx - stop));
            brTpNext = TicksUp(d * (tp - estPx));
            brWhyNext = stop != atLine ? "Max loss" : "Back inside";
            NewEntry = d;
            NewQty = q;
            NewStopPts = brStopNext;
            NewTpPts = brTpNext;
        }

        static double Avg(List<double> x, int n)
        {
            double sum = 0.0;
            for (int k = x.Count - n; k < x.Count; k++)
                sum += x[k];
            return sum / n;
        }
    }

    public class MnqNoiseV38 : Strategy
    {
        const string LongName = "Long", ShortName = "Short";
        const string SkipDefault =
            "2025-01-01,2025-01-09,2025-01-20,2025-02-17,2025-04-18,2025-05-26,2025-06-19,2025-07-03,2025-07-04,2025-09-01," +
            "2025-11-27,2025-11-28,2025-12-24,2025-12-25," +
            "2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07," +
            "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26," +
            "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24";
        const string FedDefault =
            "2025-01-29,2025-03-19,2025-05-07,2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10," +
            "2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29,2026-09-16,2026-10-28,2026-12-09," +
            "2027-01-27,2027-03-17,2027-04-28,2027-06-09,2027-07-28,2027-09-15,2027-10-27,2027-12-08";
        V38Engine engine;
        TimeZoneInfo newYork;
        int minutes;
        bool badChart;
        int nTrades;
        double net, peak, maxDd, worstDay, dayNet;
        DateTime lastDay = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqNoiseV38";
                Description = "MNQ Noise-Area Momentum v3.8: 1 MNQ, $260 max loss per trade, $900 a day, take-profit 2 noise units (50K evaluation).";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                Contracts = 1;
                MaxLoss = 260;
                DailyLoss = 900;
                TakeProfit = 2.0;
                LockAt = 0.35;
                LockPlus = 2.5;
                StopBuffer = 0.24;
                SqueezeMin = 20;
                LastEntry = "15:00";
                BigDayK = 1.5;
                CalmK = 0.7;
                RangePos = 0.65;
                TrendSessions = 50;
                FedNoShorts = true;
                SkipDates = SkipDefault;
                FedDates = FedDefault;
                PlaceOrders = true;
                AfterLossMaxLoss = 0;
                TrailDD = 0;
                TrailFrom = "";
                ProfitStep = 0;
                MaxContracts = 15;
                SizeByOwnStop = false;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                minutes = BarsPeriod.Value;
                badChart = BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || minutes <= 0 || 30 % minutes != 0;
                V38Settings st = new V38Settings();
                st.Qty = Contracts; st.MaxLoss = MaxLoss; st.DailyLoss = DailyLoss; st.TakeProfit = TakeProfit;
                st.LockAt = LockAt; st.LockPlus = LockPlus; st.StopBuffer = StopBuffer; st.SqueezeMin = SqueezeMin;
                st.LastEntryEnd = LastEntry == "15:30" ? 930 : 900;
                st.BigDayK = BigDayK; st.CalmK = CalmK; st.RangePosMin = RangePos; st.TrendN = TrendSessions;
                st.FedNoShorts = FedNoShorts; st.SkipDates = SkipDates; st.FedDates = FedDates;
                st.AfterLossMaxLoss = AfterLossMaxLoss; st.TrailDD = TrailDD; st.TrailFrom = TrailFrom ?? "";
                st.ProfitStep = ProfitStep; st.MaxContracts = MaxContracts; st.SizeByOwnStop = SizeByOwnStop;
                st.Tick = TickSize;
                st.PointValue = Instrument.MasterInstrument.PointValue;
                if (!badChart)
                    engine = new V38Engine(st, minutes);
                Print("MnqNoiseV38: " + Instrument.FullName + ", " + minutes + " " + BarsPeriod.BarsPeriodType + ", " + Contracts +
                      " MNQ, max loss $" + MaxLoss + " a trade, $" + DailyLoss + " a day, take-profit " + TakeProfit +
                      (badChart ? "  -- use a minute chart whose length divides 30 (5 or 30)" : ""));
            }
            else if (State == State.Terminated && engine != null)
                Print("MnqNoiseV38 done: " + nTrades + " trades, net $" + net.ToString("0.00", CultureInfo.InvariantCulture) +
                      ", closed drawdown $" + maxDd.ToString("0.00", CultureInfo.InvariantCulture) +
                      ", worst day $" + worstDay.ToString("0.00", CultureInfo.InvariantCulture));
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || badChart || engine == null)
                return;
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            DateTime endNy = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified), platform, newYork);
            DateTime start = endNy.AddMinutes(-minutes);
            int before = engine.Trades.Count;
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            for (int k = before; k < engine.Trades.Count; k++)
                Tally(start, engine.Trades[k].Pnl);
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;

            if (real != 0 && engine.FlatNow)
            {
                Flatten(real, "Flat 16:00");
            }
            else if (real == 0 && engine.NewEntry != 0 && PlaceOrders)
            {
                // the bracket first, in ticks from the fill, so it is attached the moment the entry fills
                string name = engine.NewEntry > 0 ? LongName : ShortName;
                SetStopLoss(name, CalculationMode.Ticks, Math.Max(1, Math.Round(engine.NewStopPts / TickSize)), false);
                if (!double.IsNaN(engine.NewTpPts))
                    SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Round(engine.NewTpPts / TickSize)));
                if (engine.NewEntry > 0) EnterLong(engine.NewQty, name);
                else EnterShort(engine.NewQty, name);
            }
            else if (real != 0 && engine.Position == real)
            {
                // in a trade: the stop and the take-profit for the next bar, from the real fill
                double avg = Position.AveragePrice;
                double stop = engine.PeekStop(avg);
                string name = real > 0 ? LongName : ShortName;
                if (!double.IsNaN(stop))
                {
                    double px = Close[0];
                    if (State == State.Realtime)  // live: where the stop would trigger now, so it is never sent past it
                        px = real > 0 ? Math.Min(px, GetCurrentBid()) : Math.Max(px, GetCurrentAsk());
                    if ((real > 0 && stop >= px) || (real < 0 && stop <= px))
                        Flatten(real, "Stop passed");  // a stop can't rest there: the line moved past the price
                    else
                    {
                        SetStopLoss(name, CalculationMode.Price, stop, false);
                        double tp = engine.PeekTarget(avg);
                        if (!double.IsNaN(tp))
                            SetProfitTarget(name, CalculationMode.Price, tp);
                    }
                }
            }
            else if (real != 0 && engine.Position == 0)
                Flatten(real, "Model flat");  // the model closed (a fill elsewhere): don't hold an unmanaged position
            Dashboard(endNy);
        }

        void Flatten(int real, string why)
        {
            if (real > 0) ExitLong(why, "");
            else ExitShort(why, "");
        }

        void Tally(DateTime start, double pnl)  // the model's own results, for the Output window and the dashboard
        {
            DateTime day = start.Date;
            if (day != lastDay) { dayNet = 0; lastDay = day; }
            dayNet += pnl;
            worstDay = Math.Min(worstDay, dayNet);
            nTrades++;
            net += pnl;
            peak = Math.Max(peak, net);
            maxDd = Math.Max(maxDd, peak - net);
        }

        void Dashboard(DateTime endNy)
        {
            string txt = "MNQ Noise Momentum v3.8, " + Contracts + " MNQ\n" +
                         "Sessions of history: " + engine.SessionsLoaded + " / 14\n" +
                         (double.IsNaN(engine.Upper) ? "Lines: after the 10:00 check\n" :
                          "Upper / lower: " + engine.Upper.ToString("0.00", CultureInfo.InvariantCulture) + " / " +
                          engine.Lower.ToString("0.00", CultureInfo.InvariantCulture) + "\n") +
                         "Today P/L (model): $" + engine.DayPnl.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", room left $" + Math.Max(0, DailyLoss + engine.DayPnl).ToString("0", CultureInfo.InvariantCulture) + "\n" +
                         "Trades " + nTrades + ", net $" + net.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", drawdown $" + maxDd.ToString("0.00", CultureInfo.InvariantCulture) + "\n" +
                         (engine.Note.Length > 0 ? "Last check: " + engine.Note : "");
            Draw.TextFixed(this, "v38_dash", txt, TextPosition.TopRight);
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Contracts", Order = 1, GroupName = "1. Size and risk")]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Max loss per trade, $ (all contracts)", Order = 2, GroupName = "1. Size and risk")]
        public double MaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Max loss a day, $ (0 = off)", Order = 3, GroupName = "1. Size and risk")]
        public double DailyLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "After a losing trade: max loss per trade, $ (0 = the same)", Order = 5, GroupName = "1. Size and risk")]
        public double AfterLossMaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20000)]
        [Display(Name = "Trailing drawdown (end of day, stops at the start), $ (0 = off)", Order = 6, GroupName = "1. Size and risk")]
        public double TrailDD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Trailing drawdown and contract steps from date, yyyy-MM-dd (blank = the first bar)", Order = 7, GroupName = "1. Size and risk")]
        public string TrailFrom { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Add a contract per $ of profit (0 = off)", Order = 8, GroupName = "1. Size and risk")]
        public double ProfitStep { get; set; }

        [NinjaScriptProperty]
        [Range(0, 60)]
        [Display(Name = "Most contracts (with the contract steps; 0 = no limit)", Order = 9, GroupName = "1. Size and risk")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Size by the trade's own stop", Order = 10, GroupName = "1. Size and risk")]
        public bool SizeByOwnStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 200)]
        [Display(Name = "When the day's room is short: 1 contract, its stop cut to the room, if at least this many points (0 = no trade)", Order = 4, GroupName = "1. Size and risk")]
        public double SqueezeMin { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Take profit, noise units (0 = off)", Order = 1, GroupName = "2. Exits")]
        public double TakeProfit { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Lock: trigger, in max losses (0 = off)", Order = 2, GroupName = "2. Exits")]
        public double LockAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Lock: stop to the entry plus, points", Order = 3, GroupName = "2. Exits")]
        public double LockPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2)]
        [Display(Name = "Stop distance past the line, noise units", Order = 4, GroupName = "2. Exits")]
        public double StopBuffer { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Last check for new entries (15:00 or 15:30)", Order = 1, GroupName = "3. Filters")]
        public string LastEntry { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "After a big day: no trades its way if its range > this x the 10-session average (0 = off)", Order = 2, GroupName = "3. Filters")]
        public double BigDayK { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2)]
        [Display(Name = "Calm stretch: no trades if the 10-session average range < this x the 40-session one (0 = off)", Order = 3, GroupName = "3. Filters")]
        public double CalmK { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1)]
        [Display(Name = "Entries near the day's extreme: the close in the top this share of the day's range (0 = off)", Order = 4, GroupName = "3. Filters")]
        public double RangePos { get; set; }

        [NinjaScriptProperty]
        [Range(0, 250)]
        [Display(Name = "No shorts while the last close is above its average of this many sessions (0 = off)", Order = 5, GroupName = "3. Filters")]
        public int TrendSessions { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed days: no shorts before 14:00", Order = 6, GroupName = "3. Filters")]
        public bool FedNoShorts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "No trades on these dates (holidays, half days)", Order = 7, GroupName = "3. Filters")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed announcement dates", Order = 8, GroupName = "3. Filters")]
        public string FedDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 1, GroupName = "4. Orders")]
        public bool PlaceOrders { get; set; }
        #endregion
    }
}
