import { useEffect, useState } from "react";

import {
  api,
  ApiError,
  type ArtifactData,
  type ArtifactItem,
  type ArtifactType,
  type ExecutionPlan,
} from "../lib/api";

const TABS: { type: ArtifactType; label: string }[] = [
  { type: "snapshots", label: "宏观快照" },
  { type: "briefs", label: "研究简报" },
  { type: "reports", label: "回测报告" },
  { type: "viewpoints", label: "观点" },
  { type: "plans", label: "执行计划" },
];

const STATUS_STYLES: Record<string, string> = {
  pending_review: "bg-amber-500/20 text-amber-300",
  approved: "bg-emerald-500/20 text-emerald-300",
  rejected: "bg-rose-500/20 text-rose-300",
  revised: "bg-sky-500/20 text-sky-300",
};

function ArtifactFields({ data }: { data: ArtifactData }) {
  return (
    <dl className="grid gap-1.5">
      {Object.entries(data).map(([key, value]) => {
        if (value === null || value === "" || (Array.isArray(value) && value.length === 0)) {
          return null;
        }
        return (
          <div key={key} className="grid grid-cols-[10rem_1fr] gap-2 text-xs">
            <dt className="text-slate-500">{key}</dt>
            <dd className="text-slate-200">
              {Array.isArray(value) ? (
                <ul className="list-disc pl-4">
                  {value.map((v, i) => (
                    <li key={i}>{String(v)}</li>
                  ))}
                </ul>
              ) : (
                String(value)
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

function PlanReviewActions({
  plan,
  onReviewed,
}: {
  plan: ArtifactItem<ExecutionPlan>;
  onReviewed: () => void;
}) {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const act = async (action: "approve" | "reject" | "revise") => {
    setBusy(true);
    setError(null);
    try {
      await api.reviewPlan(plan.id, action, notes);
      onReviewed();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-slate-700/60 pt-3">
      <input
        className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
        placeholder="审批备注（可选）"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => act("approve")}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          批准
        </button>
        <button
          disabled={busy}
          onClick={() => act("reject")}
          className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-500 disabled:opacity-50"
        >
          拒绝
        </button>
        <button
          disabled={busy}
          onClick={() => act("revise")}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-50"
        >
          需修改
        </button>
      </div>
      {error && <p className="text-xs text-rose-300">{error}</p>}
    </div>
  );
}

export function ArtifactBrowser({ refreshKey, onChanged }: { refreshKey: number; onChanged: () => void }) {
  const [tab, setTab] = useState<ArtifactType>("snapshots");
  const [loaded, setLoaded] = useState<{ tab: ArtifactType | null; items: ArtifactItem[] }>({
    tab: null,
    items: [],
  });

  useEffect(() => {
    let active = true;
    api.listArtifacts(tab).then((items) => {
      if (active) setLoaded({ tab, items });
    });
    return () => {
      active = false;
    };
  }, [tab, refreshKey]);

  const loading = loaded.tab !== tab;
  const items = loading ? [] : loaded.items;

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-700/60 bg-slate-900/60 p-4 shadow-lg">
      <h2 className="text-base font-semibold text-slate-100">产物面板</h2>
      <nav className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <button
            key={t.type}
            onClick={() => setTab(t.type)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              tab === t.type
                ? "bg-indigo-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {loading && <p className="text-xs text-slate-500">加载中…</p>}
      {!loading && items.length === 0 && (
        <p className="text-xs text-slate-500">暂无产物 —— 在左侧执行对应阶段后这里会出现结果</p>
      )}
      <div className="flex flex-col gap-3 overflow-y-auto">
        {items.map((item) => {
          const status = (item.data as ExecutionPlan).approval_status;
          return (
            <article key={item.id} className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-3">
              <header className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-100">{item.id}</h3>
                {tab === "plans" && status && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[status] ?? ""}`}>
                    {status}
                  </span>
                )}
              </header>
              <ArtifactFields data={item.data} />
              {tab === "plans" && status === "pending_review" && (
                <PlanReviewActions
                  plan={item as ArtifactItem<ExecutionPlan>}
                  onReviewed={onChanged}
                />
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
