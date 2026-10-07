"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { BuyerSimulatorView } from "@/components/BuyerSimulatorView";
import { MerchantGrowthView } from "@/components/MerchantGrowthView";
import { PolicyGuardView } from "@/components/PolicyGuardView";
import { AuditLedgerView } from "@/components/AuditLedgerView";
import { ChaosLabView } from "@/components/ChaosLabView";
import { api } from "@/lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>("buyer");
  const [pendingHitlCount, setPendingHitlCount] = useState<number>(0);

  const fetchPendingGates = async () => {
    try {
      const gates = await api.getPendingHITLGates();
      setPendingHitlCount(gates.length);
    } catch (err) {
      // Backend warming up or busy
    }
  };

  useEffect(() => {
    fetchPendingGates();
    const interval = setInterval(fetchPendingGates, 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingHitlCount={pendingHitlCount}
      />

      {/* Main Container - Keeps all views mounted to persist state across tab navigation */}
      <main className="flex-1 py-9">
        <div className="nexus-container">
          <div className={activeTab === "buyer" ? "block" : "hidden"}>
            <BuyerSimulatorView onWorkflowComplete={fetchPendingGates} />
          </div>

          <div className={activeTab === "merchant" ? "block" : "hidden"}>
            <MerchantGrowthView />
          </div>

          <div className={activeTab === "policy" ? "block" : "hidden"}>
            <PolicyGuardView onGateResolved={fetchPendingGates} />
          </div>

          <div className={activeTab === "audit" ? "block" : "hidden"}>
            <AuditLedgerView />
          </div>

          <div className={activeTab === "chaos" ? "block" : "hidden"}>
            <ChaosLabView onScenarioRun={fetchPendingGates} />
          </div>
        </div>
      </main>

      {/* Modern Clean Fintech Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-12 shadow-xs">
        <div className="nexus-container flex flex-col md:flex-row items-center justify-between text-xs text-slate-600 gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-bold text-slate-900 font-heading text-sm">AgentPay Nexus</span>
            <span className="text-slate-300">•</span>
            <span className="font-medium text-slate-600">Razorpay Buildathon 2026</span>
            <span className="text-slate-300">•</span>
            <span className="text-blue-700 font-semibold font-mono">Track 01: AI Growth & Agentic Commerce</span>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
            <span className="flex items-center gap-1.5 font-medium text-slate-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              FastAPI + LangGraph
            </span>
            <span className="text-slate-300">•</span>
            <span>Razorpay Rails</span>
            <span className="text-slate-300">•</span>
            <span>SHA-256 Chain</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
