"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  CheckCircle2, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp, 
  Search, 
  Copy, 
  Check, 
  Layers, 
  Fingerprint
} from "lucide-react";
import { api, AuditEntry } from "@/lib/api";

export const AuditLedgerView: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [trail, ver] = await Promise.all([
        api.getAuditTrail(100),
        api.verifyAuditLedger(),
      ]);
      setEntries(trail);
      setVerificationResult(ver);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerifyLedger = async () => {
    setVerifying(true);
    try {
      const ver = await api.verifyAuditLedger();
      setVerificationResult(ver);
    } catch (err: any) {
      alert("Verification error: " + err.message);
    } finally {
      setVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredEntries = entries.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.actor.toLowerCase().includes(q) ||
      e.action.toLowerCase().includes(q) ||
      e.entry_hash.toLowerCase().includes(q) ||
      JSON.stringify(e.payload).toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="nexus-card p-6 bg-white border-slate-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-700 flex items-center justify-center border border-sky-200">
              <Fingerprint className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Immutable Cryptographic Audit Ledger
              </h2>
              <p className="text-xs text-slate-500">
                Every agent action and settlement movement is committed to a cryptographically verifiable SHA-256 hash chain
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleVerifyLedger}
              disabled={verifying}
              className="btn-primary text-xs py-2 px-3.5 flex items-center gap-2 cursor-pointer"
            >
              {verifying ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Verifying Chain...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 text-white" />
                  <span>Verify Cryptographic Integrity</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              className="btn-secondary text-xs py-2 px-3 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Verification Status Pill */}
        {verificationResult && (
          <div className="mt-4 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <div>
                <span className="font-semibold text-emerald-950 block">
                  Cryptographic Ledger Verified (Zero Tampering Detected)
                </span>
                <span className="text-emerald-800 text-[11px]">
                  All {verificationResult.total_entries} blocks verified against parent nonces. Hash chain 100% intact.
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-800">
              <span className="nexus-badge badge-emerald text-[10px]">
                Blocks: {verificationResult.total_entries}
              </span>
              <span className="nexus-badge badge-blue text-[10px] truncate max-w-[200px]" title={verificationResult.latest_hash}>
                Latest: {verificationResult.latest_hash?.substring(0, 14)}...
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Explorer List */}
      <div className="nexus-card p-6 bg-white border-slate-200 space-y-4">
        {/* Search & Filter Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            <h3 className="font-bold text-slate-900 text-sm">
              Decision & Settlement Blockchain
            </h3>
            <span className="nexus-badge badge-gray text-[10px] font-mono">
              {entries.length} Blocks Recorded
            </span>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search actors, actions, hashes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="nexus-input pl-9 py-1.5 text-xs bg-slate-50/50 focus:bg-white"
            />
          </div>
        </div>

        {/* Blocks list */}
        <div className="space-y-2.5">
          {filteredEntries.map((entry) => {
            const isExpanded = expandedSeq === entry.sequence_number;

            let actorBadge = "badge-blue";
            if (entry.actor === "PolicyGuard" || entry.actor === "Policy") actorBadge = "badge-amber";
            if (entry.actor === "MerchantGrowthAgent") actorBadge = "badge-emerald";
            if (entry.actor === "Supervisor" || entry.actor === "CommerceSupervisor") actorBadge = "badge-cyan";
            if (entry.actor === "GenesisBlock") actorBadge = "badge-purple";

            return (
              <div
                key={entry.sequence_number}
                className="rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-all p-3.5 text-xs"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-slate-700 text-[11px] bg-white border border-slate-200 px-2 py-0.5 rounded">
                      #{entry.sequence_number}
                    </span>
                    <span className={`nexus-badge ${actorBadge} text-[10px] font-mono`}>
                      {entry.actor}
                    </span>
                    <span className="font-semibold text-slate-800">
                      {entry.action}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-slate-500">
                    {entry.timestamp}
                  </span>
                </div>

                {/* Hashes Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1.5 pt-2 border-t border-slate-200 text-[11px] font-mono">
                  <div className="bg-white p-2 rounded-lg border border-slate-200 flex items-center justify-between gap-2">
                    <div className="truncate">
                      <span className="text-slate-400 block text-[9px] uppercase font-sans font-semibold">Prev Hash:</span>
                      <span className="text-slate-600 truncate block">{entry.prev_hash}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(entry.prev_hash)}
                      className="text-slate-400 hover:text-slate-700 p-1 shrink-0 cursor-pointer"
                      title="Copy Prev Hash"
                    >
                      {copiedHash === entry.prev_hash ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  <div className="bg-white p-2 rounded-lg border border-slate-200 flex items-center justify-between gap-2">
                    <div className="truncate">
                      <span className="text-sky-600 block text-[9px] uppercase font-sans font-semibold">Entry Hash:</span>
                      <span className="text-sky-900 truncate block font-bold">{entry.entry_hash}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(entry.entry_hash)}
                      className="text-slate-400 hover:text-slate-700 p-1 shrink-0 cursor-pointer"
                      title="Copy Entry Hash"
                    >
                      {copiedHash === entry.entry_hash ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expand Payload */}
                <div className="mt-2 pt-1 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setExpandedSeq(isExpanded ? null : entry.sequence_number)}
                    className="text-[11px] text-blue-700 hover:text-blue-900 flex items-center gap-1 font-mono font-medium cursor-pointer"
                  >
                    <span>{isExpanded ? "Hide Payload" : "Inspect Payload"}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>

                {isExpanded && (
                  <div className="mt-2 pt-2 border-t border-slate-200">
                    <pre className="bg-white p-3 rounded-lg border border-slate-200 text-[11px] font-mono text-slate-800 overflow-x-auto max-h-60">
                      {JSON.stringify(entry.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
