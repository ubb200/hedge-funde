"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, AnalysisResult } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import OrchestratorCard from "@/components/OrchestratorCard";

const QUICK_SYMBOLS = ["BTC-USD", "AAPL", "NVDA", "MSFT", "TSLA", "ETH-USD", "SPY", "QQQ"];
const AGENT_ORDER = ["macro", "technical", "fundamental", "crypto", "sentiment", "risk"];
const AGENT_LABELS = ["Makro", "Technisch", "Fundamental", "Krypto", "Sentiment", "Risiko"];

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
        `✅ Trade ausgeführt: ${trade.direction} ${trade.quantity.toFixed(6)} ${trade.symbol} @ CHF ${trade.price_chf.toFixed(2)} — Total: CHF ${trade.total_chf.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`
      );
    } catch (e: unknown) {
      setTradeResult(`❌ Fehler: ${e instanceof Error ? e.message : "Unbekannt"}`);
    } finally {
      setTrading(false);
    }
  }

  const orderedSignals = result
    ? AGENT_ORDER
        .filter(k => result.signals[k])
        .map(k => [k, result.signals[k]] as [string, typeof result.signals[string]])
    : [];

  const agentsDone = loading ? Math.floor(elapsed / 5) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900">Symbol analysieren</h1>
        <p className="text-gray-500 mt-1">6 KI-Agenten analysieren das Asset parallel und geben eine Empfehlung</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <div className="flex gap-3">
          <input
            type="text"
            value={symbol}
            onChange={e => setSymbol(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === "Enter" && runAnalysis(symbol)}
            placeholder="z.B. AAPL, BTC-USD, SPY…"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={() => runAnalysis(symbol)}
            disabled={loading || !symbol.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analysiere…
              </>
            ) : "🔍 Analysieren"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {QUICK_SYMBOLS.map(s => (
            <button
              key={s}
              onClick={() => runAnalysis(s)}
              disabled={loading}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors disabled:opacity-40 font-medium"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-gray-800 font-semibold text-lg">6 Agenten analysieren {symbol}</p>
          <p className="text-gray-400 text-sm mt-1">{elapsed}s — dauert ca. 20–60 Sekunden</p>
          <div className="mt-5 flex justify-center gap-2 flex-wrap">
            {AGENT_LABELS.map((a, i) => (
              <span
                key={a}
                className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all ${
                  agentsDone > i
                    ? "bg-green-50 border-green-300 text-green-700"
                    : agentsDone === i
                    ? "bg-blue-50 border-blue-300 text-blue-700 animate-pulse"
                    : "border-gray-200 text-gray-400"
                }`}
              >
                {agentsDone > i ? "✓ " : agentsDone === i ? "⟳ " : ""}{a}
              </span>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-start gap-3">
          <span className="text-xl">❌</span>
          <div>
            <p className="font-semibold text-red-700">Analyse fehlgeschlagen</p>
            <p className="text-sm text-red-600 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-5">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{result.symbol}</h2>
            <span className="text-xs font-semibold text-gray-400 uppercase bg-gray-100 px-2 py-1 rounded">
              {result.asset_type}
            </span>
          </div>

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
            <div className={`rounded-xl p-4 text-sm font-medium ${
              tradeResult.startsWith("❌")
                ? "bg-red-50 text-red-700 border border-red-200"
                : "bg-green-50 text-green-700 border border-green-200"
            }`}>
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
    <Suspense fallback={
      <div className="flex items-center gap-3 py-8 text-gray-400">
        <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-300 border-t-transparent" />
        Lade…
      </div>
    }>
      <AnalyzeInner />
    </Suspense>
  );
}
