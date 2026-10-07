"use client";

import React, { useEffect, useState } from "react";
import { 
  Bot, 
  TrendingUp, 
  ShieldCheck, 
  FileCode2, 
  Flame, 
  CreditCard,
  Layers,
  Cpu
} from "lucide-react";
import { api } from "@/lib/api";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingHitlCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, pendingHitlCount }) => {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        await api.getHealth();
        setBackendOnline(true);
      } catch (err) {
        setBackendOnline(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: "buyer", label: "AI Buyer Simulator", icon: Bot },
    { id: "merchant", label: "Merchant Growth Engine", icon: TrendingUp },
    { 
      id: "policy", 
      label: "Policy & HITL Guard", 
      icon: ShieldCheck, 
      badge: pendingHitlCount > 0 ? `${pendingHitlCount} Gated` : null 
    },
    { id: "audit", label: "Cryptographic Ledger", icon: FileCode2 },
    { id: "chaos", label: "Chaos Lab", icon: Flame },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
      <div className="nexus-container py-3 space-y-2.5">
        {/* Brand & System Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-lg tracking-tight">
                  AgentPay <span className="text-blue-600">Nexus</span>
                </span>
                <span className="nexus-badge badge-blue text-[10px] font-mono py-0.5 px-2">
                  Track 01 • Buildathon
                </span>
              </div>
              <p className="text-xs text-slate-500 font-normal">
                Autonomous Multi-Agent Commerce Engine on Razorpay Rails
              </p>
            </div>
          </div>

          {/* System status pills */}
          <div className="flex items-center gap-2">
            <div className={`nexus-badge px-2.5 py-1 text-xs ${
              backendOnline ? 'badge-emerald' : backendOnline === false ? 'badge-rose' : 'badge-gray'
            }`}>
              {backendOnline ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span className="font-mono">FastAPI Live :8000</span>
                </>
              ) : backendOnline === false ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                  <span>Backend Disconnected</span>
                </>
              ) : (
                <span>Checking...</span>
              )}
            </div>

            <div className="nexus-badge badge-blue px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 hidden sm:inline-flex">
              <CreditCard className="w-3.5 h-3.5 text-blue-600" />
              <span>Razorpay Test Rails</span>
            </div>

            <div className="nexus-badge badge-cyan px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 hidden md:inline-flex">
              <Cpu className="w-3.5 h-3.5 text-sky-600" />
              <span>LangGraph</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="bg-slate-100 p-1 rounded-xl flex items-center gap-1 overflow-x-auto border border-slate-200/80 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer select-none ${
                  isActive
                    ? "bg-white text-blue-700 shadow-xs border border-slate-200"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 border border-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className="bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold font-mono px-1.5 py-0.2 rounded-full ml-0.5">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
