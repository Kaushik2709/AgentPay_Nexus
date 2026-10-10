"use client";
import { useCallback, useEffect, useState } from "react";
import { Navbar, sections, type SectionId } from "@/components/Navbar";
import { BuyerSimulatorView } from "@/components/BuyerSimulatorView";
import { MerchantGrowthView } from "@/components/MerchantGrowthView";
import { PolicyGuardView } from "@/components/PolicyGuardView";
import { AuditLedgerView } from "@/components/AuditLedgerView";
import { ChaosLabView } from "@/components/ChaosLabView";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { AuthGate } from "@/components/AuthGate";
import { OrderHistory } from "@/components/OrderHistory";
import { SecuritySettings } from "@/components/SecuritySettings";

export default function Home() {
  return <AuthGate><Workspace /></AuthGate>;
}

function Workspace() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [isSeller, setIsSeller] = useState(false);
  const [activeTab, setActiveTab] = useState<SectionId>("buyer");
  useEffect(() => { api.getIdentity().then(value => { setIsAdmin(value.role === "admin"); setIsSeller(value.role === "seller"); if (value.role === "seller") setActiveTab("merchant"); }).catch(() => { setIsAdmin(false); setIsSeller(false); }); }, []);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const fetchPending = useCallback(async () => {
    try { setPendingCount((await api.getPendingHITLGates()).length); }
    catch { setPendingCount(null); }
  }, []);
  useEffect(() => {
    let active = true;
    api.getPendingHITLGates().then(gates => { if (active) setPendingCount(gates.length); }).catch(() => { if (active) setPendingCount(null); });
    const timer = setInterval(fetchPending, 15000);
    return () => { active = false; clearInterval(timer); };
  }, [fetchPending]);
  const section = sections.find((item) => item.id === activeTab)!;
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} pendingHitlCount={pendingCount} isAdmin={isAdmin} isSeller={isSeller} />
      <div className="flex min-w-0 flex-1 flex-col lg:ml-56">
      <main id="workspace" tabIndex={-1} className="nexus-container workspace-content flex-1 py-6 sm:py-8 focus-visible:outline-none">
        <PageHeader eyebrow="Commerce operations" title={section.label} description={section.description} />
        {/* Preserve the buyer draft; operational screens refresh on entry. */}
        <div hidden={activeTab !== "buyer"}><BuyerSimulatorView onWorkflowComplete={fetchPending} /><OrderHistory /></div>
        {(isAdmin || isSeller) && activeTab === "merchant" && <MerchantGrowthView />}
        {activeTab === "policy" && <div className="space-y-6"><SecuritySettings /><PolicyGuardView onGateResolved={fetchPending} /></div>}
        {isAdmin && activeTab === "audit" && <AuditLedgerView />}
        {isAdmin && activeTab === "chaos" && <ChaosLabView onScenarioRun={fetchPending} />}
      </main>
      <footer className="mt-8 border-t border-slate-200 bg-white py-5">
        <div className="nexus-container flex flex-wrap justify-between gap-2 text-xs text-slate-500">
          <span>AgentPay Nexus · Business-focused AI engineering</span>
          <span>Demo environment · Use test payment credentials only</span>
        </div>
      </footer>
      </div>
    </div>
  );
}
