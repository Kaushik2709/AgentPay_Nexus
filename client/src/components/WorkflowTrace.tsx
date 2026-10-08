"use client";
import { ChevronDown, Clock } from "lucide-react";
import type { AgentStepTrace } from "@/lib/api";
import { Panel, StatusBadge } from "./ui";
export function WorkflowTrace({ steps, workflowId, expandedStep, onExpand }: { steps: AgentStepTrace[]; workflowId: string; expandedStep: number | null; onExpand: (index: number | null) => void }) {
  return <Panel title="Decision evidence" description={`${steps.length} recorded steps. Expand a step to inspect its payload.`} actions={<span className="break-all font-mono text-xs text-slate-500">{workflowId}</span>}>
    <div className="divide-y divide-slate-100">{steps.map((step, index) => <div key={`${step.step_number}-${index}`} className="py-3">
      <button type="button" aria-expanded={expandedStep === index} aria-controls={`trace-${workflowId}-${index}`} onClick={() => onExpand(expandedStep === index ? null : index)} className="flex min-h-11 w-full flex-wrap items-center gap-3 rounded-lg px-1 text-left hover:bg-slate-50">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-slate-200 text-xs text-slate-500">{step.step_number}</span><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{step.action.replaceAll("_", " ")}</span><span className="mt-1 block text-xs text-slate-500">{step.actor}</span></span>
        <StatusBadge tone={step.status === "FAILED" ? "danger" : step.status === "SUCCESS" ? "success" : step.status === "GATED" || step.status === "WARNING" ? "warning" : "neutral"}>{step.status.toLowerCase()}</StatusBadge><ChevronDown className={`size-4 text-slate-500 transition-transform ${expandedStep === index ? "rotate-180" : ""}`} />
      </button><p className="my-2 text-sm leading-6 text-slate-600 sm:pl-12">{step.summary}</p>
      <div id={`trace-${workflowId}-${index}`} hidden={expandedStep !== index} className="space-y-3 pt-2 sm:pl-12"><p className="flex items-center gap-2 text-xs text-slate-500"><Clock className="size-3" />{step.timestamp}</p><pre className="max-h-72 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100">{JSON.stringify(step.data_payload, null, 2)}</pre></div>
    </div>)}</div>
  </Panel>;
}
