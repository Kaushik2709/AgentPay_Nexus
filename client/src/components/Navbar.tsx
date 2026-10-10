"use client";
import { useEffect, useState } from "react";
import { Bot, TrendingUp, ShieldCheck, FileCode2, Flame, Layers, Menu, CircleHelp } from "lucide-react";
import { api } from "@/lib/api";
import { Dialog, IconButton, StatusBadge } from "./ui";
export const sections = [
  { id: "buyer", label: "Buyer workspace", icon: Bot, description: "From purchase intent to a considered decision. Create a request and review its quote." },
  { id: "merchant", label: "Merchant operations", icon: TrendingUp, description: "A clear view of your catalog, pricing strategies, and recorded commerce activity." },
  { id: "policy", label: "Policies & approvals", icon: ShieldCheck, description: "Keep spending within bounds. Review exceptions and configure your purchasing policy." },
  { id: "audit", label: "Audit trail", icon: FileCode2, description: "Follow the evidence behind each decision and check the stored ledger’s integrity." },
  { id: "chaos", label: "Scenario lab", icon: Flame, description: "Explore scripted failure paths and compare expectations with recorded outcomes." },
] as const;
export type SectionId = typeof sections[number]["id"];
interface NavbarProps { activeTab: SectionId; setActiveTab: (tab: SectionId) => void; pendingHitlCount: number | null; isAdmin?: boolean; isSeller?: boolean; }
export function Navbar({ activeTab, setActiveTab, pendingHitlCount, isAdmin = false, isSeller = false }: NavbarProps) {
  const [online, setOnline] = useState<boolean | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    let disposed = false;
    async function check() { try { await api.getHealth(); if (!disposed) setOnline(true); } catch { if (!disposed) setOnline(false); } }
    void check(); const timer = setInterval(check, 15000);
    return () => { disposed = true; clearInterval(timer); };
  }, []);
  function navigate(id: SectionId) {
    setActiveTab(id); setMenuOpen(false);
    requestAnimationFrame(() => requestAnimationFrame(() => { document.getElementById("workspace")?.focus({ preventScroll: true }); window.scrollTo({ top: 0 }); }));
  }
  const nav = (mobile: boolean) => <nav aria-label={mobile ? "Mobile workspace sections" : "Workspace sections"} className="space-y-1.5">
    {sections.filter(section => isAdmin || (isSeller && section.id === "merchant") || ["buyer", "policy"].includes(section.id)).map(({ id, label, icon: Icon }) => <button key={id} type="button" onClick={() => navigate(id)} aria-current={activeTab === id ? "page" : undefined}
      className={`flex min-h-12 w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium transition-colors ${mobile ? activeTab === id ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50" : activeTab === id ? "bg-white/10 text-white ring-1 ring-white/10" : "text-slate-300 hover:bg-white/5 hover:text-white"}`}>
      <Icon aria-hidden className={`size-[18px] ${activeTab === id && !mobile ? "text-blue-300" : ""}`} /><span className="flex-1">{label}</span>
      {id === "policy" && pendingHitlCount !== null && pendingHitlCount > 0 && <span className={`rounded px-1.5 py-0.5 text-xs ${mobile ? "bg-amber-50 text-amber-800" : "bg-amber-300/10 text-amber-200"}`}>{pendingHitlCount}</span>}
    </button>)}
  </nav>;
  return <>
    <aside aria-label="Application sidebar" className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col bg-[#101828] p-4 lg:flex">
      <div className="mb-10 flex items-center gap-3 px-2 pt-4"><div className="flex size-9 items-center justify-center rounded-xl bg-blue-600 text-white"><Layers aria-hidden className="size-5" /></div><div><p className="text-base font-semibold tracking-tight text-white">AgentPay Nexus</p><p className="mt-0.5 text-xs text-slate-400">Commerce workspace</p></div></div>
      <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[.16em] text-slate-400">Workspace</p>{nav(false)}
      <div className="mt-auto rounded-xl border border-white/10 bg-white/5 p-4"><CircleHelp aria-hidden className="mb-3 size-5 text-blue-300" /><p className="text-sm font-medium text-white">Built for considered decisions</p><p className="mt-2 text-xs leading-5 text-slate-300">AI proposals. Spending boundaries. Human oversight.</p><div className="mt-4 flex items-center gap-2 text-xs text-slate-400"><span className="size-1.5 rounded-full bg-blue-300" />Portfolio environment</div></div>
    </aside>
    <header className="border-b border-slate-200 bg-white lg:ml-56">
      <div className="nexus-container flex min-h-20 flex-wrap items-center justify-between gap-3 py-3">
        <div className="flex min-w-0 items-center gap-3"><div className="lg:hidden"><IconButton label="Open workspace menu" aria-haspopup="dialog" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu className="size-5" /></IconButton></div><div><p className="text-sm font-medium text-slate-900 lg:hidden">AgentPay Nexus</p><p className="text-xs text-slate-500 lg:text-sm">Workspace <span className="mx-2 text-slate-300">/</span><span className="text-slate-700">{sections.find(section => section.id === activeTab)?.label}</span></p></div></div>
        <div className="flex items-center gap-3"><span className="hidden sm:inline-flex"><StatusBadge tone="info">Test environment</StatusBadge></span><span role="status"><StatusBadge tone={online === null ? "neutral" : online ? "success" : "danger"}><span className="size-1.5 rounded-full bg-current" />{online === null ? "Connecting" : online ? "API connected" : "API unavailable"}</StatusBadge></span></div>
      </div>
    </header>
    {menuOpen && <Dialog title="Workspace navigation" id="workspace-navigation-title" onClose={() => setMenuOpen(false)}>{nav(true)}<p className="mt-6 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">Portfolio demonstration · Razorpay test environment</p></Dialog>}
  </>;
}
