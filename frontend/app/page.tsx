"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Portfolio, Trade } from "@/lib/api";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-gray-200 rounded animate-pulse ${className}`} />;
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Home() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.portfolio(), api.trades(5)])
      .then(([p, t]) => { setPortfolio(p); setTrades(t); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="space-y-8">
      <Skeleton className="h-10 w-48" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
      </div>
      <Skeleton className="h-48" />
    </div>
  );

  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      <strong>Backend nicht erreichbar:</strong> {error}
      <p className="text-sm mt-1 text-red-500">Der Server wacht auf — bitte 30 Sekunden warten und dann neu laden.</p>
    </div>
  );

  if (!portfolio) return null;

  const startCapital = 100000;
  const returnPct = ((portfolio.total_value_chf - startCapital) / startCapital * 100).toFixed(2);
  const returnPositive = portfolio.total_value_chf >= startCapital;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Portfolio</h1>
        <p className="text-gray-500 mt-1">Virtuelles Paper-Trading-Konto</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Portfolio-Wert"
          value={`CHF ${portfolio.total_value_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`}
          sub="Gesamt inkl. Positionen"
        />
        <StatCard
          label="Rendite"
          value={`${returnPositive ? "+" : ""}${returnPct}%`}
          sub="vs. Startkapital CHF 100'000"
          color={returnPositive ? "text-green-600" : "text-red-600"}
        />
        <StatCard
          label="Cash verfügbar"
          value={`CHF ${portfolio.cash_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`}
          sub={`${((portfolio.cash_chf / portfolio.total_value_chf) * 100).toFixed(1)}% des Portfolios`}
        />
        <StatCard
          label="Offene Positionen"
          value={String(portfolio.positions.length)}
          sub={`Investiert: CHF ${portfolio.positions_value_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`}
        />
      </div>

      {portfolio.positions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Positionen</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-3 text-left">Symbol</th>
                <th className="px-5 py-3 text-right">Menge</th>
                <th className="px-5 py-3 text-right">Einstand</th>
                <th className="px-5 py-3 text-right">Aktuell</th>
                <th className="px-5 py-3 text-right">P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {portfolio.positions.map(pos => (
                <tr key={pos.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <span className="font-semibold text-gray-900">{pos.symbol}</span>
                    <span className="ml-2 text-xs text-gray-400 capitalize">{pos.asset_type}</span>
                  </td>
                  <td className="px-5 py-3 text-right text-gray-600">{pos.quantity.toFixed(6)}</td>
                  <td className="px-5 py-3 text-right text-gray-600">
                    {pos.avg_buy_price.toLocaleString("de-CH", { maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-5 py-3 text-right text-gray-600">
                    {pos.position_value_chf
                      ? `CHF ${pos.position_value_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`
                      : "—"}
                  </td>
                  <td className={`px-5 py-3 text-right font-semibold ${(pos.pnl_chf ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {pos.pnl_chf != null
                      ? `${pos.pnl_chf >= 0 ? "+" : ""}CHF ${pos.pnl_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`
                      : "—"}
                    {pos.pnl_pct != null && (
                      <span className="ml-1 text-xs">({pos.pnl_pct >= 0 ? "+" : ""}{pos.pnl_pct.toFixed(1)}%)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Letzte Trades</h2>
            <Link href="/trades" className="text-sm text-blue-600 hover:text-blue-800">Alle →</Link>
          </div>
          {trades.length === 0 ? (
            <p className="px-5 py-6 text-sm text-gray-400">Noch keine Trades — Scheduler läuft täglich um 09:00 Uhr.</p>
          ) : (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-100">
                {trades.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${t.direction === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {t.direction}
                      </span>
                      <span className="ml-2 font-semibold">{t.symbol}</span>
                    </td>
                    <td className="px-5 py-3 text-right text-gray-600">
                      CHF {t.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}
                    </td>
                    <td className={`px-5 py-3 text-right font-semibold ${(t.pnl_chf ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {t.pnl_chf != null ? `${t.pnl_chf >= 0 ? "+" : ""}${t.pnl_chf.toFixed(0)}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col gap-4">
          <h2 className="font-semibold text-gray-900">Schnellaktionen</h2>
          <Link href="/analyze" className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-colors">
            Symbol analysieren
          </Link>
          <Link href="/screener" className="block w-full text-center bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg transition-colors">
            Screener starten
          </Link>
          <Link href="/performance" className="block w-full text-center bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg transition-colors">
            Performance anzeigen
          </Link>
        </div>
      </div>
    </div>
  );
}
