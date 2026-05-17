"use client";
import { Orchestrator } from "@/lib/api";

interface Props {
  orchestrator: Orchestrator;
  onTrade?: () => void;
  trading?: boolean;
}

export default function OrchestratorCard({ orchestrator, onTrade, trading }: Props) {
  const isBuy = orchestrator.action === "BUY";
  const isSell = orchestrator.action === "SELL";
  const isHold = orchestrator.action === "HOLD";

  const bg = isBuy
    ? "bg-green-50 border-green-400"
    : isSell
    ? "bg-red-50 border-red-400"
    : "bg-gray-50 border-gray-300";

  const badgeColor = isBuy
    ? "bg-green-600 text-white"
    : isSell
    ? "bg-red-600 text-white"
    : "bg-gray-500 text-white";

  const btnColor = isBuy
    ? "bg-green-600 hover:bg-green-700"
    : isSell
    ? "bg-red-600 hover:bg-red-700"
    : "bg-gray-400 cursor-not-allowed";

  const score = orchestrator.weighted_score ?? 0;
  const scoreBarWidth = Math.abs(score) * 100;
  const scoreColor = score > 0 ? "bg-green-500" : "bg-red-500";

  return (
    <div className={`rounded-xl border-2 p-5 ${bg}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Orchestrator — Finales Urteil</p>
          <p className="text-lg font-bold text-gray-900 mt-0.5">{orchestrator.asset_type?.toUpperCase()}</p>
        </div>
        <span className={`px-4 py-2 rounded-full text-lg font-extrabold ${badgeColor}`}>
          {orchestrator.action}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <p className="text-xs text-gray-400">Konfidenz</p>
          <p className="text-xl font-bold text-gray-900">{Math.round(orchestrator.confidence * 100)}%</p>
        </div>
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <p className="text-xs text-gray-400">Positionsgrösse</p>
          <p className="text-xl font-bold text-gray-900">
            {orchestrator.position_size_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })} CHF
          </p>
        </div>
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <p className="text-xs text-gray-400">Gewichteter Score</p>
          <p className={`text-xl font-bold ${score > 0 ? "text-green-600" : score < 0 ? "text-red-600" : "text-gray-600"}`}>
            {score > 0 ? "+" : ""}{score?.toFixed(3)}
          </p>
        </div>
      </div>

      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Signal-Stärke</span>
          <span>{scoreBarWidth.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div className={`${scoreColor} h-2.5 rounded-full`} style={{ width: `${scoreBarWidth}%` }} />
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-4">{orchestrator.reasoning}</p>

      {!isHold && onTrade && (
        <button
          onClick={onTrade}
          disabled={trading}
          className={`w-full py-3 rounded-lg text-white font-bold text-sm transition-colors ${btnColor} disabled:opacity-60`}
        >
          {trading ? "Wird ausgeführt…" : `${orchestrator.action} ausführen — ${orchestrator.position_size_chf?.toLocaleString("de-CH", { maximumFractionDigits: 0 })} CHF`}
        </button>
      )}
    </div>
  );
}
