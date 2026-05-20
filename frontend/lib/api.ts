const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  timeoutMs = 50000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? "API-Fehler");
    }
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Timeout — Backend antwortet nicht. Render wacht möglicherweise auf (dauert ~30s).");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  health: () => apiFetch<{ status: string; db: string }>("/health", undefined, 60000),
  portfolio: () => apiFetch<Portfolio>("/portfolio"),
  analyze: (symbol: string) =>
    apiFetch<AnalysisResult>(`/analyze/${symbol}`, { method: "POST" }, 120000),
  analyseLatest: (symbol: string) =>
    apiFetch<DbAnalysis>(`/analyses/latest/${symbol}`),
  analyses: (limit = 20) => apiFetch<DbAnalysis[]>(`/analyses?limit=${limit}`),
  trades: (limit = 100) => apiFetch<Trade[]>(`/trades?limit=${limit}`),
  performance: () => apiFetch<Performance>("/performance"),
  watchlist: () => apiFetch<Watchlist>("/watchlist"),
  updateWatchlist: (data: Watchlist) =>
    apiFetch<Watchlist>("/watchlist", { method: "PUT", body: JSON.stringify(data) }),
  executeTrade: (body: TradeRequest) =>
    apiFetch<TradeResult>("/trade/execute", { method: "POST", body: JSON.stringify(body) }),
  runNow: () => apiFetch("/scheduler/run-now", { method: "POST" }, 1800000),
  screenerResults: () => apiFetch<ScreenerResult[]>("/screener/results"),
  screenerRun: (topN = 25) =>
    apiFetch<{ count: number; run_at: string; results: ScreenerResult[] }>(
      `/screener/run?top_n=${topN}`,
      { method: "POST" },
      120000,
    ),
  universe: () => apiFetch<Universe>("/universe"),
};

// --- Types ---

export interface Signal {
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  reasoning: string;
  key_metrics: Record<string, unknown>;
  risk_flags: string[];
  time_horizon: string;
}

export interface Orchestrator extends Signal {
  weighted_score: number;
  position_size_pct: number;
  position_size_chf: number;
  asset_type: string;
}

export interface AnalysisResult {
  symbol: string;
  asset_type: string;
  orchestrator: Orchestrator;
  signals: Record<string, Signal>;
  analysis_id?: number;
}

export interface DbAnalysis {
  id: number;
  symbol: string;
  asset_type: string;
  orchestrator_action: string;
  orchestrator_confidence: number;
  orchestrator_reasoning: string;
  orchestrator_score: number;
  macro_signal: Signal;
  technical_signal: Signal;
  fundamental_signal: Signal;
  crypto_signal: Signal;
  risk_signal: Signal;
  analyzed_at: string;
}

export interface Position {
  id: number;
  symbol: string;
  asset_type: string;
  quantity: number;
  avg_buy_price: number;
  current_price?: number;
  current_price_chf?: number;
  position_value_chf?: number;
  cost_basis_chf: number;
  pnl_chf?: number;
  pnl_pct?: number;
  opened_at: string;
}

export interface Portfolio {
  cash_chf: number;
  positions_value_chf: number;
  total_value_chf: number;
  positions: Position[];
  updated_at: string;
}

export interface Trade {
  id: number;
  symbol: string;
  asset_type: string;
  direction: "BUY" | "SELL";
  quantity: number;
  price_usd: number;
  price_chf: number;
  total_chf: number;
  pnl_chf?: number;
  agent_signals?: Record<string, Signal>;
  executed_at: string;
}

export interface Performance {
  total_value_chf: number;
  total_return_pct: number;
  total_pnl_chf: number;
  num_trades: number;
  num_completed: number;
  win_rate_pct: number;
  wins: number;
  losses: number;
  sharpe_ratio?: number;
  best_trade?: Trade;
  worst_trade?: Trade;
  benchmarks: Benchmark[];
}

export interface Benchmark {
  id: number;
  date: string;
  sp500_price?: number;
  btc_usd_price?: number;
  portfolio_value_chf: number;
}

export interface Watchlist {
  stocks: string[];
  etfs: string[];
  crypto: string[];
}

export interface TradeRequest {
  symbol: string;
  direction: "BUY" | "SELL";
  size_chf?: number;
  quantity?: number;
  asset_type?: string;
}

export interface TradeResult {
  trade_id: number;
  symbol: string;
  direction: string;
  quantity: number;
  price_usd: number;
  price_chf: number;
  total_chf: number;
  pnl_chf?: number;
  remaining_cash_chf: number;
}

export interface ScreenerResult {
  id: number;
  run_at: string;
  symbol: string;
  score: number;
  direction: "BUY" | "SELL";
  reason: string;
  price?: number;
  was_analyzed: number;
}

export interface Universe {
  total: number;
  stocks: number;
  crypto: number;
  etfs: number;
  symbols: string[];
}
