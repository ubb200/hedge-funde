"use client";
import { useEffect, useState } from "react";
import { api, Performance } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function PerformancePage() {
  const [perf, setPerf] = useState<Performance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.performance()
      .then(setPerf)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Lade Performance…</p>;
  if (error) return <p className="text-red-500">{error}</p>;
  if (!perf) return null;

  const chartData = (() => {
    if (!perf.benchmarks || perf.benchmarks.length < 2) return [];
    const base = perf.benchmarks[0];
    return perf.benchmarks.map(b => ({
      date: b.date,
      Portfolio: parseFloat(((b.portfolio_value_chf / base.portfolio_value_chf - 1) * 100).toFixed(2)),
      "S&P 500": b.sp500_price && base.sp500_price
        ? parseFloat(((b.sp500_price / base.sp500_price - 1) * 100).toFixed(2))
        : null,
      Bitcoin: b.btc_usd_price && base.btc_usd_price
        ? parseFloat(((b.btc_usd_price / base.btc_usd_price - 1) * 100).toFixed(2))
        : null,
    }));
  })();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Performance</h1>
        <p className="text-gray-500 mt-1">Statistiken und Benchmark-Vergleich</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Gesamtrendite",
            value: `${perf.total_return_pct >= 0 ? "+" : ""}${perf.total_return_pct.toFixed(2)}%`,
            color: perf.total_return_pct >= 0 ? "text-green-600" : "text-red-600",
          },
          {
            label: "Win Rate",
            value: `${perf.win_rate_pct.toFixed(1)}%`,
            sub: `${perf.wins}W / ${perf.losses}L`,
          },
          {
            label: "Sharpe Ratio",
            value: perf.sharpe_ratio != null ? perf.sharpe_ratio.toFixed(3) : "—",
            sub: "Annualisiert (täglich)",
          },
          {
            label: "Trades gesamt",
            value: String(perf.num_trades),
            sub: `${perf.num_completed} abgeschlossen`,
          },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color ?? "text-gray-900"}`}>{stat.value}</p>
            {stat.sub && <p className="text-xs text-gray-400 mt-1">{stat.sub}</p>}
          </div>
        ))}
      </div>

      {chartData.length >= 2 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">Portfolio vs Benchmarks (rebased auf 0%)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${Number(v) >= 0 ? "+" : ""}${v}%`} />
              <Legend />
              <Line type="monotone" dataKey="Portfolio" stroke="#2563eb" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="S&P 500" stroke="#16a34a" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="Bitcoin" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          Noch nicht genug Benchmark-Daten. Das System sammelt täglich Snapshots.
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {perf.best_trade && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Bester Trade</p>
            <p className="font-bold text-gray-900 text-lg">{perf.best_trade.symbol}</p>
            <p className="text-green-600 font-semibold text-xl mt-1">
              +CHF {perf.best_trade.pnl_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
            </p>
            <p className="text-xs text-gray-400 mt-1">{new Date(perf.best_trade.executed_at).toLocaleDateString("de-CH")}</p>
          </div>
        )}
        {perf.worst_trade && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Schlechtester Trade</p>
            <p className="font-bold text-gray-900 text-lg">{perf.worst_trade.symbol}</p>
            <p className="text-red-600 font-semibold text-xl mt-1">
              CHF {perf.worst_trade.pnl_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
            </p>
            <p className="text-xs text-gray-400 mt-1">{new Date(perf.worst_trade.executed_at).toLocaleDateString("de-CH")}</p>
          </div>
        )}
      </div>
    </div>
  );
}
