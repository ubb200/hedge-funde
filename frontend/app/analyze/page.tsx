"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, AnalysisResult } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import OrchestratorCard from "@/components/OrchestratorCard";

const QUICK_SYMBOLS = ["AAPL", "NVDA", "MSFT", "TSLA", "SPY", "QQQ", "BTC-USD", "ETH-USD"];

const AGENT_ORDER = ["macro", "technical", "fundamental", "crypto", "sentiment", "risk"];

function AnalyzeInner() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [trading, setTrading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tradeResult, setTradeResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const sym = searchParams.get("symbol");
    if (sym) runAnalysis(sym);
  }, []);

  useEffect(() => {
    if (!loading) { setElapsed(0); return; }
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

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
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
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

  const orderedSignals = result
    ? AGENT_ORDER
        .filter(k => result.signals[k])
        .map(k => [k, result.signals[k]] as [string, typeof result.signals[string]])
    : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Symbol analysieren</h1>
        <p className="text-gray-500 mt-1">6 KI-Agenten analysieren das Asset und geben eine Empfehlung</p>
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
              className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-16">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-gray-600 font-medium">6 Agenten analysieren {symbol}…</p>
          <p className="text-gray-400 text-sm mt-1">{elapsed}s — dauert ca. 20–40 Sekunden</p>
          <div className="mt-4 flex justify-center gap-2 text-xs text-gray-400">
            {["Makro", "Technisch", "Fundamental", "Krypto", "Sentiment", "Risiko"].map((a, i) => (
              <span key={a} className={`px-2 py-1 rounded-full border ${elapsed > i * 4 ? "bg-blue-50 border-blue-200 text-blue-600" : "border-gray-200"}`}>
                {a}
              </span>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          <strong>Fehler:</strong> {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-900">
            {result.symbol}
            <span className="ml-2 text-sm font-normal text-gray-400 uppercase">{result.asset_type}</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {orderedSignals.map(([name, signal]) => (
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
    <Suspense fallback={<div className="text-gray-400">Lade…</div>}>
      <AnalyzeInner />
    </Suspense>
  );
}
