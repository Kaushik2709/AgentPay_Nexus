"use client";
import { Check, X, ShieldAlert, ShieldCheck, Info } from "lucide-react";
import type { Explanation } from "@/lib/api";
import { Button, StatusBadge } from "./ui";
interface Props { data: Explanation; onApprove?: () => void; onReject?: () => void; isPendingHitl?: boolean; busy?: boolean; }
export function ExplainabilityCard({ data, onApprove, onReject, isPendingHitl, busy = false }: Props) {
  if (!data || !Object.keys(data).length) return null;
  const approved = data.status === "APPROVED_AUTONOMOUS" || data.status === "APPROVED";
  const clarification = data.status === "NEEDS_CLARIFICATION";
  const gated = data.status === "GATED_PENDING_APPROVAL" || data.status === "GATED" || isPendingHitl;
  const rejected = data.status?.includes("REJECT") || data.status?.includes("FAIL");
  const tone = rejected ? "danger" : gated || clarification ? "warning" : approved ? "success" : "neutral";
  const money = (value: number) => `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  const Icon = approved ? ShieldCheck : gated ? ShieldAlert : Info;
  return <section aria-label="Purchase policy decision" aria-busy={busy || undefined} className={`nexus-card p-5 sm:p-6 ${gated ? "border-amber-200" : approved ? "border-emerald-200" : rejected ? "border-rose-200" : ""}`}>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><Icon aria-hidden className={`size-5 ${gated ? "text-amber-700" : approved ? "text-emerald-700" : "text-slate-600"}`} /><h3 className="text-base font-semibold">{data.title || "Purchase policy decision"}</h3></div><StatusBadge tone={tone}>{clarification ? "Clarification required" : rejected ? "Stopped" : gated ? "Approval required" : approved ? "Approved" : "Decision recorded"}</StatusBadge></div>
    <p className="text-sm leading-6 text-slate-600">{data.reasoning || data.reason || "Review the recorded purchase evaluation."}</p>
    {(data.order_total !== undefined || data.budget_cap !== undefined || data.applied_growth_model || data.discount_savings !== undefined) && <dl className="mt-5 grid grid-cols-2 gap-4 rounded-xl bg-slate-50 p-4 text-sm">{data.order_total !== undefined && <div><dt className="text-xs text-slate-500">Order total</dt><dd className="mt-1 font-semibold tabular-nums">{money(data.order_total)}</dd></div>}{data.budget_cap !== undefined && <div><dt className="text-xs text-slate-500">User cap</dt><dd className="mt-1 font-semibold tabular-nums">{money(data.budget_cap)}</dd></div>}{data.applied_growth_model && <div><dt className="text-xs text-slate-500">Pricing strategy</dt><dd className="mt-1">{data.applied_growth_model.replaceAll("_", " ")}</dd></div>}{data.discount_savings !== undefined && Number(data.discount_savings) > 0 && <div><dt className="text-xs text-slate-500">Quote savings</dt><dd className="mt-1 font-semibold tabular-nums text-emerald-700">{money(data.discount_savings)}</dd></div>}</dl>}
    {!!data.violations?.length && <div className="mt-5"><p className="mb-3 text-xs font-semibold text-amber-900">Triggered policy boundaries</p><ul className="space-y-2">{data.violations.map((violation,index) => <li key={index} className="flex items-start gap-2 rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm leading-6 text-amber-900"><ShieldAlert aria-hidden className="mt-1 size-4" />{violation}</li>)}</ul></div>}
    {data.recommendation && <p className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-sm leading-6 text-blue-900">{data.recommendation}</p>}
    {data.tier && <p className="mt-4 break-all text-xs text-slate-500">Policy tier: <span className="font-mono">{data.tier}</span></p>}
    {isPendingHitl && <div className="mt-5 flex flex-wrap justify-end gap-3 border-t border-slate-100 pt-5">{onReject && <Button variant="danger" disabled={busy} onClick={onReject}><X className="size-4" />Reject purchase</Button>}{onApprove && <Button disabled={busy} onClick={onApprove}><Check className="size-4" />{busy ? "Saving decision…" : "Approve purchase"}</Button>}</div>}
  </section>;
}
