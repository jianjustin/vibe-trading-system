// Typed client for the vts FastAPI backend.

export type ArtifactType = "snapshots" | "briefs" | "reports" | "viewpoints" | "plans";

export interface MacroSnapshot {
  date: string;
  stance: "进攻" | "谨慎" | "防守";
  treasury_10y: number | null;
  treasury_2y: number | null;
  spread_10y_2y: number | null;
  dxy: number | null;
  vix: number | null;
  spy_above_50d: boolean | null;
  spy_above_200d: boolean | null;
  qqq_above_50d: boolean | null;
  qqq_above_200d: boolean | null;
  hy_spread: number | null;
  most_important_change: string;
  impact_on_growth: string;
  impact_on_watchlist: string;
  next_step: string;
}

export interface ResearchBrief {
  ticker: string;
  thesis: string;
  key_evidence: string[];
  core_driver: string;
  macro_sensitivity: string;
  valuation_sensitivity: string;
  catalysts: string;
  invalidation: string;
  next_action: string;
}

export interface BacktestReport {
  rule_name: string;
  ticker_scope: string;
  market_filter: string;
  entry_rule: string;
  exit_rule: string;
  data_source: string;
  time_range: string;
  sample_count: number;
  win_rate: number | null;
  profit_loss_ratio: number | null;
  max_drawdown: number | null;
  vs_spy: string;
  vs_qqq: string;
  conclusion: string;
}

export interface Viewpoint {
  ticker: string;
  direction: "看多" | "中性" | "看空";
  confidence: "高" | "中" | "低";
  macro_support: string;
  core_logic: string;
  supporting_evidence: string;
  counter_arguments: string[];
  invalidation: string;
  valid_until: string;
}

export interface ExecutionPlan {
  ticker: string;
  direction: string;
  position_pct: string;
  entry_condition: string;
  entry_price_range: string;
  stop_loss: string;
  target: string;
  holding_period: string;
  prerequisites: string;
  approval_status: "pending_review" | "approved" | "rejected" | "revised";
  approval_notes: string;
  approved_at: string | null;
}

export type ArtifactData =
  | MacroSnapshot
  | ResearchBrief
  | BacktestReport
  | Viewpoint
  | ExecutionPlan;

export interface ArtifactItem<T = ArtifactData> {
  id: string;
  data: T;
}

export interface StageResult<T = ArtifactData> {
  artifact_type: ArtifactType;
  artifact_id: string;
  artifact: T;
}

export interface StatusResponse {
  counts: Record<ArtifactType, number>;
  latest_stance: string | null;
  latest_snapshot_date: string | null;
}

export interface BacktestRule {
  name: string;
  description: string;
  entry_rule: string;
  exit_rule: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // keep statusText
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  getStatus: () => request<StatusResponse>("/api/status"),

  listArtifacts: <T = ArtifactData>(type: ArtifactType) =>
    request<ArtifactItem<T>[]>(`/api/artifacts/${type}`),

  getBacktestRules: () => request<BacktestRule[]>("/api/backtest/rules"),

  runResearch: () =>
    request<StageResult<MacroSnapshot>>("/api/stages/research/run", { method: "POST" }),

  runDiscover: (body: {
    ticker: string;
    thesis: string;
    key_evidence: string[];
    invalidation: string;
    next_action?: string;
  }) =>
    request<StageResult<ResearchBrief>>("/api/stages/discover/run", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  runBacktest: (body: {
    ticker: string;
    rule: string;
    start_date?: string;
    end_date?: string;
  }) =>
    request<StageResult<BacktestReport>>("/api/stages/backtest/run", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  runViewpoint: (ticker: string) =>
    request<StageResult<Viewpoint>>("/api/stages/viewpoint/run", {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }),

  runPlan: (ticker: string) =>
    request<StageResult<ExecutionPlan>>("/api/stages/plan/run", {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }),

  reviewPlan: (planId: string, action: "approve" | "reject" | "revise", notes: string) =>
    request<StageResult<ExecutionPlan>>(`/api/plans/${planId}/review`, {
      method: "POST",
      body: JSON.stringify({ action, notes }),
    }),
};
