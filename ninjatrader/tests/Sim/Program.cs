// Usage: Sim <bars.csv> <minutes> [Property=value ...]
// bars.csv: "yyyy-MM-dd HH:mm,open,high,low,close" per line, bar START in New York time (the stand-in stamps each bar
// with its end time, like NinjaTrader). Properties: any public property of the strategy, e.g. Funded=true.
// Prints the strategy's trades on the account (T), its order calls (O) and the dashboard text (D).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Strategies;

static class Program
{
    static string F(double x) { return x.ToString("R", CultureInfo.InvariantCulture); }

    static int Main(string[] args)
    {
        int minutes = int.Parse(args[1], CultureInfo.InvariantCulture);
        TimeZoneInfo ny = TimeZoneInfo.FindSystemTimeZoneById("America/New_York");
        NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo = TimeZoneInfo.FindSystemTimeZoneById("Europe/London");
        List<DateTime> t = new List<DateTime>();
        List<double> o = new List<double>(), h = new List<double>(), l = new List<double>(), c = new List<double>();
        foreach (string line in File.ReadLines(args[0]))
        {
            string[] p = line.Split(',');
            DateTime start = DateTime.ParseExact(p[0], "yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);
            // NinjaTrader shows bar END times in the platform's time zone: here London, to test the conversion
            t.Add(TimeZoneInfo.ConvertTime(start.AddMinutes(minutes), ny, NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo));
            o.Add(double.Parse(p[1], CultureInfo.InvariantCulture)); h.Add(double.Parse(p[2], CultureInfo.InvariantCulture));
            l.Add(double.Parse(p[3], CultureInfo.InvariantCulture)); c.Add(double.Parse(p[4], CultureInfo.InvariantCulture));
        }
        // "Strategy=Runner" picks the rejected runner (Strategies/MnqMomentumRunner.cs), "Strategy=C" candidate C
        // (Strategies/MnqMomentumC.cs); otherwise B
        bool runner = Array.IndexOf(args, "Strategy=Runner") >= 0, cand = Array.IndexOf(args, "Strategy=C") >= 0;
        bool candD = Array.IndexOf(args, "Strategy=D") >= 0;  // candidates D / E (Strategies/MnqCandidateD.cs)
        Strategy s = runner ? (Strategy)new MnqMomentumRunner() : cand ? (Strategy)new MnqMomentumC() :
                     candD ? (Strategy)new MnqCandidateD() : new MnqNoiseMomentum();
        s.BarsPeriod.Value = minutes;
        s.Run(t, o, h, l, c, delegate (Strategy x)
        {
            for (int a = 2; a < args.Length; a++)
            {
                if (args[a] == "Strategy=Runner" || args[a] == "Strategy=C" || args[a] == "Strategy=D") continue;
                string[] kv = args[a].Split(new[] { '=' }, 2);
                PropertyInfo pi = s.GetType().GetProperty(kv[0]);  // the strategy's, or the stand-in's
                if (pi == null) throw new ArgumentException("unknown property " + kv[0]);
                pi.SetValue(x, Convert.ChangeType(kv[1], pi.PropertyType, CultureInfo.InvariantCulture));
            }
        });
        foreach (SimTrade x in s.SimTrades)
            Console.WriteLine(string.Join(",", "T", x.Direction, x.EntryBar, F(x.Entry), x.ExitBar, F(x.Exit), x.ExitName, F(x.Pnl)));
        foreach (SimTrade x in s.SimTrades)  // the same trades: which entry, how many contracts
            Console.WriteLine(string.Join(",", "TN", x.EntryName, x.Qty));
        foreach (string x in s.OrderLog)
            Console.WriteLine("O," + x);
        string d;
        if (Draw.Texts.TryGetValue(runner ? "runner_dash" : cand ? "c_dash" : "mnq_dash", out d))
            Console.WriteLine("D," + d.Replace("\n", " | "));
        foreach (string x in s.Printed)
            Console.WriteLine("P," + x);
        return 0;
    }
}
