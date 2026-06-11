import { useCallback, useEffect, useState } from "react";

import { ArtifactBrowser } from "./components/ArtifactBrowser";
import {
  BacktestCard,
  DiscoverCard,
  PlanCard,
  ResearchCard,
  ViewpointCard,
} from "./components/PipelineStages";
import { api, type StatusResponse } from "./lib/api";

const STANCE_STYLES: Record<string, string> = {
  进攻: "bg-emerald-500/20 text-emerald-300",
  谨慎: "bg-amber-500/20 text-amber-300",
  防守: "bg-rose-500/20 text-rose-300",
};

const COUNT_LABELS: { key: keyof StatusResponse["counts"]; label: string }[] = [
  { key: "snapshots", label: "快照" },
  { key: "briefs", label: "简报" },
  { key: "reports", label: "回测" },
  { key: "viewpoints", label: "观点" },
  { key: "plans", label: "计划" },
];

export default function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    api.getStatus().then(setStatus).catch(() => setStatus(null));
  }, [refreshKey]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Vibe Trading System</h1>
            <p className="text-sm text-slate-400">五阶段美股投资流水线仪表盘</p>
          </div>
          <div className="flex items-center gap-4">
            {status?.latest_stance && (
              <span
                className={`rounded-full px-3 py-1 text-sm font-medium ${STANCE_STYLES[status.latest_stance] ?? "bg-slate-700 text-slate-300"}`}
              >
                市场姿态：{status.latest_stance}
                {status.latest_snapshot_date && (
                  <span className="ml-1 text-xs opacity-70">({status.latest_snapshot_date})</span>
                )}
              </span>
            )}
            <div className="flex gap-3 text-xs text-slate-400">
              {COUNT_LABELS.map(({ key, label }) => (
                <span key={key}>
                  {label} <b className="text-slate-200">{status?.counts[key] ?? "—"}</b>
                </span>
              ))}
            </div>
          </div>
        </header>

        <main className="grid items-start gap-6 lg:grid-cols-[1fr_minmax(24rem,36rem)]">
          <div className="flex flex-col gap-4">
            <ResearchCard onDone={refresh} />
            <DiscoverCard onDone={refresh} />
            <BacktestCard onDone={refresh} />
            <ViewpointCard onDone={refresh} />
            <PlanCard onDone={refresh} />
          </div>
          <ArtifactBrowser refreshKey={refreshKey} onChanged={refresh} />
        </main>
      </div>
    </div>
  );
}
