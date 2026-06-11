import { useEffect, useState } from "react";

import {
  api,
  ApiError,
  type BacktestRule,
  type StageResult,
  type ArtifactData,
} from "../lib/api";
import {
  ErrorNote,
  Field,
  inputClass,
  ResultNote,
  RunButton,
  StageCard,
} from "./StageCard";

function useStageRunner<T extends ArtifactData>(onDone: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StageResult<T> | null>(null);

  const run = async (fn: () => Promise<StageResult<T>>) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await fn());
      onDone();
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, result, run };
}

export function ResearchCard({ onDone }: { onDone: () => void }) {
  const { loading, error, result, run } = useStageRunner(onDone);
  return (
    <StageCard step={1} title="Research 宏观研究" subtitle="抓取 VIX / 美债 / 均线状态，判定市场姿态">
      <RunButton loading={loading} onClick={() => run(() => api.runResearch())} label="抓取宏观快照" />
      <ErrorNote message={error} />
      {result && "stance" in result.artifact && (
        <ResultNote>
          <p>快照 {result.artifact_id} 已保存</p>
          <p>
            姿态 <b>{result.artifact.stance}</b> · VIX {result.artifact.vix ?? "—"} · 10Y{" "}
            {result.artifact.treasury_10y ?? "—"}
          </p>
        </ResultNote>
      )}
    </StageCard>
  );
}

export function DiscoverCard({ onDone }: { onDone: () => void }) {
  const { loading, error, result, run } = useStageRunner(onDone);
  const [ticker, setTicker] = useState("");
  const [thesis, setThesis] = useState("");
  const [evidence, setEvidence] = useState("");
  const [invalidation, setInvalidation] = useState("");

  const submit = () =>
    run(() =>
      api.runDiscover({
        ticker: ticker.trim().toUpperCase(),
        thesis: thesis.trim(),
        key_evidence: evidence
          .split(/[,，\n]/)
          .map((s) => s.trim())
          .filter(Boolean),
        invalidation: invalidation.trim(),
      }),
    );

  return (
    <StageCard step={2} title="Discover 标的研究" subtitle="登记投资论点、关键证据与失效条件">
      <div className="grid grid-cols-2 gap-2">
        <Field label="Ticker">
          <input className={inputClass} value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TSLA" />
        </Field>
        <Field label="失效条件">
          <input className={inputClass} value={invalidation} onChange={(e) => setInvalidation(e.target.value)} placeholder="连续两季交付不及预期" />
        </Field>
      </div>
      <Field label="投资论点（一句话）">
        <input className={inputClass} value={thesis} onChange={(e) => setThesis(e.target.value)} placeholder="EV 龙头，交付动能强劲" />
      </Field>
      <Field label="关键证据（逗号分隔，最多 3 条）">
        <input className={inputClass} value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="Q1 交付超预期, 毛利率连续三季扩张" />
      </Field>
      <RunButton loading={loading} onClick={submit} label="生成研究简报" />
      <ErrorNote message={error} />
      {result && <ResultNote>研究简报 {result.artifact_id} 已保存</ResultNote>}
    </StageCard>
  );
}

export function BacktestCard({ onDone }: { onDone: () => void }) {
  const { loading, error, result, run } = useStageRunner(onDone);
  const [rules, setRules] = useState<BacktestRule[]>([]);
  const [ticker, setTicker] = useState("");
  const [rule, setRule] = useState("");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2026-01-01");

  useEffect(() => {
    api.getBacktestRules().then((r) => {
      setRules(r);
      if (r.length > 0) setRule(r[0].name);
    });
  }, []);

  const selected = rules.find((r) => r.name === rule);

  return (
    <StageCard step={3} title="Backtest 历史回测" subtitle="用预定义信号规则验证策略胜率与盈亏比">
      <div className="grid grid-cols-2 gap-2">
        <Field label="Ticker">
          <input className={inputClass} value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TSLA" />
        </Field>
        <Field label="信号规则">
          <select className={inputClass} value={rule} onChange={(e) => setRule(e.target.value)}>
            {rules.map((r) => (
              <option key={r.name} value={r.name}>
                {r.description}
              </option>
            ))}
          </select>
        </Field>
        <Field label="开始日期">
          <input className={inputClass} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="结束日期">
          <input className={inputClass} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
      </div>
      {selected && (
        <p className="text-xs text-slate-500">
          入场：{selected.entry_rule} ｜ 出场：{selected.exit_rule}
        </p>
      )}
      <RunButton
        loading={loading}
        onClick={() =>
          run(() =>
            api.runBacktest({
              ticker: ticker.trim().toUpperCase(),
              rule,
              start_date: startDate,
              end_date: endDate,
            }),
          )
        }
        label="运行回测"
      />
      <ErrorNote message={error} />
      {result && "win_rate" in result.artifact && (
        <ResultNote>
          <p>报告 {result.artifact_id} 已保存（样本 {result.artifact.sample_count}）</p>
          <p>
            胜率 {result.artifact.win_rate != null ? `${(result.artifact.win_rate * 100).toFixed(1)}%` : "—"} · 盈亏比{" "}
            {result.artifact.profit_loss_ratio?.toFixed(2) ?? "—"} · 结论 <b>{result.artifact.conclusion}</b>
          </p>
        </ResultNote>
      )}
    </StageCard>
  );
}

export function ViewpointCard({ onDone }: { onDone: () => void }) {
  const { loading, error, result, run } = useStageRunner(onDone);
  const [ticker, setTicker] = useState("");
  return (
    <StageCard step={4} title="Viewpoint 综合观点" subtitle="综合宏观 + 简报 + 回测，输出方向与置信度">
      <Field label="Ticker（需已有研究简报）">
        <input className={inputClass} value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TSLA" />
      </Field>
      <RunButton
        loading={loading}
        onClick={() => run(() => api.runViewpoint(ticker.trim().toUpperCase()))}
        label="生成观点"
      />
      <ErrorNote message={error} />
      {result && "direction" in result.artifact && "confidence" in result.artifact && (
        <ResultNote>
          <p>观点 {result.artifact_id} 已保存</p>
          <p>
            方向 <b>{result.artifact.direction}</b> · 置信度 <b>{result.artifact.confidence}</b> · 反方观点{" "}
            {(result.artifact.counter_arguments as string[]).length} 条
          </p>
        </ResultNote>
      )}
    </StageCard>
  );
}

export function PlanCard({ onDone }: { onDone: () => void }) {
  const { loading, error, result, run } = useStageRunner(onDone);
  const [ticker, setTicker] = useState("");
  return (
    <StageCard step={5} title="Plan 执行计划" subtitle="从观点生成计划（中性/低置信度会被拒绝），待人工审批">
      <Field label="Ticker（需已有非中性、置信度≥中的观点）">
        <input className={inputClass} value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TSLA" />
      </Field>
      <RunButton
        loading={loading}
        onClick={() => run(() => api.runPlan(ticker.trim().toUpperCase()))}
        label="生成执行计划"
      />
      <ErrorNote message={error} />
      {result && "approval_status" in result.artifact && (
        <ResultNote>
          <p>
            计划 {result.artifact_id} 已生成，方向 <b>{result.artifact.direction}</b>，状态{" "}
            <b>{result.artifact.approval_status}</b> —— 请在右侧产物面板中审批
          </p>
        </ResultNote>
      )}
    </StageCard>
  );
}
