"use client";
import { useEffect, useState } from "react";
import { api, Trade } from "@/lib/api";

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    api.trades(200)
      .then(setTrades)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
      <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Trade-History</h1>
        <p className="text-gray-500 mt-1">{trades.length} Trades insgesamt</p>
      </div>

      {trades.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
          Noch keine Trades. Der Scheduler läuft täglich um 09:00 Uhr.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-3 text-left">Datum</th>
                <th className="px-5 py-3 text-left">Symbol</th>
                <th className="px-5 py-3 text-left">Richtung</th>
                <th className="px-5 py-3 text-right">Menge</th>
                <th className="px-5 py-3 text-right">Preis CHF</th>
                <th className="px-5 py-3 text-right">Total CHF</th>
                <th className="px-5 py-3 text-right">P&L CHF</th>
                <th className="px-5 py-3 text-center">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {trades.map(t => (
                <tr
                  key={t.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                >
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {new Date(t.executed_at).toLocaleString("de-CH")}
                  </td>
                  <td className="px-5 py-3 font-semibold text-gray-900">{t.symbol}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${t.direction === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-gray-600">{t.quantity.toFixed(6)}</td>
                  <td className="px-5 py-3 text-right text-gray-600">{t.price_chf.toFixed(2)}</td>
                  <td className="px-5 py-3 text-right text-gray-600">
                    {t.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                  </td>
                  <td className={`px-5 py-3 text-right font-semibold ${(t.pnl_chf ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {t.pnl_chf != null ? `${t.pnl_chf >= 0 ? "+" : ""}${t.pnl_chf.toFixed(0)}` : "—"}
                  </td>
                  <td className="px-5 py-3 text-center text-gray-400 text-xs">
                    {t.agent_signals ? (expanded === t.id ? "▲" : "▼") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {expanded !== null && (() => {
            const t = trades.find(x => x.id === expanded);
            if (!t?.agent_signals) return null;
            return (
              <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                  {Object.entries(t.agent_signals).map(([name, sig]) => (
                    <div key={name} className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex justify-between mb-1">
                        <span className="text-xs font-semibold text-gray-700 capitalize">{name}</span>
                        <span className={`text-xs font-bold px-1.5 rounded ${sig.action === "BUY" ? "bg-green-100 text-green-700" : sig.action === "SELL" ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
                          {sig.action}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500">{sig.reasoning?.slice(0, 100)}…</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
