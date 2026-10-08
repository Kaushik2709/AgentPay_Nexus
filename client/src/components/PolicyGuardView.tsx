"use client";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Save, ShieldCheck } from "lucide-react";
import { api, type PolicyConfig, type PendingGate, type AgentWorkflowResponse } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";
import { RazorpayModal } from "./RazorpayModal";
import { ErrorNotice, errorMessage } from "./Feedback";
import { Button, Pagination, Panel, Skeleton, StatePanel, StatusBadge, Toggle } from "./ui";

export function PolicyGuardView({ onGateResolved }: { onGateResolved?: () => void }) {
  const [policy, setPolicy] = useState<PolicyConfig | null>(null);
  const [gates, setGates] = useState<PendingGate[]>([]);
  const [loading, setLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueLoading, setQueueLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [resolving, setResolving] = useState<string | null>(null);
  const [order, setOrder] = useState<AgentWorkflowResponse["razorpay_order"]>();
  const refreshQueue = useCallback(async () => {
    setQueueLoading(true);
    try { setGates(await api.getPendingHITLGates()); setQueueError(null); }
    catch (err) { setQueueError(errorMessage(err)); }
    finally { setQueueLoading(false); }
  }, []);
  const loadPolicy = useCallback(async () => {
    setLoading(true); setError(null);
    try { setPolicy(await api.getPolicyConfig()); setDirty(false); }
    catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    let active = true;
    api.getPolicyConfig().then(value => { if (active) setPolicy(value); })
      .catch(err => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    api.getPendingHITLGates().then(value => { if (active) setGates(value); })
      .catch(err => { if (active) setQueueError(errorMessage(err)); })
      .finally(() => { if (active) setQueueLoading(false); });
    // Only refresh the queue. Never overwrite the policy draft.
    const timer = setInterval(refreshQueue, 15000);
    return () => { active = false; clearInterval(timer); };
  }, [refreshQueue]);
  function edit(update: Partial<PolicyConfig>) {
    setPolicy(current => current ? { ...current, ...update } : current);
    setDirty(true); setSaved(false);
  }
  async function save() {
    if (!policy || saving) return;
    setSaving(true); setError(null);
    try { await api.updatePolicyConfig(policy); setSaved(true); setDirty(false); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function resolve(gateId: string, action: string) {
    if (resolving) return;
    setResolving(gateId); setError(null);
    try {
      const result = await api.resumeHITLGatedWorkflow(gateId, action);
      if (!result.success) throw new Error(result.message);
      if (result.razorpay_order) setOrder(result.razorpay_order);
      await refreshQueue(); onGateResolved?.();
    } catch (err) { setError(errorMessage(err)); }
    finally { setResolving(null); }
  }
  const [page, setPage] = useState(0);
  const [selectedGateId, setSelectedGateId] = useState<string | null>(null);
  const pageSize = 5;
  const currentPage = Math.min(page, Math.max(0, Math.ceil(gates.length / pageSize) - 1));
  const visibleGates = gates.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const selectedGate = selectedGateId ? gates.find(gate => gate.gate_id === selectedGateId) : visibleGates[0];
  const categories = [...new Set(["monitors", "keyboards", "mice", "electronics", "accessories", "subscriptions", "services", ...(policy?.category_whitelist || [])])];
  return <div className="space-y-6">
    <ErrorNotice message={error} />
    <Panel title="Approval inbox" description="Review one purchase at a time. Approval prepares checkout; it does not complete payment." actions={<div className="flex flex-wrap items-center gap-3"><a href="#spending-policy" className="inline-flex min-h-11 items-center text-sm font-medium text-blue-700 underline underline-offset-4">Edit spending policy</a><Button variant="secondary" onClick={refreshQueue} loading={queueLoading}><RefreshCw className="size-4" />Refresh approvals</Button></div>}>
      <ErrorNotice message={queueError} />
      {queueLoading && gates.length === 0 ? <div role="status" aria-label="Loading approvals" className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-20" /></div> : gates.length === 0 ? <StatePanel compact icon={ShieldCheck} title={queueError ? "Approval inbox unavailable" : "You’re up to date"} description={queueError ? "Refresh the inbox to check for pending purchases." : "No purchases are currently waiting for approval."} /> : <>
        <div className="grid items-start gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
          <div className="space-y-2"><p className="mb-3 text-xs text-slate-500">{gates.length} pending purchases</p>{visibleGates.map((gate,index) => <button key={gate.gate_id} type="button" aria-pressed={selectedGate?.gate_id === gate.gate_id} disabled={resolving !== null} onClick={() => setSelectedGateId(gate.gate_id)} className={`w-full rounded-xl border p-4 text-left transition-colors ${selectedGate?.gate_id === gate.gate_id ? "border-blue-200 bg-blue-50" : "border-slate-200 hover:bg-slate-50"}`}><span className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-medium">Purchase {currentPage * pageSize + index + 1}</span><span className="text-sm font-semibold tabular-nums">{typeof gate.explainability_card.order_total === "number" ? `₹${gate.explainability_card.order_total.toLocaleString("en-IN")}` : "Review"}</span></span><span className="mt-2 block break-all font-mono text-xs text-slate-500">{gate.gate_id}</span><span className="mt-3 inline-block text-xs text-amber-800">Needs your approval</span></button>)}</div>
          <div className="min-w-0">{selectedGate ? <div><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-base font-semibold">Purchase decision</h3><StatusBadge tone="warning">Awaiting approval</StatusBadge></div><p className="mb-3 break-all font-mono text-xs text-slate-500">{selectedGate.gate_id}</p><ExplainabilityCard data={selectedGate.explainability_card} isPendingHitl busy={resolving !== null} onApprove={() => resolve(selectedGate.gate_id, "APPROVE")} onReject={() => resolve(selectedGate.gate_id, "REJECT")} /></div> : <StatePanel icon={ShieldCheck} title="Select a pending purchase" description="The previously selected purchase is no longer pending. Choose a purchase from the inbox." />}</div>
        </div>
        <div className="mt-5"><Pagination page={currentPage} pageSize={pageSize} total={gates.length} onPageChange={value => { setPage(value); setSelectedGateId(null); }} label="approvals" /></div>
      </>}
    </Panel>
    <Panel id="spending-policy" tabIndex={-1} className="scroll-mt-6" title="Spending policy" description="Set the boundaries for future purchases. Changes take effect when saved." actions={<span role="status"><StatusBadge tone={dirty ? "warning" : saved ? "success" : "neutral"}>{dirty ? "Unsaved changes" : saved ? "Policy saved" : "Current policy"}</StatusBadge></span>}>
      {loading ? <div role="status" aria-label="Loading policy" className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-20" /></div> : !policy ? <Button variant="secondary" onClick={loadPolicy}>Retry loading policy</Button> : <fieldset disabled={saving} className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2"><div className="rounded-xl border border-slate-200 bg-slate-50 p-5"><label htmlFor="policy-purchase-limit" className="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm font-medium"><span>Per-purchase limit in rupees</span><span className="text-lg font-semibold tabular-nums text-blue-700">₹{policy.max_tx_amount.toLocaleString("en-IN")}</span></label><input id="policy-purchase-limit" aria-label="Per-purchase limit in rupees" type="range" min={Math.min(0, policy.max_tx_amount)} max={Math.max(100000, policy.max_tx_amount)} step={500} value={policy.max_tx_amount} onChange={event => edit({ max_tx_amount: Number(event.target.value) })} /></div><div className="rounded-xl border border-slate-200 bg-slate-50 p-5"><label htmlFor="policy-daily-limit" className="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm font-medium"><span>Daily spending limit in rupees</span><span className="text-lg font-semibold tabular-nums text-blue-700">₹{policy.daily_velocity_cap.toLocaleString("en-IN")}</span></label><input id="policy-daily-limit" aria-label="Daily spending limit in rupees" type="range" min={0} max={Math.max(200000, policy.daily_velocity_cap)} step={1000} value={policy.daily_velocity_cap} onChange={event => edit({ daily_velocity_cap: Number(event.target.value) })} /><p className="mt-2 text-xs text-slate-500">Rolling 24-hour spending boundary</p></div></div>
        <fieldset><legend className="mb-3 text-sm font-medium">Permitted categories</legend><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{categories.map(category => <label key={category} className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm capitalize ${policy.category_whitelist.includes(category) ? "border-blue-200 bg-blue-50/50" : "border-slate-200"}`}><input type="checkbox" checked={policy.category_whitelist.includes(category)} onChange={event => edit({ category_whitelist: event.target.checked ? [...policy.category_whitelist, category] : policy.category_whitelist.filter(item => item !== category) })} className="size-4 shrink-0 accent-blue-600" />{category}</label>)}</div></fieldset>
        <Toggle label="Allow value-add proposals" description="Buyer intent and spending limits still apply." checked={policy.allow_autonomous_upsell} onChange={() => edit({ allow_autonomous_upsell: !policy.allow_autonomous_upsell })} />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5"><p className="text-xs text-slate-500">Approval polling preserves your unsaved settings.</p><Button loading={saving} disabled={!dirty} onClick={save}><Save className="size-4" />{saving ? "Saving…" : "Save policy"}</Button></div>
      </fieldset>}
    </Panel>
    {order && <RazorpayModal key={order.razorpay_order_id} isOpen orderData={order} onClose={() => setOrder(undefined)} onSuccess={() => onGateResolved?.()} />}
  </div>;
}
