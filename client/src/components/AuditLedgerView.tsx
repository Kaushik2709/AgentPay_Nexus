"use client";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, AlertTriangle, Copy, FileSearch, ChevronDown } from "lucide-react";
import { api, type AuditEntry, type AuditVerification } from "@/lib/api";
import { ErrorNotice, errorMessage } from "./Feedback";
import { Button, Field, Pagination, Panel, Skeleton, StatePanel, StatusBadge } from "./ui";

export function AuditLedgerView() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [verification, setVerification] = useState<AuditVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null); setVerification(null);
    try {
      const [trail, result] = await Promise.all([api.getAuditTrail(100), api.verifyAuditLedger()]);
      setEntries(trail); setVerification(result);
    } catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    let active = true;
    Promise.all([api.getAuditTrail(100), api.verifyAuditLedger()])
      .then(([trail, result]) => { if (active) { setEntries(trail); setVerification(result); } })
      .catch(err => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function copy(value: string) {
    try { await navigator.clipboard.writeText(value); setCopied(value); }
    catch { setError("Clipboard access is unavailable. Select and copy the hash manually."); }
  }
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 20;
  const actors = [...new Set(entries.map(entry => entry.actor))].sort();
  const actions = [...new Set(entries.map(entry => entry.action))].sort();
  const filtered = entries.filter(entry => JSON.stringify(entry).toLowerCase().includes(query.toLowerCase()) && (!actor || entry.actor === actor) && (!action || entry.action === action));
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / pageSize) - 1));
  const visibleEntries = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const formatDate = (value: string) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); };
  return <div className="space-y-6">
    <ErrorNotice message={error} />
    <Panel title="Ledger integrity" description="Verify the stored hash chain for broken links and modified payloads." actions={<Button variant="secondary" loading={loading} onClick={load}><RefreshCw className="size-4" />{loading ? "Checking…" : "Refresh & verify"}</Button>}>
      {verification ? <div role="status" className={`flex items-start gap-4 rounded-xl border p-5 ${verification.is_valid ? "border-emerald-200 bg-emerald-50/60 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>
        {verification.is_valid ? <ShieldCheck className="mt-0.5 size-6" /> : <AlertTriangle className="mt-0.5 size-6" />}<div><p className="text-base font-semibold">{verification.is_valid ? verification.total_blocks_verified ? "Stored chain verified" : "No entries to verify" : "Integrity check failed"}</p><p className="mt-2 text-sm">{verification.total_blocks_verified} entries checked.{!verification.is_valid && ` Affected entries: ${verification.tampered_blocks.join(", ")}.`}</p></div>
      </div> : loading ? <div role="status" aria-label="Checking ledger integrity"><Skeleton className="h-24" /></div> : <p className="text-sm text-slate-500">Verification is unavailable. Refresh to try again.</p>}
      <p className="mt-4 text-xs leading-5 text-slate-500">Hash chaining provides tamper evidence. This ledger is not independently anchored or immutable.</p>
    </Panel>
    <Panel title="Event explorer" description={`${entries.length} loaded events from the latest 100 records. Filters apply to this loaded dataset.`} actions={<StatusBadge>{filtered.length} matching events</StatusBadge>}>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-[1.4fr_1fr_1fr]"><Field label="Search audit events" htmlFor="audit-search"><input id="audit-search" value={query} placeholder="Actor, action, hash, or payload" onChange={event => { setQuery(event.target.value); setPage(0); }} className="nexus-input" /></Field><Field label="Filter by actor" htmlFor="audit-actor"><select id="audit-actor" value={actor} onChange={event => { setActor(event.target.value); setPage(0); }} className="nexus-select"><option value="">All actors</option>{actors.map(value => <option key={value} value={value}>{value}</option>)}</select></Field><Field label="Filter by action" htmlFor="audit-action"><select id="audit-action" value={action} onChange={event => { setAction(event.target.value); setPage(0); }} className="nexus-select"><option value="">All actions</option>{actions.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></Field></div>
      {loading ? <div role="status" aria-label="Loading recorded events" className="space-y-3"><Skeleton className="h-16" /><Skeleton className="h-16" /><Skeleton className="h-16" /></div> : !filtered.length ? <StatePanel compact icon={FileSearch} title={error ? "Events unavailable" : entries.length ? "No events match your search" : "No recorded events yet"} description={error ? "Refresh the ledger to try again." : entries.length ? "Clear or change the filters to find another event." : "Recorded purchase decisions will appear here."} action={entries.length ? <Button variant="secondary" onClick={() => { setQuery(""); setActor(""); setAction(""); setPage(0); }}>Clear filters</Button> : undefined} /> : <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">{visibleEntries.map(entry => <details key={entry.sequence_number} className="group p-4 open:bg-slate-50/50">
        <summary className="flex min-h-11 list-none flex-wrap items-center gap-3 text-sm"><span className="w-10 shrink-0 font-mono text-xs text-slate-500">#{entry.sequence_number}</span><span className="min-w-0 flex-1"><span className="block font-medium">{entry.action.replaceAll("_", " ")}</span><span className="mt-1 block text-xs text-slate-500">{entry.actor}</span></span><time dateTime={entry.timestamp} title={entry.timestamp} className="text-xs text-slate-500">{formatDate(entry.timestamp)}</time><ChevronDown aria-hidden className="size-4 text-slate-500 transition-transform group-open:rotate-180" /></summary>
        <div className="mt-5 space-y-4">{[["Previous hash", entry.prev_hash], ["Entry hash", entry.entry_hash]].map(([label, hash]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-4"><div className="mb-2 flex items-center justify-between gap-3"><p className="text-xs font-medium text-slate-500">{label}</p><Button variant="ghost" aria-label={`Copy ${label.toLowerCase()} for entry ${entry.sequence_number}`} onClick={() => copy(hash)}><Copy className="size-4" />{copied === hash ? "Copied" : "Copy"}</Button></div><code className="block break-all text-xs leading-6 text-slate-700">{hash}</code></div>)}<p className="text-xs font-medium text-slate-500">Recorded payload</p><pre className="max-h-72 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100">{JSON.stringify(entry.payload, null, 2)}</pre></div>
      </details>)}</div>}
      {copied && <p role="status" className="mt-3 text-xs text-emerald-700">Hash copied to clipboard.</p>}
      {!loading && filtered.length > 0 && <div className="mt-5"><Pagination page={currentPage} pageSize={pageSize} total={filtered.length} onPageChange={setPage} label="events" /></div>}
    </Panel>
  </div>;
}
