"use client";

import React, { useState } from "react";
import { 
  Bot, 
  Sparkles, 
  CreditCard, 
  SlidersHorizontal, 
  Clock, 
  Lock, 
  ChevronDown, 
  ChevronUp, 
  Receipt,
  Check,
  ShieldCheck,
  Zap,
  ShoppingBag,
  ArrowRight
} from "lucide-react";
import { api, AgentWorkflowResponse } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";
import { RazorpayModal } from "./RazorpayModal";
import { StateGraphVisualizer } from "./StateGraphVisualizer";

interface BuyerSimulatorViewProps {
  onWorkflowComplete?: () => void;
}

export const BuyerSimulatorView: React.FC<BuyerSimulatorViewProps> = ({ onWorkflowComplete }) => {
  const [goal, setGoal] = useState("Buy me a 4K monitor and ergonomic keyboard under ₹25,000");
  const [budgetCap, setBudgetCap] = useState<number>(25000);
  const [strictItemsOnly, setStrictItemsOnly] = useState<boolean>(false);
  const [allowAutonomousUpsell, setAllowAutonomousUpsell] = useState<boolean>(false);
  const [selectedGrowthModel, setSelectedGrowthModel] = useState<string>("auto");
  
  const [loading, setLoading] = useState<boolean>(false);
  const [workflowResult, setWorkflowResult] = useState<AgentWorkflowResponse | null>(null);
  const [showRazorpayModal, setShowRazorpayModal] = useState<boolean>(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const presets = [
    {
      id: "preset_1",
      label: "4K Monitor + Keyboard",
      text: "Buy me a 4K monitor and ergonomic keyboard under ₹25,000",
      budget: 25000,
      strict: false,
    },
    {
      id: "preset_2",
      label: "Coffee Bean Subscription",
      text: "Buy monthly specialty Arabica coffee beans subscription",
      budget: 2000,
      strict: true,
    },
    {
      id: "preset_3",
      label: "GPU Compute Credits",
      text: "Buy GPU cloud compute credits for AI inference",
      budget: 5000,
      strict: false,
    },
    {
      id: "preset_4",
      label: "Studio ANC Headphones",
      text: "Buy StudioMaster Pro ANC Wireless Studio Headphones",
      budget: 12000,
      strict: true,
    },
  ];

  const handleExecute = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setWorkflowResult(null);

    try {
      const response = await api.orchestrateWorkflow({
        user_goal: goal,
        budget_cap_inr: budgetCap,
        strict_items_only: strictItemsOnly,
        allow_autonomous_upsell: allowAutonomousUpsell,
        force_growth_model: selectedGrowthModel === "auto" ? undefined : selectedGrowthModel,
      });
      setWorkflowResult(response);
      if (onWorkflowComplete) onWorkflowComplete();
    } catch (err: any) {
      alert("Execution error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleHitlResolve = async (action: string) => {
    if (!workflowResult?.hitl_gate_id) return;
    try {
      const res = await api.resumeHITLGatedWorkflow(workflowResult.hitl_gate_id, action);
      if (res.success && action === "APPROVE") {
        if (workflowResult.quote) {
          setShowRazorpayModal(true);
        }
      }
      setWorkflowResult({
        ...workflowResult,
        status: action === "APPROVE" ? "COMPLETED_AUTONOMOUS" : "REJECTED_BY_USER",
      });
      if (onWorkflowComplete) onWorkflowComplete();
    } catch (err: any) {
      alert("Failed to resolve HITL gate: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* 2-Column Responsive Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        {/* Left Column: Natural Language Prompting & Controls */}
        <div className="nexus-card p-6 space-y-5 bg-white">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Autonomous AI Buyer Agent
              </h2>
              <p className="text-xs text-slate-500">
                Natural language intent, MCP discovery & bounded spending
              </p>
            </div>
          </div>

          {/* Goal Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 block">
              Buyer Prompt / Intent
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              className="nexus-input text-xs leading-relaxed resize-none bg-slate-50/50 focus:bg-white transition-all"
              placeholder="What would you like the autonomous buyer agent to purchase?"
            />
          </div>

          {/* Quick Preset Cards */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-500 block">
              Quick Scenario Presets
            </span>
            <div className="grid grid-cols-2 gap-2">
              {presets.map((p) => {
                const isSelected = goal === p.text;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setGoal(p.text);
                      setBudgetCap(p.budget);
                      setStrictItemsOnly(p.strict);
                    }}
                    className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? "bg-blue-50 border-blue-300 ring-1 ring-blue-400/40 text-blue-950"
                        : "bg-slate-50/70 border-slate-200 hover:bg-slate-100 hover:border-slate-300 text-slate-700"
                    }`}
                  >
                    <span className="text-xs font-semibold line-clamp-1">
                      {p.label}
                    </span>
                    <span className="text-[11px] font-bold text-blue-700 font-mono mt-1">
                      Cap: ₹{p.budget.toLocaleString()}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Safety & Intent Constraints */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-4">
            {/* Spending Cap */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-blue-600" />
                  Spending Cap Boundary
                </span>
                <span className="font-mono font-bold text-blue-700 text-sm">
                  ₹{budgetCap.toLocaleString()}
                </span>
              </div>
              <input
                type="range"
                min={1000}
                max={50000}
                step={500}
                value={budgetCap}
                onChange={(e) => setBudgetCap(Number(e.target.value))}
                className="w-full cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>₹1,000</span>
                <span>₹25,000</span>
                <span>₹50,000</span>
              </div>
            </div>

            {/* Toggle Switches */}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200">
              <label 
                onClick={() => setStrictItemsOnly(!strictItemsOnly)}
                className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer select-none transition-all ${
                  strictItemsOnly 
                    ? "bg-blue-50 border-blue-300 text-blue-950" 
                    : "bg-white border-slate-200 text-slate-700 hover:border-slate-300"
                }`}
              >
                <div className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center border transition-all ${
                  strictItemsOnly ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
                }`}>
                  {strictItemsOnly && <Check className="w-3 h-3 stroke-[3]" />}
                </div>
                <div>
                  <span className="font-semibold block text-xs">Strict Items Only</span>
                  <span className="text-[10px] text-slate-500 block leading-tight">Shields unrequested upsells</span>
                </div>
              </label>

              <label 
                onClick={() => setAllowAutonomousUpsell(!allowAutonomousUpsell)}
                className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer select-none transition-all ${
                  allowAutonomousUpsell 
                    ? "bg-blue-50 border-blue-300 text-blue-950" 
                    : "bg-white border-slate-200 text-slate-700 hover:border-slate-300"
                }`}
              >
                <div className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center border transition-all ${
                  allowAutonomousUpsell ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
                }`}>
                  {allowAutonomousUpsell && <Check className="w-3 h-3 stroke-[3]" />}
                </div>
                <div>
                  <span className="font-semibold block text-xs">Allow Autonomous Upsells</span>
                  <span className="text-[10px] text-slate-500 block leading-tight">Permits value add-ons</span>
                </div>
              </label>
            </div>

            {/* Merchant Strategy */}
            <div className="pt-2 border-t border-slate-200 space-y-1">
              <label className="text-xs font-semibold text-slate-600 block">
                Merchant AI Revenue Model
              </label>
              <select
                value={selectedGrowthModel}
                onChange={(e) => setSelectedGrowthModel(e.target.value)}
                className="nexus-select text-xs font-medium bg-white"
              >
                <option value="auto">Auto-Select (Dynamic Algorithm)</option>
                <option value="quality_upgrade">Model 1: Quality Upgrade (Vertical Upsell)</option>
                <option value="conversion_closer">Model 2: Conversion Closer (Dynamic Discount)</option>
                <option value="bulk_subscription">Model 3: Bulk / Subscription (Recurring Autopay)</option>
                <option value="value_services">Model 4: Value-Add Services (Warranty & Care)</option>
              </select>
            </div>
          </div>

          {/* Action Button */}
          <button
            type="button"
            onClick={handleExecute}
            disabled={loading || !goal.trim()}
            className="w-full btn-primary py-3 text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-sm"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Executing Multi-Agent Workflow...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-blue-100" />
                <span>Execute Autonomous Workflow</span>
              </>
            )}
          </button>
        </div>

        {/* Right Column: Dynamic Quote / Execution Results */}
        <div className="space-y-6">
          {workflowResult ? (
            <div className="space-y-5">
              {/* Dynamic Quote Breakdown Card */}
              {workflowResult.quote && (
                <div className="nexus-card p-6 bg-white border-blue-200 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                        <Receipt className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">
                          Dynamic Merchant Quote
                        </h3>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Workflow #{workflowResult.workflow_id}
                        </span>
                      </div>
                    </div>
                    <span className="nexus-badge badge-blue text-[11px] font-mono font-semibold">
                      {workflowResult.quote.applied_growth_model}
                    </span>
                  </div>

                  {/* Items List */}
                  <div className="divide-y divide-slate-100">
                    {workflowResult.quote.items.map((item, idx) => (
                      <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-semibold text-slate-800 flex items-center gap-2">
                            <span>{item.name}</span>
                            {item.is_upgraded && (
                              <span className="nexus-badge badge-cyan text-[9px] py-0.2">Upgraded</span>
                            )}
                            {item.is_warranty && (
                              <span className="nexus-badge badge-purple text-[9px] py-0.2">Care Plan</span>
                            )}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                            SKU: {item.sku} • Qty: {item.quantity}
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="font-bold text-slate-900 font-mono text-xs">
                            ₹{Number(item.unit_price * item.quantity).toLocaleString()}
                          </span>
                          {item.original_price > item.unit_price && (
                            <span className="text-[10px] text-slate-400 line-through block font-mono">
                              ₹{Number(item.original_price * item.quantity).toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Price Summary */}
                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5 text-xs font-mono">
                    <div className="flex justify-between text-slate-600">
                      <span>Base Subtotal:</span>
                      <span className="font-semibold text-slate-800">₹{Number(workflowResult.quote.base_subtotal).toLocaleString()}</span>
                    </div>

                    {workflowResult.quote.discount_total > 0 && (
                      <div className="flex justify-between text-emerald-700 font-semibold">
                        <span>Autonomous Growth Discount:</span>
                        <span>-₹{Number(workflowResult.quote.discount_total).toLocaleString()}</span>
                      </div>
                    )}

                    {workflowResult.quote.warranty_total > 0 && (
                      <div className="flex justify-between text-purple-700 font-semibold">
                        <span>2-Year Express Replacement Care:</span>
                        <span>+₹{Number(workflowResult.quote.warranty_total).toLocaleString()}</span>
                      </div>
                    )}

                    <div className="flex justify-between text-sm font-bold text-slate-900 pt-2 border-t border-slate-200">
                      <span>Final Settlement Total:</span>
                      <span className="text-blue-700 font-bold text-base font-mono">
                        ₹{Number(workflowResult.quote.final_total).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex justify-between text-[11px] text-slate-500 pt-0.5">
                      <span>Merchant Margin Protected:</span>
                      <span className="text-emerald-700 font-bold">
                        {(workflowResult.quote.merchant_gross_margin_pct * 100).toFixed(1)}% (Floor Enforced)
                      </span>
                    </div>
                  </div>

                  {/* Nonce & Signature */}
                  <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
                    <div className="flex items-center gap-1 font-mono text-[10px] text-slate-600">
                      <Lock className="w-3 h-3 text-blue-600" />
                      <span>Sig: {workflowResult.quote.merchant_signature.substring(0, 16)}...</span>
                    </div>
                    <span className="nexus-badge badge-gray text-[10px]">
                      SHA-256 Nonce Verified
                    </span>
                  </div>

                  {/* Settle Action */}
                  {workflowResult.status === "COMPLETED_AUTONOMOUS" && workflowResult.razorpay_order && (
                    <button
                      type="button"
                      onClick={() => setShowRazorpayModal(true)}
                      className="w-full btn-emerald py-3 text-sm font-bold flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <CreditCard className="w-4 h-4" />
                      <span>Settle Order #{workflowResult.razorpay_order.razorpay_order_id} via Razorpay</span>
                    </button>
                  )}
                </div>
              )}

              {/* Explainability Card */}
              {workflowResult.explainability_card && (
                <ExplainabilityCard
                  data={workflowResult.explainability_card}
                  isPendingHitl={workflowResult.status === "GATED_HITL"}
                  onApprove={() => handleHitlResolve("APPROVE")}
                  onReject={() => handleHitlResolve("REJECT")}
                />
              )}
            </div>
          ) : (
            <div className="nexus-card p-8 flex flex-col items-center justify-center text-center bg-white border-slate-200 space-y-3 min-h-[440px]">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                <ShoppingBag className="w-7 h-7 text-blue-600" />
              </div>
              <div className="space-y-1 max-w-sm">
                <h3 className="font-bold text-slate-900 text-sm">
                  Autonomous Multi-Agent Engine Ready
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Enter a prompt or select a preset on the left. The supervisor agent will autonomously search the catalog, negotiate pricing, verify safety boundaries, and settle on Razorpay rails.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 w-full pt-3 max-w-xs text-center font-mono text-[10px] text-slate-500">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="block font-bold text-slate-800">1. Buyer</span>
                  <span>Intent Parsing</span>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="block font-bold text-slate-800">2. Merchant</span>
                  <span>Dynamic Quoting</span>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="block font-bold text-slate-800">3. Rails</span>
                  <span>Razorpay Settle</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* StateGraph Visualizer Pipeline */}
      {workflowResult && (
        <StateGraphVisualizer
          steps={workflowResult.steps}
          workflowStatus={workflowResult.status}
          appliedModel={workflowResult.quote?.applied_growth_model}
          policyTier={workflowResult.policy_result?.tier}
          isExecuting={loading}
        />
      )}

      {/* StateGraph Chronological Step Trace Explorer */}
      {workflowResult && workflowResult.steps && workflowResult.steps.length > 0 && (
        <div className="nexus-card p-6 bg-white border-slate-200 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Multi-Agent Chronological Trace ({workflowResult.steps.length} Steps Executed)
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-500">
              Workflow #{workflowResult.workflow_id}
            </span>
          </div>

          <div className="space-y-2.5">
            {workflowResult.steps.map((step, idx) => {
              const isExpanded = expandedStep === idx;
              const isSuccess = step.status === "SUCCESS";
              const isGated = step.status === "GATED";

              return (
                <div
                  key={idx}
                  className="rounded-xl bg-slate-50 border border-slate-200 overflow-hidden transition-all text-xs"
                >
                  <button
                    type="button"
                    onClick={() => setExpandedStep(isExpanded ? null : idx)}
                    className="w-full p-3.5 flex items-center justify-between hover:bg-slate-100/70 text-left transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-2.5 flex-1 pr-3">
                      <span className="font-mono text-xs bg-white border border-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-bold">
                        #{step.step_number}
                      </span>
                      <span className="font-semibold text-slate-900 text-xs">
                        {step.actor}
                      </span>
                      <span className="text-slate-400">→</span>
                      <span className="font-mono text-blue-700 text-xs font-semibold">
                        {step.action}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`nexus-badge text-[10px] font-mono ${
                        isGated ? 'badge-amber' : isSuccess ? 'badge-emerald' : 'badge-gray'
                      }`}>
                        {step.status}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-500" />
                      )}
                    </div>
                  </button>

                  <div className="px-3.5 pb-3.5 pt-0 text-slate-600 text-xs">
                    <p className="leading-relaxed text-slate-700 mb-2">
                      {step.summary}
                    </p>

                    {isExpanded && step.data_payload && Object.keys(step.data_payload).length > 0 && (
                      <div className="mt-2.5 pt-2.5 border-t border-slate-200 space-y-1">
                        <span className="text-[11px] font-mono text-slate-500 block uppercase font-semibold">
                          Step State Payload:
                        </span>
                        <pre className="bg-white p-3 rounded-lg border border-slate-200 text-xs font-mono text-blue-950 overflow-x-auto">
                          {JSON.stringify(step.data_payload, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Razorpay Test Rails Checkout Modal */}
      {showRazorpayModal && workflowResult?.razorpay_order && (
        <RazorpayModal
          isOpen={showRazorpayModal}
          onClose={() => setShowRazorpayModal(false)}
          orderData={{
            razorpay_order_id: workflowResult.razorpay_order.razorpay_order_id,
            amount_inr: workflowResult.razorpay_order.amount_inr,
            currency: workflowResult.razorpay_order.currency,
            receipt: workflowResult.razorpay_order.receipt,
            key_id: workflowResult.razorpay_order.key_id,
            notes: workflowResult.razorpay_order.notes,
          }}
          onSuccess={() => {
            if (onWorkflowComplete) onWorkflowComplete();
          }}
        />
      )}
    </div>
  );
};
