"use client";
import React, { useState } from "react";
import { ShieldAlert, RotateCcw, ShieldCheck, Play, FlaskConical } from "lucide-react";
import { api, AgentWorkflowResponse } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";
import { StateGraphVisualizer } from "./StateGraphVisualizer";
import { WorkflowTrace } from "./WorkflowTrace";
import { ErrorNotice, errorMessage } from "./Feedback";
import { Button, Panel, StatusBadge } from "./ui";
interface ChaosLabViewProps {
  onScenarioRun?: () => void;
}

export const ChaosLabView: React.FC<ChaosLabViewProps> = ({ onScenarioRun }) => {
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [chaosResult, setChaosResult] = useState<AgentWorkflowResponse | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const [error, setError] = useState<string | null>(null);

  const scenarios = [
    { id: "budget_breach", icon: ShieldAlert },
    { id: "stock_race_condition", icon: RotateCcw },
    { id: "strict_upsell_rejection", icon: ShieldCheck },
  ];
  const handleRunScenario = async (scenarioId: string) => {
    if (runningScenario) return;
    setError(null);
    setExpandedStep(null);
    setRunningScenario(scenarioId);
    setChaosResult(null);
    try {
      const res = await api.triggerChaosScenario(scenarioId);
      setChaosResult(res);
      if (onScenarioRun) onScenarioRun();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setRunningScenario(null);
    }
  };

  const descriptions: Record<string, { title: string; objective: string; expected: string }> = {
    budget_breach: { title: "Budget cap breach", objective: "Request a monitor and keyboard with a ₹15,000 spending cap.", expected: "Inspect whether the returned policy decision requires human approval." },
    stock_race_condition: { title: "Stock unavailable", objective: "Explore a scripted stock-unavailable path before checkout.", expected: "Inspect the recorded failure and inventory response. This does not prove atomic payment rollback." },
    strict_upsell_rejection: { title: "Strict item protection", objective: "Request only specified items while the merchant proposes an add-on.", expected: "Inspect the buyer’s rejection and the merchant’s alternative pricing proposal." },
  };
  return <div className="space-y-6">
    <ErrorNotice message={error} />
    <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4"><FlaskConical aria-hidden className="mt-1 size-5 text-blue-700" /><p className="text-sm leading-6 text-blue-900">These scenarios explore scripted behavior. Returned traces provide evidence of this run; they do not establish concurrency safety or payment recovery.</p></div>
    <div className="grid items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3">{scenarios.map(scenario => { const Icon = scenario.icon; const content = descriptions[scenario.id]; return <article key={scenario.id} className="nexus-card flex flex-col p-5 sm:p-6"><div className="mb-5 flex items-center justify-between gap-3"><div className="flex size-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50"><Icon aria-hidden className="size-5 text-slate-600" /></div><StatusBadge>{scenario.id === "budget_breach" ? "Spending policy" : scenario.id === "stock_race_condition" ? "Inventory" : "Buyer intent"}</StatusBadge></div><h2 className="text-lg font-semibold">{content.title}</h2><p className="mt-3 text-sm leading-6 text-slate-600">{content.objective}</p><div className="my-5 flex-1 rounded-xl bg-slate-50 p-4"><h3 className="text-xs font-semibold text-slate-600">What to look for</h3><p className="mt-2 text-sm leading-6 text-slate-500">{content.expected}</p></div><Button onClick={() => handleRunScenario(scenario.id)} disabled={runningScenario !== null} loading={runningScenario === scenario.id} className="w-full"><Play className="size-4" />{runningScenario === scenario.id ? "Running scenario…" : "Run scenario"}</Button></article>; })}</div>
    {runningScenario && <Panel title="Scenario in progress"><p role="status" className="text-sm leading-6 text-slate-500">The request is running. Its recorded outcome and trace will appear when it completes.</p></Panel>}
    {chaosResult && <>
      <Panel title="Recorded outcome" description={chaosResult.user_goal} actions={<StatusBadge tone={chaosResult.status.includes("FAILED") || chaosResult.status.includes("REJECT") ? "danger" : chaosResult.status.includes("GATED") ? "warning" : "info"}>{chaosResult.status.replaceAll("_", " ").toLowerCase()}</StatusBadge>}>
        {chaosResult.quote && <p className="text-sm text-slate-600">Returned quote total <span className="ml-2 text-lg font-semibold tabular-nums text-slate-900">₹{chaosResult.quote.final_total.toLocaleString("en-IN")}</span></p>}
        {chaosResult.explainability_card && <div className="mt-4"><ExplainabilityCard data={chaosResult.explainability_card} /></div>}
        {chaosResult.hitl_gate_id && <p className="mt-4 text-sm leading-6 text-amber-800">This run created a pending decision. Open Policies & approvals to review it.</p>}
      </Panel>
      <StateGraphVisualizer steps={chaosResult.steps} workflowStatus={chaosResult.status} />
      {chaosResult.steps.length > 0 && <WorkflowTrace steps={chaosResult.steps} workflowId={chaosResult.workflow_id} expandedStep={expandedStep} onExpand={setExpandedStep} />}
    </>}
  </div>;
};