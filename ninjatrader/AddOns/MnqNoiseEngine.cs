// MNQ Noise Momentum: the trading rules, with no NinjaTrader code in them.
//
// The same rules as mnqbot/noise.py and pine/mnq_noise_momentum.pine (v1.6), bar for bar. The indicator
// (Indicators/MnqNoiseSignals.cs) and the strategy (Strategies/MnqNoiseMomentum.cs) feed it bars and act on what it
// decides. ninjatrader/tests checks it trade for trade against the Python bot.
//
// Feed it finished bars in order, with the bar's START time in New York time (NinjaTrader stamps bars with their end
// time; the wrappers subtract the bar length). The bar length must divide 30 minutes; use 5 minutes.
//
// Written in C# 5 (no $"" strings, no tuples) so NinjaTrader 8's compiler takes it.
using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.AddOns.MnqBot
{
    public sealed class NoiseSettings
    {
        public int Lookback = 14;            // sessions in the noise average
        public int Qty = 3;                  // contracts
        public double Tick = 0.25;
        public double PointValue = 2.0;      // MNQ
        public double CommissionPerSide = 0.62;
        public int SlippageTicks = 1;        // on every market fill
        public string SkipDates = NoiseEngine.SkipDatesDefault;
        public double StopBuffer = 0.24;     // the line stop sits this many noise units past the line
        public double MaxLoss = 350.0;       // $ for the whole position; 0 = off
        public string FedDates = NoiseEngine.FedDatesDefault;
        public bool FedNoShorts = true;      // Fed days: no shorts before 14:00
        public double TakeProfit = 1.5;      // noise units from the fill; 0 = off
        public double LockAt = 1.0;          // in max losses of profit; then the stop moves to entry + LockPlus
        public double LockPlus = 2.5;        // points
        public int MaxLosers = 4;            // no new entries after this many losers today; 0 = no limit
    }

    public sealed class NoiseTrade
    {
        public int Direction, Qty, EntryBar, ExitBar;
        public DateTime EntryTime, ExitTime;
        public double Entry, Exit, Pnl;
        public string Reason;
    }

    public sealed class NoiseOrder   // the bracket to send with an entry (NaN: none)
    {
        public int SignalBar, Direction;
        public double Expected, Stop, Target;
    }

    public sealed class NoiseEvent   // BUY, SELL, EXIT, TARGET, FLAT
    {
        public int Bar;
        public string Action;
    }

    public sealed class NoiseHeadsUp
    {
        public int Bar, Direction, CheckMinute;
        public double Line;
    }

    public sealed class NoiseEngine
    {
        public const string SkipDatesDefault =
            "2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07," +
            "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26," +
            "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24";
        public const string FedDatesDefault =
            "2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29,2026-09-16,2026-10-28,2026-12-09," +
            "2027-01-27,2027-03-17,2027-04-28,2027-06-09,2027-07-28,2027-09-15,2027-10-27,2027-12-08";
        public const int NChecks = 12, FirstCheck = 600, LastCheck = 930, Step = 30, RthOpen = 570, RthClose = 960;
        public const int FedCutoff = 840;

        readonly NoiseSettings s;
        readonly int minutes;
        readonly double slip;
        readonly double[] ring;
        double[] today = NewToday();
        int filled, slot;
        double dayOpen = double.NaN, prevClose = double.NaN, lastRthClose = double.NaN;
        int pendingKind, pendingDir;  // pendingKind 1: entry in pendingDir, 2: close; filled at the next bar's open
        double estPx = double.NaN;

        public readonly List<NoiseTrade> Trades = new List<NoiseTrade>();
        public readonly List<NoiseEvent> Events = new List<NoiseEvent>();
        public readonly List<NoiseOrder> Orders = new List<NoiseOrder>();
        public readonly List<NoiseHeadsUp> HeadsUps = new List<NoiseHeadsUp>();

        // State after the last bar, for the wrappers' alerts and dashboard
        public int Bar = -1;               // index of the last bar fed in
        public DateTime BarTime;           // its start, New York time
        public int Position;               // +1 long, -1 short, 0 flat (the bot's own position)
        public double EntryPrice;
        public int EntryBar;
        public double Upper = double.NaN, Lower = double.NaN, Sigma = double.NaN;
        public bool Locked, SkipToday, FedToday;
        public int LosersToday;
        public double DayPnl;              // closed P/L today, $
        public int DayTrades;

        public NoiseEngine(NoiseSettings settings, int barMinutes)
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
        public int PendingEntry { get { return pendingKind == 1 ? pendingDir : 0; } }
        public int SessionsLoaded { get { return Math.Min(filled, s.Lookback); } }
        public double CapPoints { get { return s.MaxLoss > 0 ? s.MaxLoss / s.Qty / s.PointValue : double.NaN; } }
        public double LockPoints
        {
            get { return s.LockAt > 0 && s.MaxLoss > 0 ? s.LockAt * s.MaxLoss / s.Qty / s.PointValue : double.NaN; }
        }
        public bool FreshOk { get { return s.MaxLosers <= 0 || LosersToday < s.MaxLosers; } }

        double LineStop(int d)
        {
            return d > 0 ? Upper * (1 - s.StopBuffer * Sigma) : Lower * (1 + s.StopBuffer * Sigma);
        }

        // The stop resting for the next bar while in a trade: the closest of the line stop, the max loss from the fill
        // and the lock. NaN when flat or before the first check.
        public double StopNow(out string reason)
        {
            reason = "";
            if (Position == 0 || double.IsNaN(Upper))
                return double.NaN;
            int p = Position;
            double line = LineStop(p);
            reason = "Back inside";
            if (s.MaxLoss > 0)
            {
                double cap = EntryPrice - p * s.MaxLoss / s.Qty / s.PointValue;
                if ((p > 0 && cap > line) || (p < 0 && cap < line)) { line = cap; reason = "Max loss"; }
            }
            if (Locked)
            {
                double lk = EntryPrice + p * s.LockPlus;
                if ((p > 0 && lk > line) || (p < 0 && lk < line)) { line = lk; reason = "Lock"; }
            }
            return line;
        }

        public double TargetNow()
        {
            if (Position == 0 || s.TakeProfit <= 0 || double.IsNaN(Sigma))
                return double.NaN;
            return EntryPrice * (1 + Position * s.TakeProfit * Sigma);
        }

        // The lines of the next half-hour check today (the noise for that time of day), for the dashboard.
        public bool NextCheckLines(out int checkMinute, out double upper, out double lower)
        {
            checkMinute = 0;
            upper = lower = double.NaN;
            if (!Ready || double.IsNaN(dayOpen))
                return false;
            int end = BarTime.Hour * 60 + BarTime.Minute + minutes;
            int next = end < FirstCheck ? FirstCheck : end - (end - FirstCheck) % Step + Step;
            if (next > LastCheck)
                return false;
            checkMinute = next;
            double sg = NoiseFor((next - FirstCheck) / Step);
            upper = Math.Max(dayOpen, prevClose) * (1 + sg);
            lower = Math.Min(dayOpen, prevClose) * (1 - sg);
            return true;
        }

        double NoiseFor(int k)
        {
            double sum = 0.0;
            for (int d = 0; d < s.Lookback; d++)  // same summation order as the Python and Pine loops
                sum += ring[d * NChecks + k];
            return sum / s.Lookback;
        }

        static bool InList(string list, DateTime t)
        {
            return !string.IsNullOrEmpty(list) && list.Contains(t.ToString("yyyy-MM-dd"));  // substring test, like Pine
        }

        void OpenPos(double o, int i, int d)
        {
            Position = d;
            EntryPrice = o + d * slip;
            EntryBar = i;
            entryTime = BarTime;
        }

        DateTime entryTime;

        void ClosePos(int i, double price, string reason)
        {
            double pnl = Position * (price - EntryPrice) * s.Qty * s.PointValue - 2 * s.CommissionPerSide * s.Qty;
            NoiseTrade t = new NoiseTrade();
            t.Direction = Position; t.Qty = s.Qty; t.EntryBar = EntryBar; t.EntryTime = entryTime; t.Entry = EntryPrice;
            t.ExitBar = i; t.ExitTime = BarTime; t.Exit = price; t.Reason = reason; t.Pnl = pnl;
            Trades.Add(t);
            if (pnl < 0 && reason != "Session ended")
                LosersToday++;
            DayPnl += pnl;
            DayTrades++;
            Position = 0;
            Locked = false;
        }

        void Event(int i, string action)
        {
            NoiseEvent e = new NoiseEvent();
            e.Bar = i; e.Action = action;
            Events.Add(e);
        }

        public void OnBar(DateTime nyStart, double o, double h, double l, double c)
        {
            int i = ++Bar;
            BarTime = nyStart;
            int tMin = nyStart.Hour * 60 + nyStart.Minute;
            int end = tMin + minutes;
            bool inRth = tMin >= RthOpen && end <= RthClose;

            // market orders from the previous bar fill at this bar's open
            if (pendingKind != 0)
            {
                int kind = pendingKind, d = pendingDir;
                pendingKind = 0;
                if (kind == 2 && Position != 0)
                    ClosePos(i, o - Position * slip, "Back inside");
                else if (kind == 1)
                {
                    if (Position == -d)
                        ClosePos(i, o - Position * slip, "reversed");
                    if (Position == 0)
                        OpenPos(o, i, d);
                }
            }

            // the resting stop (checked before the rest, like the broker)
            if (Position != 0 && !double.IsNaN(Upper))
            {
                int p = Position;
                double line = LineStop(p);
                string reason = "Back inside";
                if (s.MaxLoss > 0)
                {
                    // from the fill; on the fill bar from the expected fill, as a bracket placed with the entry would be
                    double basePx = EntryBar != i ? EntryPrice : estPx;
                    double cap = basePx - p * s.MaxLoss / s.Qty / s.PointValue;
                    if ((p > 0 && cap > line) || (p < 0 && cap < line)) { line = cap; reason = "Max loss"; }
                }
                if (Locked)
                {
                    double lk = EntryPrice + p * s.LockPlus;
                    if ((p > 0 && lk > line) || (p < 0 && lk < line)) { line = lk; reason = "Lock"; }
                }
                bool hit;
                double price;
                if (EntryBar == i)  // a stop attached to the entry can fill on the fill bar itself
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = (p > 0 ? Math.Min(o, line) : Math.Max(o, line)) - p * slip;
                }
                else if ((p > 0 && o <= line) || (p < 0 && o >= line))  // the line moved past the price, or a gap
                {
                    hit = true;
                    price = o - p * slip;
                }
                else
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = line - p * slip;
                }
                if (hit)
                {
                    ClosePos(i, price, reason);
                    Event(i, "EXIT");
                }
                else if (s.TakeProfit > 0 && EntryBar != i)  // the take-profit limit, from the bar after the fill
                {
                    double tp = EntryPrice * (1 + p * s.TakeProfit * Sigma);
                    if ((p > 0 && h >= tp + s.Tick) || (p < 0 && l <= tp - s.Tick))
                    {
                        ClosePos(i, tp, "Target");
                        Event(i, "TARGET");
                    }
                }
            }

            if (Position != 0 && !Locked && s.LockAt > 0 && s.MaxLoss > 0)
            {
                // the lock arms when the bar reaches the trigger (high for a long, low for a short), from the next bar
                double trigger = s.LockAt * s.MaxLoss / s.Qty / s.PointValue;
                Locked = Position * ((Position > 0 ? h : l) - EntryPrice) >= trigger;
            }

            if (Position != 0 && (!inRth || tMin == RthOpen))  // a session ended early (half day, data gap)
            {
                ClosePos(i, c - Position * slip, "Session ended");
                Event(i, "EXIT");
            }

            if (tMin == RthOpen)
            {
                prevClose = lastRthClose;
                dayOpen = o;
                LosersToday = 0;
                DayPnl = 0;
                DayTrades = 0;
                Upper = Lower = Sigma = double.NaN;
                today = NewToday();
                SkipToday = InList(s.SkipDates, nyStart);
                FedToday = s.FedNoShorts && InList(s.FedDates, nyStart);
            }
            if (inRth)
                lastRthClose = c;

            if (inRth && !double.IsNaN(dayOpen) && end >= FirstCheck && end <= LastCheck && (end - FirstCheck) % Step == 0)
            {
                int k = (end - FirstCheck) / Step;
                today[k] = Math.Abs(c / dayOpen - 1);
                if (filled >= s.Lookback && !double.IsNaN(prevClose))
                {
                    Sigma = NoiseFor(k);
                    Upper = Math.Max(dayOpen, prevClose) * (1 + Sigma);
                    Lower = Math.Min(dayOpen, prevClose) * (1 - Sigma);
                    bool shortOk = !(FedToday && end < FedCutoff);
                    int dir = 0;
                    if (SkipToday || Position != 0)
                        dir = 0;  // in a trade, exits are the resting stop's job
                    else if (c > Upper && FreshOk)
                        dir = 1;
                    else if (c < Lower && shortOk && FreshOk)
                        dir = -1;
                    if (dir != 0)
                    {
                        pendingKind = 1;
                        pendingDir = dir;
                        Event(i, dir > 0 ? "BUY" : "SELL");
                        estPx = c + dir * slip;  // the expected fill, for the max loss on the fill bar
                        double stop = LineStop(dir);
                        if (s.MaxLoss > 0)
                        {
                            double cap = estPx - dir * s.MaxLoss / s.Qty / s.PointValue;
                            stop = dir > 0 ? Math.Max(stop, cap) : Math.Min(stop, cap);
                        }
                        NoiseOrder ord = new NoiseOrder();
                        ord.SignalBar = i; ord.Direction = dir; ord.Expected = estPx; ord.Stop = stop;
                        ord.Target = s.TakeProfit > 0 ? estPx * (1 + dir * s.TakeProfit * Sigma) : double.NaN;
                        Orders.Add(ord);
                    }
                }
            }

            // heads-up: five minutes before a check, flat, and the close already past that check's line
            int nxt = end + 5;
            if (inRth && 5 % minutes == 0 && !double.IsNaN(dayOpen) && nxt >= FirstCheck && nxt <= LastCheck &&
                (nxt - FirstCheck) % Step == 0 && filled >= s.Lookback && !double.IsNaN(prevClose) && Position == 0 &&
                !SkipToday && FreshOk)
            {
                double sg = NoiseFor((nxt - FirstCheck) / Step);
                double up = Math.Max(dayOpen, prevClose) * (1 + sg), lo = Math.Min(dayOpen, prevClose) * (1 - sg);
                int hd = 0;
                if (c > up)
                    hd = 1;
                else if (c < lo && !(FedToday && nxt < FedCutoff))
                    hd = -1;
                if (hd != 0)
                {
                    NoiseHeadsUp hu = new NoiseHeadsUp();
                    hu.Bar = i; hu.Direction = hd; hu.CheckMinute = nxt; hu.Line = hd > 0 ? up : lo;
                    HeadsUps.Add(hu);
                }
            }

            if (inRth && end == RthClose)
            {
                if (Position != 0)
                {
                    ClosePos(i, c - Position * slip, "16:00 close");
                    Event(i, "FLAT");
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
        }

        public static string Hhmm(int minuteOfDay)
        {
            return string.Format("{0:00}:{1:00}", minuteOfDay / 60, minuteOfDay % 60);
        }
    }
}
