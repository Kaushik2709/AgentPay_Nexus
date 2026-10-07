"use client";

import React from "react";
import { 
  Bot, 
  Search, 
  TrendingUp, 
  ShieldCheck, 
  ShieldAlert, 
  CreditCard, 
  ArrowRight
} from "lucide-react";
import { AgentStepTrace } from "@/lib/api";

interface StateGraphVisualizerProps {
  steps?: AgentStepTrace[];
  workflowStatus?: string;
  appliedModel?: string;
  policyTier?: string;
  isExecuting?: boolean;
}

export const StateGraphVisualizer: React.FC<StateGraphVisualizerProps> = ({
  steps = [],
  workflowStatus,
  appliedModel,
  policyTier,
  isExecuting = false,
}) => {
  // Determine state of each node based on step traces
  const hasStep = (actor: string, actionPattern?: string) => {
    return steps.some((s) => {
      const matchActor = s.actor.toLowerCase().includes(actor.toLowerCase());
      if (!actionPattern) return matchActor;
      return matchActor && s.action.toLowerCase().includes(actionPattern.toLowerCase());
    });
  };

  const isGated = workflowStatus === "GATED_HITL" || steps.some(s => s.status === "GATED");
  const isComplete = workflowStatus === "COMPLETED_AUTONOMOUS" || workflowStatus === "SUCCESS";

  const nodes = [
    {
      id: "buyer",
      name: "Buyer Agent",
      role: "Intent & Constraints",
      icon: Bot,
      active: isExecuting || steps.length > 0,
      status: steps.length > 0 ? "SUCCESS" : isExecuting ? "RUNNING" : "IDLE",
      metric: "UAP / ACP Intent",
      color: "blue",
    },
    {
      id: "catalog",
      name: "MCP Catalog",
      role: "Schema & Inventory",
      icon: Search,
      active: hasStep("BuyerAgent", "MCP"),
      status: hasStep("BuyerAgent", "MCP") ? "SUCCESS" : isExecuting ? "PENDING" : "IDLE",
      metric: "JSON-LD Discovery",
      color: "cyan",
    },
    {
      id: "merchant",
      name: "Merchant AI",
      role: appliedModel ? `Model: ${appliedModel}` : "Revenue Optimization",
      icon: TrendingUp,
      active: hasStep("MerchantGrowthAgent"),
      status: hasStep("MerchantGrowthAgent") ? "SUCCESS" : "IDLE",
      metric: appliedModel ? "Quote Generated" : "4 Growth Models",
      color: "emerald",
    },
    {
      id: "shield",
      name: "Upsell Shield",
      role: "Intent Alignment Guard",
      icon: ShieldCheck,
      active: hasStep("BuyerAgent", "SHIELD"),
      status: hasStep("BuyerAgent", "SHIELD") ? "SUCCESS" : "IDLE",
      metric: "Anti-Clutter Filter",
      color: "purple",
    },
    {
      id: "policy",
      name: "Policy Sentinel",
      role: policyTier ? policyTier.replace(/_/g, " ") : "Bounded Safety Gate",
      icon: isGated ? ShieldAlert : ShieldCheck,
      active: hasStep("PolicyGuard") || hasStep("Policy"),
      status: isGated ? "GATED" : hasStep("PolicyGuard") ? "SUCCESS" : "IDLE",
      metric: isGated ? "1-Click HITL Triggered" : "Autonomous Pass",
      color: isGated ? "amber" : "emerald",
    },
    {
      id: "settlement",
      name: "Razorpay Rails",
      role: "HMAC & Settlement",
      icon: CreditCard,
      active: isComplete || hasStep("Supervisor", "SETTLED") || hasStep("Supervisor", "CONFIRMED"),
      status: isComplete ? "SETTLED" : isGated ? "ON HOLD" : "IDLE",
      metric: "SHA-256 Non-Repudiation",
      color: "blue",
    },
  ];

  return (
    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 mb-5 shadow-xs">
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 font-mono">
            LangGraph Supervisor StateGraph
          </span>
        </div>
        <div className="flex items-center gap-2">
          {workflowStatus && (
            <span className={`nexus-badge text-[11px] ${
              isGated ? 'badge-amber' : isComplete ? 'badge-emerald' : 'badge-blue'
            }`}>
              {isGated ? "⏸ GATED HITL PAUSE" : isComplete ? "✓ AUTONOMOUS EXECUTION" : workflowStatus}
            </span>
          )}
          <span className="text-[11px] text-slate-500 font-mono">
            {steps.length} Steps Traced
          </span>
        </div>
      </div>

      {/* Nodes visual flow */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 relative">
        {nodes.map((node, idx) => {
          const Icon = node.icon;
          const isNodeGated = node.status === "GATED";
          const isNodeSuccess = node.status === "SUCCESS" || node.status === "SETTLED";

          let borderClass = "border-slate-200 bg-white text-slate-700 shadow-2xs";
          let glowClass = "";
          let iconBg = "bg-slate-100 text-slate-600 border border-slate-200";

          if (isNodeGated) {
            borderClass = "border-amber-300 bg-amber-50/80 text-amber-900 shadow-2xs";
            glowClass = "";
            iconBg = "bg-amber-100 text-amber-700 border border-amber-200";
          } else if (isNodeSuccess) {
            borderClass = "border-emerald-300 bg-emerald-50/70 text-emerald-900 shadow-2xs";
            glowClass = "";
            iconBg = "bg-emerald-100 text-emerald-700 border border-emerald-200";
          } else if (node.status === "RUNNING") {
            borderClass = "border-blue-300 bg-blue-50/90 text-blue-900 shadow-xs";
            glowClass = "animate-pulse";
            iconBg = "bg-blue-100 text-blue-700 border border-blue-200";
          }

          return (
            <div
              key={node.id}
              className={`flex flex-col p-3 rounded-xl border transition-all duration-200 ${borderClass} ${glowClass} relative group`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${iconBg}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isNodeGated 
                    ? "bg-amber-100 text-amber-800 border border-amber-200"
                    : isNodeSuccess 
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                    : node.status === "RUNNING"
                    ? "bg-blue-100 text-blue-800 border border-blue-200"
                    : "bg-slate-100 text-slate-500 border border-slate-200"
                }`}>
                  {node.status}
                </span>
              </div>

              <div className="font-semibold text-xs text-slate-900 tracking-tight leading-snug truncate">
                {node.name}
              </div>
              <div className="text-[10px] text-slate-500 truncate mt-0.5" title={node.role}>
                {node.role}
              </div>

              <div className="mt-2 pt-2 border-t border-slate-100 text-[10px] font-mono text-slate-600 truncate font-medium">
                {node.metric}
              </div>

              {idx < nodes.length - 1 && (
                <div className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-300 pointer-events-none">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
