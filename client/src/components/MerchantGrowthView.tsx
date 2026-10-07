"use client";

import React, { useState, useEffect } from "react";
import { 
  TrendingUp, 
  Package, 
  Percent, 
  Save, 
  RefreshCw, 
  Plus, 
  Minus, 
  Sparkles, 
  Code, 
  Search, 
  Check
} from "lucide-react";
import { api, CatalogProduct } from "@/lib/api";

export const MerchantGrowthView: React.FC = () => {
  const [dashboard, setDashboard] = useState<any>(null);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [marginFloor, setMarginFloor] = useState<number>(0.20);
  const [activeModels, setActiveModels] = useState<string[]>([
    "quality_upgrade",
    "conversion_closer",
    "bulk_subscription",
    "value_services",
  ]);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingConfig, setSavingConfig] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedProductSchema, setSelectedProductSchema] = useState<CatalogProduct | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dash, prods] = await Promise.all([
        api.getMerchantDashboard(),
        api.getProducts(),
      ]);
      setDashboard(dash);
      setProducts(prods);
      setMarginFloor(dash.margin_floor_pct || 0.20);
      setActiveModels(dash.active_growth_models || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await api.updateMerchantConfig({
        margin_floor_pct: marginFloor,
        active_growth_models: activeModels,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      loadData();
    } catch (err: any) {
      alert("Failed to save merchant config: " + err.message);
    } finally {
      setSavingConfig(false);
    }
  };

  const toggleGrowthModel = (modelKey: string) => {
    if (activeModels.includes(modelKey)) {
      setActiveModels(activeModels.filter((m) => m !== modelKey));
    } else {
      setActiveModels([...activeModels, modelKey]);
    }
  };

  const handleQuickStockAdjust = async (sku: string, currentStock: number, delta: number) => {
    const nextStock = Math.max(0, currentStock + delta);
    try {
      await api.updateProductInventory(sku, { stock_quantity: nextStock });
      setProducts(products.map(p => p.sku === sku ? { ...p, stock_quantity: nextStock } : p));
    } catch (err: any) {
      alert("Failed to update stock: " + err.message);
    }
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.sku.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const modelsList = [
    {
      id: "quality_upgrade",
      name: "1. Quality Upgrade (Vertical Upsell)",
      tag: "Higher AOV • Zero Clutter",
      desc: "Recommends upgraded 120Hz Creator 4K Monitor (+₹1,500) when budget headroom exists, delivering higher value without unrequested items.",
      margin: "32% Margin Floor",
    },
    {
      id: "conversion_closer",
      name: "2. Conversion Closer (Dynamic Discount)",
      tag: "Instant 2.5% Auto Discount",
      desc: "Applies an autonomous 2.5-4% discount when buyer intent is strict, beating competitor agents to lock in deals before they bounce.",
      margin: "25% Margin Floor",
    },
    {
      id: "bulk_subscription",
      name: "3. Bulk / Subscription (Recurring LTV)",
      tag: "UPI Autopay • 15% Off",
      desc: "15% discount for scheduled recurring replenishment via Razorpay Subscriptions / UPI Autopay. Locks in long-term customer LTV.",
      margin: "20% Margin Floor",
    },
    {
      id: "value_services",
      name: "4. Value-Add Services (Warranty & Care)",
      tag: "90% Gross Margin Add-on",
      desc: "Attaches 2-Year Express Replacement Care (+₹1,200) yielding 90% gross margins with zero physical warehouse overhead.",
      margin: "90% Margin Yield",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Merchant AI Growth & Revenue Engine
            </h2>
            <p className="text-xs text-slate-500">
              Autonomous dynamic pricing algorithms, profit margin floor protection & MCP inventory
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          className="btn-secondary self-start sm:self-auto text-xs py-2 px-3.5 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Live Engine</span>
        </button>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Total Revenue</span>
          <span className="text-xl font-bold text-slate-900 font-mono mt-1 block">
            ₹{Number(dashboard?.total_revenue || 0).toLocaleString()}
          </span>
          <span className="text-[11px] text-emerald-700 font-mono font-semibold flex items-center gap-1 mt-1">
            <TrendingUp className="w-3 h-3" /> Live Settled
          </span>
        </div>

        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Orders Settled</span>
          <span className="text-xl font-bold text-blue-700 font-mono mt-1 block">
            {dashboard?.settled_orders_count || 0}
          </span>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">Razorpay Rails</span>
        </div>

        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Average Order (AOV)</span>
          <span className="text-xl font-bold text-slate-900 font-mono mt-1 block">
            ₹{Number(dashboard?.average_order_value || 23500).toLocaleString()}
          </span>
          <span className="text-[11px] text-emerald-700 font-mono font-semibold mt-1 block">+14.2% AI Lift</span>
        </div>

        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Discounts Granted</span>
          <span className="text-xl font-bold text-purple-700 font-mono mt-1 block">
            ₹{Number(dashboard?.total_discounts_granted || 0).toLocaleString()}
          </span>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">Floor Protected</span>
        </div>

        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Active SKUs</span>
          <span className="text-xl font-bold text-sky-700 font-mono mt-1 block">
            {products.length}
          </span>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">MCP Catalog</span>
        </div>

        <div className="nexus-card p-3.5 bg-white border-slate-200">
          <span className="text-[10px] text-slate-400 uppercase font-mono block font-semibold">Total Stock Units</span>
          <span className="text-xl font-bold text-amber-700 font-mono mt-1 block">
            {products.reduce((acc, p) => acc + (p.stock_quantity || 0), 0)}
          </span>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">Real-time DB</span>
        </div>
      </div>

      {/* Margin Floor & Strategy Switchboard (Side by Side on md+) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Margin Floor Card */}
        <div className="md:col-span-5 nexus-card p-6 bg-white border-slate-200 flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                <Percent className="w-3.5 h-3.5" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">
                Merchant Profit Margin Floor
              </h3>
            </div>
            
            <p className="text-xs text-slate-500 leading-relaxed">
              Autonomous discounts and upgrades are cryptographically bounded and will <strong className="text-slate-800">NEVER</strong> breach this floor.
            </p>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-700 font-semibold">
                  Guaranteed Margin Floor
                </span>
                <span className="text-xl font-extrabold font-mono text-emerald-700">
                  {(marginFloor * 100).toFixed(0)}%
                </span>
              </div>
              
              <input
                type="range"
                min={0.10}
                max={0.45}
                step={0.01}
                value={marginFloor}
                onChange={(e) => setMarginFloor(parseFloat(e.target.value))}
                className="w-full cursor-pointer"
              />

              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>10% (High Volume)</span>
                <span>25% (Balanced)</span>
                <span>45% (High Margin)</span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={handleSaveConfig}
              disabled={savingConfig}
              className="w-full btn-primary py-2.5 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer"
            >
              {savingConfig ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Saving...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Strategy Saved!</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Strategy Configurations</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 4 AI Growth Models Grid */}
        <div className="md:col-span-7 nexus-card p-6 bg-white border-slate-200 space-y-4">
          <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">
                4 Autonomous Growth Models
              </h3>
            </div>
            <span className="nexus-badge badge-blue text-[11px] font-mono font-semibold">
              {activeModels.length} / 4 Active
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {modelsList.map((m) => {
              const isSelected = activeModels.includes(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => toggleGrowthModel(m.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer select-none flex flex-col justify-between ${
                    isSelected
                      ? "bg-blue-50/70 border-blue-300 ring-1 ring-blue-400/30 text-blue-950"
                      : "bg-slate-50 border-slate-200 opacity-70 hover:opacity-100 text-slate-700"
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs leading-snug">
                        {m.name}
                      </span>
                      <div className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-all ${
                        isSelected ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
                      }`}>
                        {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                      </div>
                    </div>
                    
                    <span className="nexus-badge badge-cyan text-[9px] font-mono py-0.2">
                      {m.tag}
                    </span>

                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      {m.desc}
                    </p>
                  </div>

                  <div className="pt-2 mt-2 border-t border-slate-200/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                    <span>Safety Floor:</span>
                    <span className="text-emerald-700 font-bold">{m.margin}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Live Production Catalog & Inventory Table */}
      <div className="nexus-card p-6 bg-white border-slate-200 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-blue-600" />
            <h3 className="font-bold text-slate-900 text-sm">
              Live Production Catalog & MCP Inventory
            </h3>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Search SKU, name, category..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="nexus-input pl-8 py-1.5 text-xs bg-slate-50/50 focus:bg-white"
              />
            </div>
            <span className="nexus-badge badge-blue text-[10px] font-mono whitespace-nowrap py-1">
              MCP / JSON-LD Ready
            </span>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-mono text-[10px] uppercase">
                <th className="py-2.5 px-3 font-semibold">Product / SKU</th>
                <th className="py-2.5 px-3 font-semibold">Category</th>
                <th className="py-2.5 px-3 text-right font-semibold">Retail Price</th>
                <th className="py-2.5 px-3 text-right font-semibold">Cost Price</th>
                <th className="py-2.5 px-3 text-right font-semibold">Margin %</th>
                <th className="py-2.5 px-3 text-center font-semibold">Live Stock</th>
                <th className="py-2.5 px-3 text-center font-semibold">MCP Schema</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans">
              {filteredProducts.map((product) => {
                const marginPct = ((product.retail_price - product.cost_price) / product.retail_price) * 100;

                return (
                  <tr key={product.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900 text-xs">{product.name}</div>
                      <div className="font-mono text-[10px] text-blue-700 font-semibold">{product.sku}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="nexus-badge badge-gray text-[10px]">
                        {product.category}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 text-xs">
                      ₹{product.retail_price.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-500 text-xs">
                      ₹{product.cost_price.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono">
                      <span className={`font-bold text-xs ${marginPct >= 30 ? 'text-emerald-700' : 'text-blue-700'}`}>
                        {marginPct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleQuickStockAdjust(product.sku, product.stock_quantity, -1)}
                          className="w-6 h-6 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center border border-slate-200 transition-colors cursor-pointer"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className={`font-mono font-bold text-xs w-7 text-center ${
                          product.stock_quantity === 0 ? 'text-rose-600' : product.stock_quantity < 5 ? 'text-amber-600' : 'text-slate-900'
                        }`}>
                          {product.stock_quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleQuickStockAdjust(product.sku, product.stock_quantity, 1)}
                          className="w-6 h-6 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center border border-slate-200 transition-colors cursor-pointer"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => setSelectedProductSchema(product)}
                        className="btn-secondary py-1 px-2.5 text-[11px] font-mono flex items-center gap-1 mx-auto cursor-pointer"
                      >
                        <Code className="w-3 h-3 text-sky-600" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON-LD Schema Modal */}
      {selectedProductSchema && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-xl w-full p-5 space-y-4 text-slate-900">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Code className="w-4 h-4 text-sky-600" />
                <h3 className="font-bold text-slate-900 text-sm font-heading">
                  JSON-LD MCP Schema • {selectedProductSchema.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedProductSchema(null)}
                className="text-slate-400 hover:text-slate-700 text-xs font-mono cursor-pointer"
              >
                ✕ Close
              </button>
            </div>

            <pre className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-[11px] font-mono text-slate-800 overflow-x-auto max-h-96">
              {JSON.stringify(selectedProductSchema.json_ld_schema, null, 2)}
            </pre>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedProductSchema(null)}
                className="btn-primary text-xs py-1.5 px-4 cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
