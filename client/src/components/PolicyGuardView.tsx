"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  ShieldAlert, 
  Save, 
  CheckCircle2, 
  RefreshCw, 
  Lock, 
  UserCheck,
  SlidersHorizontal,
  Check,
  Zap,
  Shield,
  Trash2,
  CheckCheck
} from "lucide-react";
import { api } from "@/lib/api";
import { ExplainabilityCard } from "./ExplainabilityCard";

interface PolicyGuardViewProps {
  onGateResolved?: () => void;
}

export const PolicyGuardView: React.FC<PolicyGuardViewProps> = ({ onGateResolved }) => {
  const [policy, setPolicy] = useState<any>(null);
  const [pendingGates, setPendingGates] = useState<any[]>([]);
  const [maxTx, setMaxTx] = useState<number>(25000);
  const [dailyVelocity, setDailyVelocity] = useState<number>(50000);
  const [whitelist, setWhitelist] = useState<string[]>([]);
  const [allowUpsell, setAllowUpsell] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [saved, setSaved] = useState<boolean>(false);
  const [resolvingAll, setResolvingAll] = useState<boolean>(false);

  const categories = [
    { id: "monitors", label: "4K Displays & Monitors" },
    { id: "keyboards", label: "Mechanical Keyboards" },
    { id: "mice", label: "Ergonomic Mice" },
    { id: "electronics", label: "Audio & Electronics" },
    { id: "accessories", label: "Desk Hubs & Mats" },
    { id: "subscriptions", label: "Consumables & Subscriptions" },
    { id: "services", label: "Care & Extended Warranties" },
  ];

  const loadData = async () => {
    setLoading(true);
    try {
      const [pol, gates] = await Promise.all([
        api.getPolicyConfig(),
        api.getPendingHITLGates(),
      ]);
      setPolicy(pol);
      setPendingGates(gates);
      setMaxTx(pol.max_tx_amount || 25000);
      setDailyVelocity(pol.daily_velocity_cap || 50000);
      setWhitelist(pol.category_whitelist || []);
      setAllowUpsell(pol.allow_autonomous_upsell || false);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleSavePolicy = async () => {
    setSaving(true);
    try {
      await api.updatePolicyConfig({
        max_tx_amount: maxTx,
        daily_velocity_cap: dailyVelocity,
        category_whitelist: whitelist,
        allow_autonomous_upsell: allowUpsell,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      loadData();
    } catch (err: any) {
      alert("Failed to update policy: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleResolveGate = async (gateId: string, action: string) => {
    try {
      await api.resumeHITLGatedWorkflow(gateId, action);
      loadData();
      if (onGateResolved) onGateResolved();
    } catch (err: any) {
      alert("Failed to resolve gate: " + err.message);
    }
  };

  const handleBatchResolveAll = async (action: string) => {
    setResolvingAll(true);
    try {
      for (const gate of pendingGates) {
        const gid = gate.gate_id || gate.id;
        if (gid) {
          await api.resumeHITLGatedWorkflow(gid, action);
        }
      }
      await loadData();
      if (onGateResolved) onGateResolved();
    } catch (err: any) {
      alert("Batch resolution failed: " + err.message);
    } finally {
      setResolvingAll(false);
    }
  };

  const toggleCategory = (catId: string) => {
    if (whitelist.includes(catId)) {
      setWhitelist(whitelist.filter(c => c !== catId));
    } else {
      setWhitelist([...whitelist, catId]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Adaptive Bounded Safety & HITL Guard
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic 3-tier financial boundaries with 1-click human explainability gating
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          className="btn-secondary self-start sm:self-auto text-xs py-2 px-3 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Gated Queue</span>
        </button>
      </div>

      {/* 3-Tier Architecture Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="nexus-card p-4 bg-emerald-50/50 border-emerald-200">
          <div className="flex items-center justify-between mb-2">
            <span className="nexus-badge badge-emerald text-[10px] font-mono">
              Tier 1 • Autonomous
            </span>
            <Zap className="w-4 h-4 text-emerald-600" />
          </div>
          <h4 className="font-bold text-slate-900 text-xs mb-1">
            Zero-Friction Fastlane
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            Transactions strictly under cap (≤₹{maxTx.toLocaleString()}), whitelisted categories, and matching intent settle autonomously.
          </p>
        </div>

        <div className="nexus-card p-4 bg-amber-50/50 border-amber-200">
          <div className="flex items-center justify-between mb-2">
            <span className="nexus-badge badge-amber text-[10px] font-mono">
              Tier 2 • Gated HITL
            </span>
            <ShieldAlert className="w-4 h-4 text-amber-600" />
          </div>
          <h4 className="font-bold text-slate-900 text-xs mb-1">
            1-Click Escalation Gate
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            Spending cap exceedances or unrequested upsells immediately halt execution and present a 1-click decision card.
          </p>
        </div>

        <div className="nexus-card p-4 bg-rose-50/50 border-rose-200">
          <div className="flex items-center justify-between mb-2">
            <span className="nexus-badge badge-rose text-[10px] font-mono">
              Tier 3 • Hard Block
            </span>
            <Lock className="w-4 h-4 text-rose-600" />
          </div>
          <h4 className="font-bold text-slate-900 text-xs mb-1">
            Non-Negotiable Bounds
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            Daily velocity breaches (&gt;₹{dailyVelocity.toLocaleString()}), non-whitelisted categories, or bad nonces are rejected.
          </p>
        </div>
      </div>

      {/* Pending HITL Gate Queue (Active Gated Transactions) */}
      <div className="nexus-card p-6 bg-white border-slate-200 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-amber-600" />
            <h3 className="font-bold text-slate-900 text-sm">
              Active HITL Gated Queue
            </h3>
          </div>
          
          <div className="flex items-center gap-2">
            <span className={`nexus-badge font-mono text-xs ${
              pendingGates.length > 0 ? 'badge-amber' : 'badge-emerald'
            }`}>
              {pendingGates.length} Pending
            </span>

            {pendingGates.length > 0 && (
              <div className="flex items-center gap-1.5 ml-2">
                <button
                  type="button"
                  onClick={() => handleBatchResolveAll("APPROVE")}
                  disabled={resolvingAll}
                  className="btn-emerald py-1 px-2.5 text-xs font-semibold cursor-pointer"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Authorize All</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleBatchResolveAll("REJECT")}
                  disabled={resolvingAll}
                  className="btn-rose py-1 px-2.5 text-xs font-semibold cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Reject All</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {pendingGates.length > 0 ? (
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {pendingGates.map((gate) => {
              const gateId = gate.gate_id || gate.id;
              const workflowId = gate.workflow_id || gate.order_id || "N/A";
              return (
                <div key={gateId} className="p-3.5 rounded-xl bg-amber-50/40 border border-amber-200/80 space-y-2">
                  <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-amber-200/60">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-amber-900">
                        Gate #{gateId}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        Workflow: {workflowId}
                      </span>
                    </div>
                    <span className="nexus-badge badge-amber text-[10px] font-mono">
                      Tier 2 Intercept
                    </span>
                  </div>

                  <ExplainabilityCard
                    data={gate.explainability_card || {
                      title: "HITL Transaction Boundary Exceeded",
                      reasoning: `Quote total ₹${gate.quote_data?.final_total} exceeds policy limits.`,
                      violations: gate.violations,
                      order_total: gate.quote_data?.final_total,
                      budget_cap: maxTx,
                      applied_growth_model: gate.quote_data?.applied_growth_model,
                      status: "GATED_PENDING_APPROVAL",
                    }}
                    isPendingHitl={true}
                    onApprove={() => handleResolveGate(gateId, "APPROVE")}
                    onReject={() => handleResolveGate(gateId, "REJECT")}
                  />
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center bg-slate-50 rounded-xl border border-slate-200">
            <CheckCircle2 className="w-7 h-7 text-emerald-600 mx-auto mb-1.5" />
            <h4 className="font-bold text-slate-800 text-xs">
              All Policies Enforced & Gated Queue Clean
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">
              No transactions currently held in review. Trigger a workflow exceeding ₹{maxTx.toLocaleString()} to test live gating.
            </p>
          </div>
        )}
      </div>

      {/* Safety Bounds Configuration Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sliders Card */}
        <div className="nexus-card p-6 bg-white border-slate-200 space-y-4">
          <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <SlidersHorizontal className="w-4 h-4 text-blue-600" />
            <h3 className="font-bold text-slate-900 text-sm">
              Financial Boundary Controls
            </h3>
          </div>

          {/* Per Transaction Cap */}
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-700 font-semibold">
                Max Per-Transaction Autonomous Cap
              </span>
              <span className="text-sm font-bold font-mono text-blue-700">
                ₹{maxTx.toLocaleString()}
              </span>
            </div>
            <input
              type="range"
              min={2000}
              max={100000}
              step={1000}
              value={maxTx}
              onChange={(e) => setMaxTx(parseInt(e.target.value))}
              className="w-full cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>₹2,000</span>
              <span>₹25,000</span>
              <span>₹1,00,000</span>
            </div>
          </div>

          {/* Daily Velocity Cap */}
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-700 font-semibold">
                Daily Autonomous Velocity Cap
              </span>
              <span className="text-sm font-bold font-mono text-sky-700">
                ₹{dailyVelocity.toLocaleString()}
              </span>
            </div>
            <input
              type="range"
              min={5000}
              max={200000}
              step={5000}
              value={dailyVelocity}
              onChange={(e) => setDailyVelocity(parseInt(e.target.value))}
              className="w-full cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>₹5,000</span>
              <span>₹50,000</span>
              <span>₹2,00,000</span>
            </div>
          </div>

          {/* Autonomous Upsells Policy Switch */}
          <label 
            onClick={() => setAllowUpsell(!allowUpsell)}
            className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200 cursor-pointer hover:border-slate-300 transition-all select-none"
          >
            <div className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center border transition-all ${
              allowUpsell ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
            }`}>
              {allowUpsell && <Check className="w-3 h-3 stroke-[3]" />}
            </div>
            <div>
              <span className="font-semibold text-slate-800 text-xs block">
                Allow Autonomous Value-Add Upsells (Tier 1)
              </span>
              <span className="text-[11px] text-slate-500 block leading-tight mt-0.5">
                When disabled, any unrequested merchant warranty triggers Tier 2 HITL gating.
              </span>
            </div>
          </label>
        </div>

        {/* Category Whitelist Card */}
        <div className="nexus-card p-6 bg-white border-slate-200 flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
              <Shield className="w-4 h-4 text-emerald-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Whitelisted Product Categories
              </h3>
            </div>
            <p className="text-xs text-slate-500">
              Agent orders outside these permitted categories will be instantly intercepted.
            </p>

            <div className="grid grid-cols-2 gap-2">
              {categories.map((cat) => {
                const isWhitelisted = whitelist.includes(cat.id);
                return (
                  <label
                    key={cat.id}
                    onClick={() => toggleCategory(cat.id)}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer select-none text-xs transition-all ${
                      isWhitelisted
                        ? "bg-blue-50 border-blue-300 text-blue-950 font-medium"
                        : "bg-slate-50 border-slate-200 text-slate-500"
                    }`}
                  >
                    <div className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-all ${
                      isWhitelisted ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
                    }`}>
                      {isWhitelisted && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                    </div>
                    <span className="truncate">{cat.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={handleSavePolicy}
              disabled={saving}
              className="w-full btn-primary py-2.5 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer"
            >
              {saving ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Saving Policy Limits...</span>
                </>
              ) : saved ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Policy Enforced!</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Update & Enforce Policy Sentinel</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
