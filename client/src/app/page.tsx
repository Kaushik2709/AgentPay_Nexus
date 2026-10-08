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

export default function Home() {
  const [activeTab, setActiveTab] = useState<SectionId>("buyer");
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
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} pendingHitlCount={pendingCount} />
      <div className="flex flex-1 flex-col lg:ml-56">
      <main id="workspace" tabIndex={-1} className="nexus-container workspace-content flex-1 py-6 sm:py-8 focus-visible:outline-none">
        <PageHeader eyebrow="Commerce operations" title={section.label} description={section.description} />
        {/* Preserve the buyer draft; operational screens refresh on entry. */}
        <div hidden={activeTab !== "buyer"}><BuyerSimulatorView onWorkflowComplete={fetchPending} /></div>
        {activeTab === "merchant" && <MerchantGrowthView />}
        {activeTab === "policy" && <PolicyGuardView onGateResolved={fetchPending} />}
        {activeTab === "audit" && <AuditLedgerView />}
        {activeTab === "chaos" && <ChaosLabView onScenarioRun={fetchPending} />}
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
