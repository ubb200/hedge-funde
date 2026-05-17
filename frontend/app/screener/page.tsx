"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ScreenerResult } from "@/lib/api";

export default function ScreenerPage() {
  const router = useRouter();
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runAt, setRunAt] = useState<string | null>(null);
  const [universeCount, setUniverseCount] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.screenerResults(), api.universe()])
      .then(([r, u]) => {
        setResults(r);
        setUniverseCount(u.total);
        if (r.length > 0) setRunAt(r[0].run_at);
      })
      .finally(() => setLoading(false));
  }, []);

  async function runScreener() {
    setRunning(true);
    try {
      const res = await api.screenerRun(30);
      setResults(res.results);
      setRunAt(res.run_at);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Screener</h1>
          <p className="text-gray-500 mt-1">
            {universeCount
              ? `${universeCount} Symbole gescannt — interessanteste Kandidaten für Claude-Analyse`
              : "Lädt…"}
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
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
        >
          {running ? "Scannt…" : "Jetzt scannen"}
        </button>
      </div>

      {loading ? (
        <p className="text-gray-400">Lade Screener-Ergebnisse…</p>
      ) : results.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
          Noch keine Screener-Daten. Klick auf "Jetzt scannen" um zu starten.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Rang</th>
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Signal</th>
                <th className="px-4 py-3 text-right">Score</th>
                <th className="px-4 py-3 text-right">Preis (USD)</th>
                <th className="px-4 py-3 text-left">Begründung</th>
                <th className="px-4 py-3 text-center">Analysiert</th>
                <th className="px-4 py-3 text-center">Aktion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((r, i) => (
                <tr key={r.symbol} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-4 py-3 font-bold text-gray-900">{r.symbol}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold ${
                        r.direction === "BUY"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {r.direction}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold tabular-nums ${
                    r.score > 0 ? "text-green-600" : "text-red-600"
                  }`}>
                    {r.score > 0 ? "+" : ""}{r.score.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                    {r.price != null ? r.price.toLocaleString("de-CH", { maximumFractionDigits: 2 }) : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">
                    {r.reason}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {r.was_analyzed ? (
                      <span className="text-green-500 text-xs font-semibold">✓</span>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => router.push(`/analyze?symbol=${r.symbol}`)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Analysieren →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <strong>Wie funktioniert der Screener?</strong>
        <ul className="mt-2 space-y-1 text-blue-700 text-xs">
          <li>• Lädt OHLCV-Daten für alle Symbole auf einmal via yfinance</li>
          <li>• Berechnet RSI, Momentum (5d/20d), Volumen-Spikes, SMA-Abstand, 52w-Hoch/Tief</li>
          <li>• Sortiert nach absolutem Interest-Score — stärkste Signale zuerst</li>
          <li>• Top 25 werden täglich mit den 5 Claude-Agenten tief analysiert</li>
        </ul>
      </div>
    </div>
  );
}
