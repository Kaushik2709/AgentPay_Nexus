"use client";
import { Bot, Search, TrendingUp, ShieldCheck, CreditCard } from "lucide-react";
import type { AgentStepTrace } from "@/lib/api";

interface Props { steps?: AgentStepTrace[]; workflowStatus?: string; appliedModel?: string; policyTier?: string; isExecuting?: boolean }
export function StateGraphVisualizer({ steps = [], workflowStatus, isExecuting = false }: Props) {
  const stages = [
    { name: "Buyer intent", action: "PARSE_INTENT", icon: Bot },
    { name: "Catalog search", action: "MCP_CATALOG_QUERY", icon: Search },
    { name: "Merchant quote", action: "QUOTE", icon: TrendingUp },
    { name: "Buyer shield", action: "SHIELD", icon: ShieldCheck },
    { name: "Policy check", action: "POLICY_EVALUATION", icon: ShieldCheck },
    { name: "Payment order", action: "CREATE_RAZORPAY_ORDER", icon: CreditCard },
  ];
  const label = workflowStatus === "PAID" ? "Payment verified"
    : ["COMPLETED_AUTONOMOUS", "AWAITING_PAYMENT"].includes(workflowStatus || "") ? "Awaiting payment"
    : workflowStatus === "GATED_HITL" ? "Approval required"
    : workflowStatus === "NEEDS_CLARIFICATION" ? "Clarification required"
    : workflowStatus === "REJECTED_BY_USER" ? "Purchase rejected"
    : workflowStatus === "FAILED_ROLLED_BACK" ? "Workflow stopped"
    : isExecuting ? "Request in progress" : "Ready";
  return <section aria-label="Workflow stages" className="nexus-card p-4">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-sm font-semibold">Workflow trace</h2>
      <span role="status" className="nexus-badge badge-gray text-xs">{label}</span>
    </div>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {stages.map(({ name, action, icon: Icon }) => {
        const trace = steps.filter(step => step.action.includes(action)).at(-1);
        const status = trace?.status || (isExecuting ? "PENDING" : "NOT RUN");
        const style = status === "FAILED" ? "badge-rose" : status === "GATED" || status === "WARNING" ? "badge-amber" : status === "SUCCESS" ? "badge-emerald" : "badge-gray";
        return <div key={name} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <Icon className="mb-3 size-5 text-slate-600" />
          <p className="mb-2 text-sm font-medium">{name}</p>
          <span className={`nexus-badge text-[10px] ${style}`}>{status}</span>
        </div>;
      })}
    </div>
    <p className="mt-3 text-xs text-slate-500">{steps.length} recorded steps. Order creation prepares checkout; payment is a separate action.</p>
  </section>;
}
