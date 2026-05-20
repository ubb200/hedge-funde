"use client";
import { useEffect, useState, useCallback } from "react";
import { api, Performance } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-gray-200 rounded-lg animate-pulse ${className}`} />;
}

function StatBox({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <p className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2">{label}</p>
      <p className={`text-2xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function PerformancePage() {
  const [perf, setPerf] = useState<Performance | null>(null);
  const [loading, setLoading] = useState(true);
  const [slowLoad, setSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setSlowLoad(false);
    const slow = setTimeout(() => setSlowLoad(true), 5000);
    api.performance()
      .then(setPerf)
      .catch(e => setError(e.message))
      .finally(() => { setLoading(false); clearTimeout(slow); });
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-9 w-44 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>
      {slowLoad && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent shrink-0" />
          <p className="text-sm font-semibold text-blue-800">Backend wacht auf… (~30s)</p>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
      </div>
      <Skeleton className="h-80" />
      <div className="grid md:grid-cols-2 gap-6">
        <Skeleton className="h-36" />
        <Skeleton className="h-36" />
      </div>
    </div>
  );

  if (error) return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Performance</h1>
        <p className="text-gray-500 mt-1">Statistiken und Benchmark-Vergleich</p>
      </div>
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start gap-3">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <p className="font-semibold text-amber-800">Fehler beim Laden</p>
          <p className="text-sm text-amber-700 mt-0.5">{error}</p>
        </div>
        <button
          onClick={load}
          className="shrink-0 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          Erneut versuchen
        </button>
      </div>
    </div>
  );

  if (!perf) return null;

  const chartData = (() => {
    if (!perf.benchmarks || perf.benchmarks.length < 2) return [];
    const base = perf.benchmarks[0];
    return perf.benchmarks.map(b => ({
      date: b.date.slice(5),
      Portfolio: parseFloat(((b.portfolio_value_chf / base.portfolio_value_chf - 1) * 100).toFixed(2)),
      "S&P 500": b.sp500_price && base.sp500_price
        ? parseFloat(((b.sp500_price / base.sp500_price - 1) * 100).toFixed(2))
        : null,
      Bitcoin: b.btc_usd_price && base.btc_usd_price
        ? parseFloat(((b.btc_usd_price / base.btc_usd_price - 1) * 100).toFixed(2))
        : null,
    }));
  })();

  const returnColor = perf.total_return_pct >= 0 ? "text-green-600" : "text-red-600";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Performance</h1>
          <p className="text-gray-500 mt-1">Statistiken und Benchmark-Vergleich</p>
        </div>
        <button
          onClick={load}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          ↻ Neu laden
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox
          label="Gesamtrendite"
          value={`${perf.total_return_pct >= 0 ? "+" : ""}${perf.total_return_pct.toFixed(2)}%`}
          sub={`P&L: CHF ${perf.total_pnl_chf >= 0 ? "+" : ""}${perf.total_pnl_chf.toFixed(0)}`}
          color={returnColor}
        />
        <StatBox
          label="Win Rate"
          value={`${perf.win_rate_pct.toFixed(1)}%`}
          sub={`${perf.wins} Gewinner / ${perf.losses} Verlierer`}
        />
        <StatBox
          label="Sharpe Ratio"
          value={perf.sharpe_ratio != null ? perf.sharpe_ratio.toFixed(3) : "—"}
          sub="Annualisiert (täglich)"
        />
        <StatBox
          label="Trades gesamt"
          value={String(perf.num_trades)}
          sub={`${perf.num_completed} abgeschlossen`}
        />
      </div>

      {chartData.length >= 2 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">Portfolio vs Benchmarks (rebased auf 0%)</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(v) => [`${Number(v) >= 0 ? "+" : ""}${v}%`]}
                contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb", fontSize: "13px" }}
              />
              <Legend />
              <Line type="monotone" dataKey="Portfolio" stroke="#2563eb" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="S&P 500" stroke="#16a34a" strokeWidth={1.5} dot={false} strokeDasharray="5 3" />
              <Line type="monotone" dataKey="Bitcoin" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="5 3" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-10 text-center">
          <p className="text-gray-400">Noch nicht genug Benchmark-Daten.</p>
          <p className="text-gray-300 text-xs mt-1">Das System sammelt täglich Snapshots — nach einigen Tagen erscheint hier ein Chart.</p>
        </div>
      )}

      {(perf.best_trade || perf.worst_trade) && (
        <div className="grid md:grid-cols-2 gap-6">
          {perf.best_trade && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2">🏆 Bester Trade</p>
              <div className="flex items-baseline justify-between">
                <p className="font-bold text-gray-900 text-xl">{perf.best_trade.symbol}</p>
                <p className="text-green-600 font-bold text-xl">
                  +CHF {perf.best_trade.pnl_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                </p>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(perf.best_trade.executed_at).toLocaleDateString("de-CH")} · {perf.best_trade.direction} {perf.best_trade.asset_type}
              </p>
            </div>
          )}
          {perf.worst_trade && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2">📉 Schlechtester Trade</p>
              <div className="flex items-baseline justify-between">
                <p className="font-bold text-gray-900 text-xl">{perf.worst_trade.symbol}</p>
                <p className="text-red-600 font-bold text-xl">
                  CHF {perf.worst_trade.pnl_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                </p>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(perf.worst_trade.executed_at).toLocaleDateString("de-CH")} · {perf.worst_trade.direction} {perf.worst_trade.asset_type}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
