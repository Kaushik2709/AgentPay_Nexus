"use client";
import React, { useState } from "react";
import { ArrowRight, Sparkles, CreditCard, ShoppingBag, Check, ShieldCheck, Receipt, Bot, Lock } from "lucide-react";
import { api, AgentWorkflowResponse } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";
import { RazorpayModal } from "./RazorpayModal";
import { StateGraphVisualizer } from "./StateGraphVisualizer";
import { ErrorNotice, errorMessage } from "./Feedback";
import { WorkflowTrace } from "./WorkflowTrace";
import { Button, Field, Panel, StatusBadge, Toggle, Skeleton } from "./ui";
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
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);

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
    setError(null);
    setExpandedStep(null);
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
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleHitlResolve = async (action: string) => {
    if (!workflowResult?.hitl_gate_id || resolving) return;
    setResolving(true);
    setError(null);
    try {
      const res = await api.resumeHITLGatedWorkflow(workflowResult.hitl_gate_id, action);
      setWorkflowResult({
        ...workflowResult,
        status: action === "APPROVE" ? "AWAITING_PAYMENT" : "REJECTED_BY_USER",
        razorpay_order: res.razorpay_order,
        explainability_card: {
          ...workflowResult.explainability_card,
          status: action === "APPROVE" ? "APPROVED" : "REJECTED",
          title: action === "APPROVE" ? "Purchase approved — payment pending" : "Purchase rejected",
          reasoning: res.message,
        },
      });
      if (action === "APPROVE" && res.razorpay_order) setShowRazorpayModal(true);
      if (onWorkflowComplete) onWorkflowComplete();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setResolving(false);
    }
  };

  const money = (amount: number) => `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  const quote = workflowResult?.quote;
  return <div className="space-y-6">
    <ErrorNotice message={error} />
    <div className="purchase-grid">
      <Panel title="Create a purchase" description="Tell your buyer what you need. Set the boundaries before it prepares a quote." actions={<span className="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><Bot className="size-5" /></span>}>
        <fieldset disabled={loading || resolving} className="space-y-6">
          <Field label="Purchase request" htmlFor="purchase-request" hint="Include the items you need and any preferences.">
            <textarea id="purchase-request" value={goal} onChange={event => setGoal(event.target.value)} rows={3} className="nexus-input resize-y leading-7" placeholder="Describe your purchase…" />
          </Field>
          <div><p className="mb-3 text-xs font-medium text-slate-500">Or start with a scenario</p><div className="grid gap-2 sm:grid-cols-2">{presets.map(preset => <button key={preset.id} type="button" aria-pressed={goal === preset.text} onClick={() => { setGoal(preset.text); setBudgetCap(preset.budget); setStrictItemsOnly(preset.strict); }} className={`flex min-h-16 flex-col justify-center gap-1 rounded-lg border px-3 py-2.5 text-left transition-colors ${goal === preset.text ? "border-blue-200 bg-blue-50 text-blue-900" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}><span className="text-sm font-medium">{preset.label}</span><span className="text-xs text-slate-500">Budget {money(preset.budget)}</span></button>)}</div></div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><label htmlFor="purchase-budget" className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm font-medium"><span>Purchase budget in rupees</span><span className="text-lg font-semibold tabular-nums text-blue-700">{money(budgetCap)}</span></label><input id="purchase-budget" aria-label="Purchase budget in rupees" type="range" min={1000} max={50000} step={500} value={budgetCap} onChange={event => setBudgetCap(Number(event.target.value))} /><div className="mt-1 flex justify-between text-xs text-slate-500"><span>₹1,000</span><span>₹50,000</span></div></div>
          <div className="space-y-3"><Toggle label="Strict items only" description="Keep the quote limited to requested items." checked={strictItemsOnly} onChange={() => setStrictItemsOnly(!strictItemsOnly)} /><Toggle label="Allow autonomous upsells" description="Let the merchant propose value add-ons." checked={allowAutonomousUpsell} onChange={() => setAllowAutonomousUpsell(!allowAutonomousUpsell)} /></div>
          <Field label="Merchant pricing strategy" htmlFor="pricing-strategy"><select id="pricing-strategy" className="nexus-select" value={selectedGrowthModel} onChange={event => setSelectedGrowthModel(event.target.value)}><option value="auto">Automatic pricing</option><option value="quality_upgrade">Quality upgrade</option><option value="conversion_closer">Conversion discount</option><option value="bulk_subscription">Bulk / subscription pricing</option><option value="value_services">Warranty & care services</option></select></Field>
          <Button loading={loading} disabled={!goal.trim()} onClick={handleExecute} className="w-full"><Sparkles className="size-4" />{loading ? "Preparing your quote…" : "Prepare purchase quote"}{!loading && <ArrowRight className="ml-auto size-4" />}</Button>
        </fieldset>
      </Panel>
      <div className="min-w-0 space-y-5" aria-busy={loading || undefined}>
        {workflowResult ? <>
          {!quote && !workflowResult.explainability_card && <Panel title="Workflow outcome"><p role="status" className="text-lg font-medium">{workflowResult.status.replaceAll("_", " ").toLowerCase()}</p><p className="mt-3 text-sm leading-6 text-slate-500">No quote was returned. Review the recorded evidence below before trying another request.</p></Panel>}
          {quote && <Panel title="Your merchant quote" description="Review the items and pricing before continuing." actions={<StatusBadge tone="info">{quote.applied_growth_model.replaceAll("_", " ")}</StatusBadge>}>
            <div className="mb-5 rounded-xl border border-blue-100 bg-blue-50/60 p-5"><p className="text-xs font-medium text-blue-800">Quote total</p><p className="mt-2 text-4xl font-semibold tracking-tight tabular-nums">{money(quote.final_total)}</p><p className="mt-3 text-sm leading-6 text-slate-600">{workflowResult.user_goal}</p></div>
            <div className="divide-y divide-slate-100">{quote.items.map((item, index) => <div key={`${item.sku}-${index}`} className="flex flex-wrap justify-between gap-3 py-4"><div className="min-w-0 flex-1"><p className="text-sm font-medium">{item.name}</p><p className="mt-1 break-all text-xs text-slate-500">{item.quantity} × {money(item.unit_price)} · {item.sku}</p><div className="mt-2 flex gap-2">{item.is_upgraded && <StatusBadge tone="info">Upgraded</StatusBadge>}{item.is_warranty && <StatusBadge>Care plan</StatusBadge>}</div></div><div className="text-right"><p className="text-sm font-semibold tabular-nums">{money(item.unit_price * item.quantity)}</p>{item.original_price > item.unit_price && <p className="mt-1 text-xs text-slate-500 line-through">{money(item.original_price * item.quantity)}</p>}</div></div>)}</div>
            <dl className="mt-4 space-y-3 rounded-xl bg-slate-50 p-4 text-sm"><div className="flex justify-between gap-3"><dt className="text-slate-500">Base subtotal</dt><dd className="tabular-nums">{money(quote.base_subtotal)}</dd></div>{quote.discount_total > 0 && <div className="flex justify-between gap-3 text-emerald-700"><dt>Discount</dt><dd>−{money(quote.discount_total)}</dd></div>}{quote.warranty_total > 0 && <div className="flex justify-between gap-3"><dt className="text-slate-500">Care services</dt><dd>{money(quote.warranty_total)}</dd></div>}<div className="flex justify-between gap-3 border-t border-slate-200 pt-3 font-semibold"><dt>Total</dt><dd>{money(quote.final_total)}</dd></div><div className="flex justify-between gap-3 text-xs text-slate-500"><dt>Quoted merchant margin</dt><dd>{(quote.merchant_gross_margin_pct * 100).toFixed(1)}%</dd></div></dl>
            <details className="mt-4 text-xs text-slate-500"><summary className="flex min-h-11 items-center gap-2"><Lock className="size-3" />Quote identifiers & signature</summary><p className="mt-2 break-all font-mono">{quote.quote_id}</p><p className="mt-2 break-all font-mono">{quote.merchant_signature}</p><p className="mt-2">Expires: {quote.expires_at}</p></details>
            {["COMPLETED_AUTONOMOUS", "AWAITING_PAYMENT"].includes(workflowResult.status) && workflowResult.razorpay_order && <Button onClick={() => setShowRazorpayModal(true)} className="mt-4 w-full"><CreditCard className="size-4" />Continue to test checkout</Button>}
            {workflowResult.status === "PAID" && <p role="status" className="mt-4 flex items-center gap-2 text-sm text-emerald-700"><Check className="size-4" />Payment verified</p>}
          </Panel>}
          {workflowResult.explainability_card && <ExplainabilityCard data={workflowResult.explainability_card} isPendingHitl={workflowResult.status === "GATED_HITL"} busy={resolving} onApprove={() => handleHitlResolve("APPROVE")} onReject={() => handleHitlResolve("REJECT")} />}
        </> : <Panel title="Purchase review" description="A clear decision, with the evidence behind it.">
          <div className="relative overflow-hidden rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 via-white to-slate-50 px-5 py-8"><div className="mb-5 flex size-12 items-center justify-center rounded-xl border border-blue-200 bg-white text-blue-600"><ShoppingBag className="size-6" /></div><h3 role={loading ? "status" : undefined} className="text-xl font-semibold tracking-tight">{loading ? "Preparing your purchase" : "Intent becomes a considered purchase"}</h3><p className="mt-3 max-w-md text-sm leading-6 text-slate-600">{loading ? "Catalog discovery, pricing, and policy checks are in progress. Recorded evidence arrives when the request completes." : "Your quote, spending decision, and checkout options will appear here. Start by creating a purchase request."}</p>{loading && <div className="mt-5 space-y-3"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-5 w-1/2" /></div>}</div>
          <ol className="mt-6 space-y-5">{[{title:"Discover suitable items",description:"The buyer interprets your request and searches the catalog.",icon:Bot},{title:"Review the merchant’s offer",description:"See proposed items, pricing, and any changes to your request.",icon:Receipt},{title:"Check policy, then decide",description:"Review spending boundaries before approval or test checkout.",icon:ShieldCheck}].map((step,index)=><li key={step.title} className="flex gap-4"><span className="flex size-9 shrink-0 items-center justify-center rounded-full border border-slate-200 text-sm font-medium text-slate-500">{index+1}</span><div><p className="text-sm font-medium">{step.title}</p><p className="mt-1 text-sm leading-6 text-slate-500">{step.description}</p></div></li>)}</ol>
        </Panel>}
      </div>
    </div>
    {(workflowResult || loading) && <StateGraphVisualizer steps={workflowResult?.steps} workflowStatus={workflowResult?.status} isExecuting={loading} />}
    {workflowResult && workflowResult.steps.length > 0 && <WorkflowTrace steps={workflowResult.steps} workflowId={workflowResult.workflow_id} expandedStep={expandedStep} onExpand={setExpandedStep} />}
    {showRazorpayModal && workflowResult?.razorpay_order && <RazorpayModal key={workflowResult.razorpay_order.razorpay_order_id} isOpen orderData={workflowResult.razorpay_order} onClose={() => setShowRazorpayModal(false)} onSuccess={() => setWorkflowResult(current => current ? { ...current, status: "PAID" } : current)} />}
  </div>;
};
