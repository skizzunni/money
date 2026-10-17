// Usage: Harness <bars.csv> <minutes> [Name=value ...]
// bars.csv: "yyyy-MM-dd HH:mm,open,high,low,close" per line, bar start in New York time.
// Settings: any NoiseSettings field, e.g. Qty=10 MaxLoss=350. Prints the trades, events, orders and heads-ups.
using System;
using System.Globalization;
using System.IO;
using System.Reflection;
using NinjaTrader.NinjaScript.AddOns.MnqBot;

static class Program
{
    static string F(double x) { return double.IsNaN(x) ? "nan" : x.ToString("R", CultureInfo.InvariantCulture); }

    static int Main(string[] args)
    {
        NoiseSettings s = new NoiseSettings();
        for (int a = 2; a < args.Length; a++)
        {
            string[] kv = args[a].Split(new[] { '=' }, 2);
            FieldInfo f = typeof(NoiseSettings).GetField(kv[0]);
            if (f == null) { Console.Error.WriteLine("unknown setting " + kv[0]); return 2; }
            f.SetValue(s, Convert.ChangeType(kv[1], f.FieldType, CultureInfo.InvariantCulture));
        }
        NoiseEngine e = new NoiseEngine(s, int.Parse(args[1], CultureInfo.InvariantCulture));
        foreach (string line in File.ReadLines(args[0]))
        {
            string[] p = line.Split(',');
            DateTime t = DateTime.ParseExact(p[0], "yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);
            e.OnBar(t, double.Parse(p[1], CultureInfo.InvariantCulture), double.Parse(p[2], CultureInfo.InvariantCulture),
                    double.Parse(p[3], CultureInfo.InvariantCulture), double.Parse(p[4], CultureInfo.InvariantCulture));
        }
        foreach (NoiseTrade t in e.Trades)
            Console.WriteLine(string.Join(",", "T", t.Direction, t.EntryBar, F(t.Entry), t.ExitBar, F(t.Exit), t.Reason, F(t.Pnl)));
        foreach (NoiseEvent v in e.Events)
            Console.WriteLine(string.Join(",", "E", v.Bar, v.Action));
        foreach (NoiseOrder o in e.Orders)
            Console.WriteLine(string.Join(",", "O", o.SignalBar, o.Direction, F(o.Expected), F(o.Stop), F(o.Target)));
        foreach (NoiseHeadsUp h in e.HeadsUps)
            Console.WriteLine(string.Join(",", "H", h.Bar, h.Direction));
        return 0;
    }
}
