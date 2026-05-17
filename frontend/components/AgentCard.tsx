"use client";
import { Signal } from "@/lib/api";

const AGENT_NAMES: Record<string, string> = {
  macro: "Makro",
  technical: "Technisch",
  fundamental: "Fundamental",
  crypto: "Krypto",
  risk: "Risiko",
  sentiment: "Sentiment",
};

const AGENT_DESC: Record<string, string> = {
  macro: "Fed, Inflation, Zinskurve",
  technical: "RSI, MACD, Indikatoren",
  fundamental: "KGV, Earnings, Bilanz",
  crypto: "Dominanz, Fear/Greed",
  risk: "Portfolio-Schutz",
  sentiment: "News, Analysten, Insider",
};

interface Props {
  name: string;
  signal: Signal;
}

export default function AgentCard({ name, signal }: Props) {
  if (!signal) return null;

  const actionColor =
    signal.action === "BUY"
      ? "bg-green-100 text-green-800 border-green-300"
      : signal.action === "SELL"
      ? "bg-red-100 text-red-800 border-red-300"
      : "bg-gray-100 text-gray-700 border-gray-300";

  const barColor =
    signal.action === "BUY"
      ? "bg-green-500"
      : signal.action === "SELL"
      ? "bg-red-500"
      : "bg-gray-400";

  const confidencePct = Math.round((signal.confidence ?? 0) * 100);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-gray-900">{AGENT_NAMES[name] ?? name}</p>
          <p className="text-xs text-gray-400">{AGENT_DESC[name] ?? ""}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-bold border ${actionColor}`}>
          {signal.action}
        </span>
      </div>

      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Konfidenz</span>
          <span>{confidencePct}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2">
          <div
            className={`${barColor} h-2 rounded-full transition-all`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>

      {signal.reasoning && (
        <p className="text-sm text-gray-600 leading-relaxed">{signal.reasoning}</p>
      )}

      {signal.risk_flags && signal.risk_flags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {signal.risk_flags.map((flag, i) => (
            <span key={i} className="text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 rounded px-2 py-0.5">
              ⚠ {flag}
            </span>
          ))}
        </div>
      )}

      {signal.key_metrics && Object.keys(signal.key_metrics).length > 0 && (
        <div className="flex flex-wrap gap-1">
          {Object.entries(signal.key_metrics).slice(0, 4).map(([k, v]) => (
            <span key={k} className="text-xs bg-gray-50 text-gray-500 border border-gray-200 rounded px-2 py-0.5">
              {k}: {v === null || v === undefined ? "N/A" : String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
