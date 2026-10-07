"use client";

import React from "react";
import { Info, ShieldAlert, CheckCircle2, Check, X, ShieldX } from "lucide-react";

interface ExplainabilityCardProps {
  data: Record<string, any>;
  onApprove?: () => void;
  onReject?: () => void;
  isPendingHitl?: boolean;
}

export const ExplainabilityCard: React.FC<ExplainabilityCardProps> = ({
  data,
  onApprove,
  onReject,
  isPendingHitl
}) => {
  if (!data || Object.keys(data).length === 0) return null;

  const isApproved = data.status === "APPROVED_AUTONOMOUS" || data.status === "APPROVED";
  const isGated = data.status === "GATED_PENDING_APPROVAL" || data.status === "GATED";
  const violations = data.violations || [];

  return (
    <div className={`rounded-xl border p-4 my-3 transition-all ${
      isGated 
        ? "bg-amber-50/90 border-amber-200 shadow-xs"
        : isApproved
        ? "bg-emerald-50/80 border-emerald-200 shadow-xs"
        : "bg-slate-50 border-slate-200 shadow-xs"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/90 mb-3">
        <div className="flex items-center gap-2.5">
          {isApproved ? (
            <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center border border-emerald-200">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          ) : isGated ? (
            <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center border border-amber-200">
              <ShieldAlert className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center border border-blue-200">
              <Info className="w-4 h-4" />
            </div>
          )}
          <div>
            <span className="font-semibold text-slate-900 text-sm font-heading">
              {data.title || "Policy Sentinel & Explainability Assessment"}
            </span>
          </div>
        </div>

        {data.tier && (
          <span className={`nexus-badge text-[10px] font-mono ${
            data.tier === "TIER_1_AUTONOMOUS" ? "badge-emerald" :
            data.tier === "TIER_2_GATED_HITL" ? "badge-amber" : "badge-rose"
          }`}>
            {data.tier}
          </span>
        )}
      </div>

      <p className="text-slate-700 text-xs mb-3 leading-relaxed">
        {data.reasoning || data.reason || "Autonomous multi-agent policy compliance check completed."}
      </p>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 bg-white p-3 rounded-lg border border-slate-200 text-xs font-mono shadow-xs">
        {data.order_total !== undefined && (
          <div>
            <span className="text-slate-500 text-[10px] block uppercase font-sans font-medium">Order Total</span>
            <span className="font-bold text-slate-900 text-sm">₹{Number(data.order_total).toLocaleString()}</span>
          </div>
        )}
        {data.budget_cap !== undefined && (
          <div>
            <span className="text-slate-500 text-[10px] block uppercase font-sans font-medium">User Cap</span>
            <span className="font-bold text-slate-700 text-sm">₹{Number(data.budget_cap).toLocaleString()}</span>
          </div>
        )}
        {data.applied_growth_model && (
          <div>
            <span className="text-slate-500 text-[10px] block uppercase font-sans font-medium">AI Model</span>
            <span className="font-bold text-blue-700 truncate block">{data.applied_growth_model}</span>
          </div>
        )}
        {data.discount_savings !== undefined && Number(data.discount_savings) > 0 && (
          <div>
            <span className="text-slate-500 text-[10px] block uppercase font-sans font-medium">AI Savings</span>
            <span className="font-bold text-emerald-700 text-sm">₹{Number(data.discount_savings).toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* Violations / Gating Reasons */}
      {violations.length > 0 && (
        <div className="mb-3">
          <span className="text-[11px] font-semibold text-amber-900 block mb-1.5 font-mono">
            Triggered Policy Boundaries:
          </span>
          <div className="space-y-1.5">
            {violations.map((v: string, i: number) => (
              <div key={i} className="text-xs text-amber-900 bg-amber-100/70 p-2.5 rounded-lg border border-amber-200 flex items-start gap-2">
                <ShieldX className="w-3.5 h-3.5 text-amber-700 mt-0.5 shrink-0" />
                <span>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendation */}
      {data.recommendation && (
        <div className="text-xs text-blue-900 bg-blue-50/80 p-2.5 rounded-lg border border-blue-200 mb-3 flex items-center gap-2">
          <span className="text-blue-600 text-sm">💡</span>
          <span className="italic">{data.recommendation}</span>
        </div>
      )}

      {/* HITL Action Buttons */}
      {isPendingHitl && (
        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
          {onReject && (
            <button
              onClick={onReject}
              className="btn-rose px-3.5 py-1.5 text-xs font-semibold"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject Transaction</span>
            </button>
          )}
          {onApprove && (
            <button
              onClick={onApprove}
              className="btn-emerald px-4 py-1.5 text-xs font-semibold"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Authorize 1-Click Escalation</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
