"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, AnalysisResult } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import OrchestratorCard from "@/components/OrchestratorCard";

const QUICK_SYMBOLS = ["AAPL", "NVDA", "MSFT", "SPY", "QQQ", "BTC-USD", "ETH-USD", "SOL-USD"];

function AnalyzeInner() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [trading, setTrading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tradeResult, setTradeResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sym = searchParams.get("symbol");
    if (sym) runAnalysis(sym);
  }, []);

  async function runAnalysis(sym: string) {
    const s = sym.trim().toUpperCase();
    if (!s) return;
    setSymbol(s);
    setLoading(true);
    setResult(null);
    setTradeResult(null);
    setError(null);
    try {
      const data = await api.analyze(s);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  async function executeTrade() {
    if (!result) return;
    setTrading(true);
    try {
      const trade = await api.executeTrade({
        symbol: result.symbol,
        direction: result.orchestrator.action as "BUY" | "SELL",
        size_chf: result.orchestrator.position_size_chf,
        asset_type: result.asset_type,
      });
      setTradeResult(
        `Trade ausgeführt: ${trade.direction} ${trade.quantity.toFixed(6)} ${trade.symbol} @ CHF ${trade.price_chf.toFixed(2)} — Total: CHF ${trade.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`
      );
    } catch (e: unknown) {
      setTradeResult(`Fehler: ${e instanceof Error ? e.message : "Unbekannt"}`);
    } finally {
      setTrading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Symbol analysieren</h1>
        <p className="text-gray-500 mt-1">5 KI-Agenten analysieren das Asset und geben eine Empfehlung</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <div className="flex gap-3">
          <input
            type="text"
            value={symbol}
            onChange={e => setSymbol(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === "Enter" && runAnalysis(symbol)}
            placeholder="z.B. AAPL, BTC-USD, SPY…"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => runAnalysis(symbol)}
            disabled={loading || !symbol}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition-colors"
          >
            {loading ? "Analysiere…" : "Analysieren"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {QUICK_SYMBOLS.map(s => (
            <button
              key={s}
              onClick={() => runAnalysis(s)}
              disabled={loading}
              className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-16">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-gray-500">5 Agenten analysieren {symbol}… (ca. 10–20 Sekunden)</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
      )}

      {result && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-900">{result.symbol} — {result.asset_type.toUpperCase()}</h2>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {Object.entries(result.signals).map(([name, signal]) => (
              <AgentCard key={name} name={name} signal={signal} />
            ))}
          </div>

          <OrchestratorCard
            orchestrator={result.orchestrator}
            onTrade={result.orchestrator.action !== "HOLD" ? executeTrade : undefined}
            trading={trading}
          />

          {tradeResult && (
            <div className={`rounded-lg p-4 text-sm ${tradeResult.startsWith("Fehler") ? "bg-red-50 text-red-700 border border-red-200" : "bg-green-50 text-green-700 border border-green-200"}`}>
              {tradeResult}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<p className="text-gray-400">Lade…</p>}>
      <AnalyzeInner />
    </Suspense>
  );
}
