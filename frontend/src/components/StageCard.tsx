import type { ReactNode } from "react";

interface StageCardProps {
  step: number;
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function StageCard({ step, title, subtitle, children }: StageCardProps) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-700/60 bg-slate-900/60 p-4 shadow-lg">
      <header className="flex items-center gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-bold text-indigo-300">
          {step}
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-100">{title}</h2>
          <p className="text-xs text-slate-400">{subtitle}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

export function RunButton({
  onClick,
  loading,
  label = "执行",
}: {
  onClick: () => void;
  loading: boolean;
  label?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {loading ? "执行中…" : label}
    </button>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="rounded-lg border border-rose-700/50 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
      {message}
    </p>
  );
}

export function ResultNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-emerald-700/40 bg-emerald-950/30 px-3 py-2 text-xs text-emerald-200">
      {children}
    </div>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-400">
      {label}
      {children}
    </label>
  );
}

export const inputClass =
  "rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500";
