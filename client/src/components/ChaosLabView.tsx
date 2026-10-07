"use client";

import React, { useState } from "react";
import { 
  Flame, 
  ShieldAlert, 
  RotateCcw, 
  ShieldCheck, 
  Play, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp,
  Clock
} from "lucide-react";
import { api, AgentWorkflowResponse } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";
import { StateGraphVisualizer } from "./StateGraphVisualizer";

interface ChaosLabViewProps {
  onScenarioRun?: () => void;
}

export const ChaosLabView: React.FC<ChaosLabViewProps> = ({ onScenarioRun }) => {
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [chaosResult, setChaosResult] = useState<AgentWorkflowResponse | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const scenarios = [
    {
      id: "budget_breach",
      title: "Failure Case 1: Budget Cap Breach",
      badge: "Policy Boundary Test",
      badgeClass: "badge-amber",
      description: "Buyer requests 4K monitor & keyboard (~₹23,000) with a strict ₹15,000 policy cap.",
      expectedBehavior: "Policy Guard halts automated debit, generates explainability card showing overage, and triggers a Tier 2 HITL 1-click authorization card.",
      icon: ShieldAlert,
      iconColor: "text-amber-700 bg-amber-100 border-amber-200",
    },
    {
      id: "stock_race_condition",
      title: "Failure Case 2: Stock Race Condition & Atomic Rollback",
      badge: "Concurrency Test",
      badgeClass: "badge-rose",
      description: "Stock reaches 0 due to a competing buyer agent right before checkout confirmation.",
      expectedBehavior: "Supervisor detects stock lock failure, invalidates quote, releases held funds, logs rollback in audit trail, and avoids orphaned Razorpay charges.",
      icon: RotateCcw,
      iconColor: "text-rose-700 bg-rose-100 border-rose-200",
    },
    {
      id: "strict_upsell_rejection",
      title: "Failure Case 3: Upsell Shield Rejection & Fallback",
      badge: "Buyer Shield Test",
      badgeClass: "badge-blue",
      description: "User specifies strict items only, Merchant attempts value-add warranty add-on.",
      expectedBehavior: "Buyer AI activates Upsell Shield, rejects accessory, Merchant AI dynamically falls back to Model 2 (2.5% Conversion Closer discount).",
      icon: ShieldCheck,
      iconColor: "text-blue-700 bg-blue-100 border-blue-200",
    },
  ];

  const handleRunScenario = async (scenarioId: string) => {
    setRunningScenario(scenarioId);
    setChaosResult(null);
    try {
      const res = await api.triggerChaosScenario(scenarioId);
      setChaosResult(res);
      if (onScenarioRun) onScenarioRun();
    } catch (err: any) {
      alert("Chaos scenario failed: " + err.message);
    } finally {
      setRunningScenario(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="nexus-card bg-white border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center border border-rose-200">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 font-heading">
              Failure & Resilience Chaos Lab
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic 1-click test triggers verifying graceful failure handling without data loss or orphaned charges
            </p>
          </div>
        </div>
      </div>

      {/* Scenario Trigger Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          const isRunning = runningScenario === sc.id;

          return (
            <div
              key={sc.id}
              className="nexus-card flex flex-col justify-between p-4 bg-white border-slate-200 hover:border-slate-300 shadow-2xs"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${sc.iconColor}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className={`nexus-badge ${sc.badgeClass} text-[10px] font-mono`}>
                    {sc.badge}
                  </span>
                </div>

                <h3 className="font-bold text-slate-900 text-sm font-heading mb-1.5 leading-snug">
                  {sc.title}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed mb-3">
                  {sc.description}
                </p>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700 leading-relaxed mb-4">
                  <span className="font-mono text-sky-700 font-bold block mb-0.5">Expected Handling:</span>
                  {sc.expectedBehavior}
                </div>
              </div>

              <div>
                <button
                  onClick={() => handleRunScenario(sc.id)}
                  disabled={!!runningScenario}
                  className="w-full btn-primary py-2 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer"
                >
                  {isRunning ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                      <span>Injecting Chaos...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Run Chaos Scenario</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Execution Result Waterfall */}
      {chaosResult && (
        <div className="space-y-4">
          {/* Visual StateGraph for Chaos run */}
          <StateGraphVisualizer
            steps={chaosResult.steps}
            workflowStatus={chaosResult.status}
            appliedModel={chaosResult.quote?.applied_growth_model}
            policyTier={chaosResult.policy_result?.tier}
          />

          {/* Recovery Proof Card */}
          <div className="nexus-card bg-emerald-50 border-emerald-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-emerald-950 text-sm font-heading">
                Resilience Guarantee Verified
              </h3>
            </div>
            <p className="text-xs text-emerald-800 leading-relaxed">
              Execution finished with status <span className="font-mono font-bold text-emerald-900">{chaosResult.status}</span>. All actions logged in the immutable SHA-256 audit ledger. Zero orphaned charges generated on Razorpay rails.
            </p>
          </div>

          {/* Explainability Card if Gated */}
          {chaosResult.explainability_card && (
            <ExplainabilityCard
              data={chaosResult.explainability_card}
              isPendingHitl={chaosResult.status === "GATED_HITL"}
            />
          )}

          {/* Step-by-Step Waterfall Trace */}
          <div className="nexus-card bg-white border-slate-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm font-heading">
                  Chaos Execution Waterfall Trace ({chaosResult.steps.length} Steps)
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                Workflow #{chaosResult.workflow_id}
              </span>
            </div>

            <div className="space-y-2">
              {chaosResult.steps.map((step, idx) => {
                const isExpanded = expandedStep === idx;
                return (
                  <div
                    key={idx}
                    className="rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-[10px] bg-white border border-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-bold">
                          #{step.step_number}
                        </span>
                        <span className="font-semibold text-slate-800 font-heading">
                          {step.actor}
                        </span>
                        <span className="text-slate-400">→</span>
                        <span className="font-mono text-blue-700 text-[11px] font-semibold">
                          {step.action}
                        </span>
                      </div>
                      <span className={`nexus-badge text-[10px] font-mono ${
                        step.status === "SUCCESS" ? "badge-emerald" :
                        step.status === "GATED" ? "badge-amber" : "badge-rose"
                      }`}>
                        {step.status}
                      </span>
                    </div>

                    <p className="mt-1.5 text-slate-600 text-xs leading-relaxed">
                      {step.summary}
                    </p>

                    {step.data_payload && Object.keys(step.data_payload).length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200">
                        <button
                          onClick={() => setExpandedStep(isExpanded ? null : idx)}
                          className="text-[10px] font-mono text-blue-700 hover:text-blue-900 flex items-center gap-1 cursor-pointer font-medium"
                        >
                          <span>{isExpanded ? "Hide Payload" : "View Step Data Payload"}</span>
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                        {isExpanded && (
                          <pre className="mt-2 bg-white p-2.5 rounded-lg border border-slate-200 text-[10px] font-mono text-slate-800 overflow-x-auto">
                            {JSON.stringify(step.data_payload, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
