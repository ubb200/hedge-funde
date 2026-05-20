"use client";
import { useEffect, useState, useCallback } from "react";
import { api, Trade, Signal } from "@/lib/api";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-gray-200 rounded-lg animate-pulse ${className}`} />;
}

const AGENT_NAMES: Record<string, string> = {
  macro: "Makro",
  technical: "Technisch",
  fundamental: "Fundamental",
  crypto: "Krypto",
  risk: "Risiko",
  sentiment: "Sentiment",
};
const AGENT_ORDER = ["macro", "technical", "fundamental", "crypto", "sentiment", "risk"];

function AgentPill({ name, sig }: { name: string; sig: Signal }) {
  const color =
    sig.action === "BUY"
      ? "bg-green-50 border-green-200 text-green-800"
      : sig.action === "SELL"
      ? "bg-red-50 border-red-200 text-red-800"
      : "bg-gray-50 border-gray-200 text-gray-600";
  const badge =
    sig.action === "BUY"
      ? "bg-green-500 text-white"
      : sig.action === "SELL"
      ? "bg-red-500 text-white"
      : "bg-gray-400 text-white";

  const short = sig.reasoning
    ? sig.reasoning.length > 120
      ? sig.reasoning.slice(0, 120) + "…"
      : sig.reasoning
    : "—";

  return (
    <div className={`rounded-lg border p-2.5 flex flex-col gap-1 ${color}`}>
      <div className="flex items-center gap-1.5">
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${badge}`}>
          {sig.action}
        </span>
        <span className="text-xs font-semibold">{AGENT_NAMES[name] ?? name}</span>
        <span className="text-[10px] text-gray-400 ml-auto">{Math.round((sig.confidence ?? 0) * 100)}%</span>
      </div>
      <p className="text-[11px] leading-snug opacity-80">{short}</p>
      {sig.time_horizon && (
        <p className="text-[10px] text-gray-400 font-medium">⏱ {sig.time_horizon}</p>
      )}
    </div>
  );
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [slowLoad, setSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      <div>
        <Skeleton className="h-9 w-48 mb-2" />
        <Skeleton className="h-4 w-32" />
      </div>
      {slowLoad && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent shrink-0" />
          <p className="text-sm font-semibold text-blue-800">Backend wacht auf… (~30s)</p>
        </div>
      )}
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
            <div className="flex gap-4">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-12 rounded-full" />
              <Skeleton className="h-5 w-24 ml-auto" />
              <Skeleton className="h-5 w-16" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[...Array(6)].map((_, j) => <Skeleton key={j} className="h-16 rounded-lg" />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (error) return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold text-gray-900">Trade-History</h1>
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start gap-3">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <p className="font-semibold text-amber-800">Fehler beim Laden</p>
          <p className="text-sm text-amber-700 mt-0.5">{error}</p>
        </div>
        <button onClick={load} className="shrink-0 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
          Erneut versuchen
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Trade-History</h1>
          <p className="text-gray-500 mt-1">{trades.length} Trades — inkl. Agent-Begründungen</p>
        </div>
        <button onClick={load} className="text-xs text-blue-600 hover:text-blue-800 font-medium">
          ↻ Neu laden
        </button>
      </div>

      {trades.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">Noch keine Trades</p>
          <p className="text-gray-300 text-sm">Der Scheduler läuft täglich um 09:00 Uhr.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {trades.map(t => {
            const pnl = t.pnl_chf;
            const agents = t.agent_signals
              ? AGENT_ORDER
                  .filter(k => t.agent_signals![k])
                  .map(k => [k, t.agent_signals![k]] as [string, Signal])
              : [];

            return (
              <div key={t.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                {/* Trade-Header */}
                <div className="px-5 py-3 flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-gray-100">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${t.direction === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {t.direction}
                  </span>
                  <span className="font-bold text-gray-900 text-base">{t.symbol}</span>
                  <span className="text-xs text-gray-400 capitalize bg-gray-100 px-2 py-0.5 rounded">
                    {t.asset_type}
                  </span>
                  <span className="text-sm text-gray-500 tabular-nums">
                    CHF {t.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                  </span>
                  {pnl != null && (
                    <span className={`text-sm font-semibold tabular-nums ${pnl >= 0 ? "text-green-600" : "text-red-600"}`}>
                      P&amp;L: {pnl >= 0 ? "+" : ""}CHF {pnl.toFixed(0)}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 ml-auto tabular-nums">
                    {new Date(t.executed_at).toLocaleString("de-CH", {
                      day: "2-digit", month: "2-digit", year: "2-digit",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                </div>

                {/* Agent-Begründungen */}
                {agents.length > 0 ? (
                  <div className="px-5 py-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                    {agents.map(([name, sig]) => (
                      <AgentPill key={name} name={name} sig={sig} />
                    ))}
                  </div>
                ) : (
                  <div className="px-5 py-3 text-xs text-gray-300 italic">
                    Keine Agent-Daten für diesen Trade gespeichert.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
