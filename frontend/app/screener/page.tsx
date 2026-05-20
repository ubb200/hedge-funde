"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, ScreenerResult } from "@/lib/api";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-gray-200 rounded-lg animate-pulse ${className}`} />;
}

export default function ScreenerPage() {
  const router = useRouter();
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [slowLoad, setSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runAt, setRunAt] = useState<string | null>(null);
  const [universeCount, setUniverseCount] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setSlowLoad(false);
    const slow = setTimeout(() => setSlowLoad(true), 5000);
    Promise.all([api.screenerResults(), api.universe()])
      .then(([r, u]) => {
        setResults(r);
        setUniverseCount(u.total);
        if (r.length > 0) setRunAt(r[0].run_at);
      })
      .catch(e => setError(e.message))
      .finally(() => { setLoading(false); clearTimeout(slow); });
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!running) { setElapsed(0); return; }
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  async function runScreener() {
    setRunning(true);
    setElapsed(0);
    try {
      const res = await api.screenerRun(30);
      setResults(res.results);
      setRunAt(res.run_at);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Screener-Fehler");
    } finally {
      setRunning(false);
    }
  }

  if (loading) return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Skeleton className="h-9 w-36 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-10 w-36" />
      </div>
      {slowLoad && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent shrink-0" />
          <p className="text-sm font-semibold text-blue-800">Backend wacht auf… (~30s)</p>
        </div>
      )}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3 border-b border-gray-100">
            <Skeleton className="h-4 w-6" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-5 w-12 rounded-full" />
            <Skeleton className="h-4 w-16 ml-auto" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-48" />
          </div>
        ))}
      </div>
    </div>
  );

  if (error) return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Screener</h1>
        <p className="text-gray-500 mt-1">Markt-Scanner für die besten Kandidaten</p>
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
          <h1 className="text-3xl font-extrabold text-gray-900">Screener</h1>
          <p className="text-gray-500 mt-1">
            {universeCount
              ? `${universeCount} Symbole im Universum — stärkste Signale für Claude-Analyse`
              : "Markt-Scanner"}
          </p>
          {runAt && (
            <p className="text-xs text-gray-400 mt-0.5">
              Letzter Lauf: {new Date(runAt).toLocaleString("de-CH")}
            </p>
          )}
        </div>
        <button
          onClick={runScreener}
          disabled={running}
          className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-60 transition-colors flex items-center gap-2"
        >
          {running ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Scannt… {elapsed}s
            </>
          ) : (
            <>📡 Jetzt scannen</>
          )}
        </button>
      </div>

      {running && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm font-semibold text-blue-800">
            Screener läuft — {universeCount ?? "~200"} Symbole werden analysiert…
          </p>
          <p className="text-xs text-blue-600 mt-0.5">Dauert ca. 60–120 Sekunden. Bitte warten.</p>
          <div className="mt-3 bg-blue-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-1000"
              style={{ width: `${Math.min(elapsed / 90 * 100, 95)}%` }}
            />
          </div>
        </div>
      )}

      {results.length === 0 && !running ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">Noch keine Screener-Daten</p>
          <p className="text-gray-300 text-sm">Klick auf "Jetzt scannen" um zu starten. Dauert ~90 Sekunden.</p>
        </div>
      ) : results.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left w-10">#</th>
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-left">Signal</th>
                  <th className="px-4 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-right">Preis</th>
                  <th className="px-4 py-3 text-left">Begründung</th>
                  <th className="px-4 py-3 text-center w-16">✓</th>
                  <th className="px-4 py-3 text-center w-24">Aktion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.map((r, i) => (
                  <tr key={r.symbol} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-400 text-xs font-medium">{i + 1}</td>
                    <td className="px-4 py-3 font-bold text-gray-900">{r.symbol}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        r.direction === "BUY"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}>
                        {r.direction}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right font-semibold tabular-nums ${
                      r.score > 0 ? "text-green-600" : "text-red-600"
                    }`}>
                      {r.score > 0 ? "+" : ""}{r.score.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500 tabular-nums">
                      {r.price != null
                        ? `$${r.price.toLocaleString("en-US", { maximumFractionDigits: 2 })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">
                      {r.reason}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {r.was_analyzed ? (
                        <span className="text-green-500 font-bold">✓</span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => router.push(`/analyze?symbol=${r.symbol}`)}
                        className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 font-semibold px-3 py-1 rounded-lg transition-colors"
                      >
                        Analysieren
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-700">
        <p className="font-semibold mb-2">Wie funktioniert der Screener?</p>
        <ul className="space-y-1 text-gray-500 text-xs">
          <li>• Lädt OHLCV-Daten für alle Symbole gleichzeitig via yfinance</li>
          <li>• Berechnet RSI, Momentum (5d/20d), Volumen-Spikes, SMA-Abstand, 52w-Hoch/Tief</li>
          <li>• Sortiert nach absolutem Interest-Score — stärkste Signale zuerst</li>
          <li>• Top 25 werden täglich um 09:00 Uhr mit Claude tief analysiert</li>
        </ul>
      </div>
    </div>
  );
}
