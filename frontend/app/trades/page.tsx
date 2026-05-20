"use client";
import { useEffect, useState, useCallback } from "react";
import { api, Trade } from "@/lib/api";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-gray-200 rounded-lg animate-pulse ${className}`} />;
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [slowLoad, setSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setSlowLoad(false);
    const slow = setTimeout(() => setSlowLoad(true), 5000);
    api.trades(200)
      .then(setTrades)
      .catch(e => setError(e.message))
      .finally(() => { setLoading(false); clearTimeout(slow); });
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Skeleton className="h-9 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      {slowLoad && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent shrink-0" />
          <p className="text-sm font-semibold text-blue-800">Backend wacht auf… (~30s)</p>
        </div>
      )}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3 border-b border-gray-100">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-5 w-12 rounded-full" />
            <Skeleton className="h-4 w-16 ml-auto" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );

  if (error) return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Trade-History</h1>
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

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Trade-History</h1>
          <p className="text-gray-500 mt-1">{trades.length} Trades insgesamt</p>
        </div>
        <button
          onClick={load}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          ↻ Neu laden
        </button>
      </div>

      {trades.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">Noch keine Trades</p>
          <p className="text-gray-300 text-sm">Der Scheduler läuft täglich um 09:00 Uhr.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-5 py-3 text-left">Datum</th>
                  <th className="px-5 py-3 text-left">Symbol</th>
                  <th className="px-5 py-3 text-left">Dir.</th>
                  <th className="px-5 py-3 text-right">Menge</th>
                  <th className="px-5 py-3 text-right">Preis CHF</th>
                  <th className="px-5 py-3 text-right">Total CHF</th>
                  <th className="px-5 py-3 text-right">P&amp;L</th>
                  <th className="px-5 py-3 text-center w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {trades.map(t => (
                  <>
                    <tr
                      key={t.id}
                      className={`hover:bg-gray-50 transition-colors ${t.agent_signals ? "cursor-pointer" : ""}`}
                      onClick={() => t.agent_signals && setExpanded(expanded === t.id ? null : t.id)}
                    >
                      <td className="px-5 py-3 text-gray-400 text-xs tabular-nums">
                        {new Date(t.executed_at).toLocaleString("de-CH", {
                          day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"
                        })}
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-semibold text-gray-900">{t.symbol}</span>
                        <span className="ml-1.5 text-xs text-gray-400 capitalize">{t.asset_type}</span>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${t.direction === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                          {t.direction}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right text-gray-500 tabular-nums text-xs">{t.quantity.toFixed(6)}</td>
                      <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{t.price_chf.toFixed(2)}</td>
                      <td className="px-5 py-3 text-right text-gray-700 tabular-nums font-medium">
                        {t.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                      </td>
                      <td className={`px-5 py-3 text-right font-semibold tabular-nums ${(t.pnl_chf ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {t.pnl_chf != null
                          ? `${t.pnl_chf >= 0 ? "+" : ""}${t.pnl_chf.toFixed(0)}`
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3 text-center text-gray-400 text-xs">
                        {t.agent_signals ? (expanded === t.id ? "▲" : "▼") : ""}
                      </td>
                    </tr>
                    {expanded === t.id && t.agent_signals && (
                      <tr key={`${t.id}-detail`}>
                        <td colSpan={8} className="bg-gray-50 px-5 py-4 border-t border-gray-100">
                          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                            {Object.entries(t.agent_signals).map(([name, sig]) => (
                              <div key={name} className="bg-white rounded-lg border border-gray-200 p-3">
                                <div className="flex justify-between items-center mb-1.5">
                                  <span className="text-xs font-semibold text-gray-700 capitalize">{name}</span>
                                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                                    sig.action === "BUY" ? "bg-green-100 text-green-700"
                                    : sig.action === "SELL" ? "bg-red-100 text-red-700"
                                    : "bg-gray-100 text-gray-600"
                                  }`}>
                                    {sig.action}
                                  </span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5 mb-1.5">
                                  <div
                                    className={`h-1.5 rounded-full ${sig.action === "BUY" ? "bg-green-400" : sig.action === "SELL" ? "bg-red-400" : "bg-gray-300"}`}
                                    style={{ width: `${Math.round((sig.confidence ?? 0) * 100)}%` }}
                                  />
                                </div>
                                <p className="text-xs text-gray-400 leading-snug line-clamp-2">
                                  {sig.reasoning?.slice(0, 90)}
                                </p>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
