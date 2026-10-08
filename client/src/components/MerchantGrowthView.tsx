"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  TrendingUp, 
  Package, 
  Percent, 
  Save, 
  RefreshCw, 
  Plus, 
  Minus, 
  Receipt,
  Layers,
  Code, 
  Search, 
  Check
} from "lucide-react";
import { api, CatalogProduct, MerchantDashboard } from "@/lib/api";

import { ErrorNotice, errorMessage } from "./Feedback";
import { CatalogSchemaDialog } from "./CatalogSchemaDialog";
import { Button, Dialog, Field, MetricCard, Pagination, Panel, Skeleton, StatePanel, StatusBadge, Toggle } from "./ui";

function InventoryControls({ product, busy, onAdjust }: { product: CatalogProduct; busy: boolean; onAdjust: (delta: number) => void }) {
  return <div className="flex items-center justify-center gap-2">
    <button type="button" aria-label={`Decrease stock for ${product.name}`} disabled={busy || product.stock_quantity === 0}
      onClick={() => onAdjust(-1)} className="flex size-11 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50"><Minus className="size-4" /></button>
    <span className={`w-8 text-center font-mono text-sm font-bold ${product.stock_quantity === 0 ? "text-rose-700" : product.stock_quantity < 5 ? "text-amber-700" : "text-slate-900"}`}>{product.stock_quantity}</span>
    <button type="button" aria-label={`Increase stock for ${product.name}`} disabled={busy}
      onClick={() => onAdjust(1)} className="flex size-11 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50"><Plus className="size-4" /></button>
  </div>;
}

export const MerchantGrowthView: React.FC = () => {
  const [dashboard, setDashboard] = useState<MerchantDashboard | null>(null);
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

  const [error, setError] = useState<string | null>(null);
  const [updatingStock, setUpdatingStock] = useState<string | null>(null);
  const loadData = useCallback(async () => {
    setError(null);
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
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([api.getMerchantDashboard(), api.getProducts()]).then(([dash, prods]) => {
      if (!active) return;
      setDashboard(dash); setProducts(prods);
      setMarginFloor(dash.margin_floor_pct); setActiveModels(dash.active_growth_models);
    }).catch(err => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await api.updateMerchantConfig({ margin_floor_pct: marginFloor, active_growth_models: activeModels });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      await loadData();
    } catch (err) { setError(errorMessage(err)); }
    finally { setSavingConfig(false); }
  };
  const toggleGrowthModel = (key: string) => setActiveModels(current => current.includes(key) ? current.filter(model => model !== key) : [...current, key]);
  const handleQuickStockAdjust = async (sku: string, currentStock: number, delta: number) => {
    if (updatingStock) return;
    setUpdatingStock(sku); setError(null);
    const nextStock = Math.max(0, currentStock + delta);
    try {
      await api.updateProductInventory(sku, { stock_quantity: nextStock });
      setProducts(current => current.map(product => product.sku === sku ? { ...product, stock_quantity: nextStock } : product));
    } catch (err) { setError(errorMessage(err)); }
    finally { setUpdatingStock(null); }
  };
  const filteredProducts = products.filter(product => [product.name, product.sku, product.category].some(value => value.toLowerCase().includes(searchQuery.toLowerCase())));
  const [page, setPage] = useState(0);
  const [confirmRefresh, setConfirmRefresh] = useState(false);
  const pageSize = 6;
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filteredProducts.length / pageSize) - 1));
  const visibleProducts = filteredProducts.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const dirty = dashboard !== null && (marginFloor !== dashboard.margin_floor_pct || JSON.stringify([...activeModels].sort()) !== JSON.stringify([...dashboard.active_growth_models].sort()));
  const money = (value: number) => `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  const strategies = [
    { id: "quality_upgrade", name: "Quality upgrade", tag: "Better product fit", desc: "Propose a higher-spec product when the buyer’s budget and intent allow it." },
    { id: "conversion_closer", name: "Conversion discount", tag: "Price flexibility", desc: "Prepare a discounted quote within the merchant’s configured margin boundary." },
    { id: "bulk_subscription", name: "Bulk / subscription pricing", tag: "Illustrative pricing", desc: "Explore subscription-style pricing. Recurring billing and mandates are not implemented." },
    { id: "value_services", name: "Warranty & care", tag: "Optional service proposal", desc: "Propose a care service when the buyer’s intent and upsell settings permit it." },
  ];
  return <div className="space-y-6">
    <ErrorNotice message={error} />
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-500">Figures reflect records in this demo environment.</p><Button variant="secondary" loading={loading} onClick={() => dirty ? setConfirmRefresh(true) : void loadData()}><RefreshCw className="size-4" />Refresh data</Button></div>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-6">
      <MetricCard label="Recorded revenue" value={dashboard ? money(dashboard.metrics.total_revenue_inr) : null} caption="Orders marked paid" icon={TrendingUp} loading={loading} />
      <MetricCard label="Paid orders" value={dashboard?.metrics.total_orders_completed ?? null} caption="Recorded order status" icon={Check} loading={loading} />
      <MetricCard label="Average order" value={dashboard ? money(dashboard.metrics.total_orders_completed ? dashboard.metrics.avg_order_value_inr : 0) : null} caption="From recorded paid orders" icon={Receipt} loading={loading} />
      <MetricCard label="Discounts granted" value={dashboard ? money(dashboard.metrics.total_discounts_granted_inr) : null} caption="Recorded quote discounts" icon={Percent} loading={loading} />
      <MetricCard label="Catalog products" value={dashboard ? products.length : null} caption="Products in this catalog" icon={Package} loading={loading} />
      <MetricCard label="Stock units" value={dashboard ? products.reduce((total, product) => total + product.stock_quantity, 0) : null} caption="Current catalog inventory" icon={Layers} loading={loading} />
    </div>
    <Panel title="Pricing configuration" description="Choose the strategies the merchant can propose. Save to apply changes to future quotes." actions={<span role="status"><StatusBadge tone={dirty ? "warning" : saveSuccess ? "success" : "neutral"}>{dirty ? "Unsaved changes" : saveSuccess ? "Configuration saved" : "Current configuration"}</StatusBadge></span>}>
      <fieldset disabled={loading || savingConfig || !dashboard} className="space-y-6">
        <div className="grid gap-6 xl:grid-cols-[.65fr_1fr]">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-5"><label htmlFor="merchant-margin" className="flex flex-wrap items-center justify-between gap-3 text-sm font-medium"><span>Merchant margin floor</span><span className="text-2xl font-semibold tabular-nums text-blue-700">{(marginFloor * 100).toFixed(0)}%</span></label><p className="my-4 text-sm leading-6 text-slate-500">Minimum margin used when preparing a quote. Product selection and buyer constraints still apply.</p><input id="merchant-margin" aria-label="Merchant margin floor" type="range" min={0.10} max={0.45} step={0.01} value={marginFloor} onChange={event => setMarginFloor(Number(event.target.value))} /><div className="mt-2 flex justify-between text-xs text-slate-500"><span>10%</span><span>45%</span></div></div>
          <div className="grid gap-3 sm:grid-cols-2">{strategies.map(strategy => <Toggle key={strategy.id} label={strategy.name} description={strategy.desc} checked={activeModels.includes(strategy.id)} onChange={() => toggleGrowthModel(strategy.id)} />)}</div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5"><p className="text-xs text-slate-500">{activeModels.length} of 4 strategies enabled</p><Button onClick={handleSaveConfig} loading={savingConfig} disabled={!dirty}><Save className="size-4" />{savingConfig ? "Saving…" : "Save configuration"}</Button></div>
      </fieldset>
    </Panel>
    <Panel title="Catalog & inventory" description="Search products, adjust stock, and inspect the product schema." actions={<StatusBadge>{products.length} products</StatusBadge>}>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><Field label="Search catalog" htmlFor="catalog-search"><div className="relative"><Search aria-hidden className="pointer-events-none absolute left-3 top-3.5 size-4 text-slate-500" /><input id="catalog-search" value={searchQuery} placeholder="Name, SKU, or category" onChange={event => { setSearchQuery(event.target.value); setPage(0); }} className="nexus-input pl-10 sm:w-80" /></div></Field><p className="text-xs text-slate-500">JSON-LD schemas available</p></div>
      {loading ? <div role="status" aria-label="Loading catalog" className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-20" /></div> : !filteredProducts.length ? <StatePanel compact icon={Package} title={error ? "Catalog unavailable" : "No products found"} description={error ? "Refresh data to try loading the catalog again." : "Try a different name, SKU, or category."} /> : <>
        <div className="grid gap-3 md:hidden">{visibleProducts.map(product => <article key={product.sku} className="rounded-xl border border-slate-200 p-4"><div className="mb-3 flex items-start justify-between gap-3"><h3 className="text-sm font-semibold">{product.name}</h3><StatusBadge tone={product.stock_quantity === 0 ? "danger" : product.stock_quantity < 5 ? "warning" : "neutral"}>{product.stock_quantity === 0 ? "Out of stock" : product.stock_quantity < 5 ? "Low stock" : "In stock"}</StatusBadge></div><p className="break-all font-mono text-xs text-slate-500">{product.sku}</p><p className="mt-2 text-xs capitalize text-slate-500">{product.category}</p><dl className="my-4 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-xs text-slate-500">Retail price</dt><dd className="mt-1 font-semibold tabular-nums">{money(product.retail_price)}</dd></div><div><dt className="text-xs text-slate-500">Cost price</dt><dd className="mt-1 tabular-nums">{money(product.cost_price)}</dd></div><div><dt className="text-xs text-slate-500">Margin</dt><dd className="mt-1">{(product.retail_price ? (1 - product.cost_price / product.retail_price) * 100 : 0).toFixed(1)}%</dd></div></dl><div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4"><InventoryControls product={product} busy={updatingStock !== null} onAdjust={delta => handleQuickStockAdjust(product.sku, product.stock_quantity, delta)} /><Button variant="secondary" aria-label={`Inspect schema for ${product.name}`} onClick={() => setSelectedProductSchema(product)}><Code className="size-4" />Inspect</Button></div></article>)}</div>
        <p className="mb-3 hidden text-xs text-slate-500 md:block xl:hidden">Scroll the table horizontally to see every column.</p>
        <div role="region" aria-label="Product inventory table" tabIndex={0} className="hidden overflow-auto rounded-xl border border-slate-200 md:block"><table className="w-full min-w-[940px] whitespace-nowrap text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-600"><tr>{["Product / SKU", "Category", "Retail price", "Cost price", "Margin", "Stock", "Schema"].map(label => <th key={label} scope="col" className="px-4 py-3 font-medium">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{visibleProducts.map(product => <tr key={product.sku} className="hover:bg-slate-50/60"><td className="min-w-60 max-w-80 whitespace-normal px-4 py-4"><p className="font-medium">{product.name}</p><p className="mt-1 break-all font-mono text-xs text-slate-500">{product.sku}</p></td><td className="px-4"><StatusBadge>{product.category}</StatusBadge></td><td className="px-4 font-medium tabular-nums">{money(product.retail_price)}</td><td className="px-4 tabular-nums text-slate-600">{money(product.cost_price)}</td><td className="px-4 tabular-nums">{(product.retail_price ? (1 - product.cost_price / product.retail_price) * 100 : 0).toFixed(1)}%</td><td className="px-4"><InventoryControls product={product} busy={updatingStock !== null} onAdjust={delta => handleQuickStockAdjust(product.sku, product.stock_quantity, delta)} /></td><td className="px-4"><Button variant="secondary" aria-label={`Inspect schema for ${product.name}`} onClick={() => setSelectedProductSchema(product)}><Code className="size-4" />Inspect</Button></td></tr>)}</tbody></table></div>
      </>}
      {!loading && filteredProducts.length > 0 && <div className="mt-5"><Pagination page={currentPage} pageSize={pageSize} total={filteredProducts.length} onPageChange={setPage} label="products" /></div>}
    </Panel>
    {selectedProductSchema && <CatalogSchemaDialog product={selectedProductSchema} onClose={() => setSelectedProductSchema(null)} />}
    {confirmRefresh && <Dialog title="Discard configuration changes?" id="discard-config-title" onClose={() => setConfirmRefresh(false)}><p className="text-sm leading-6 text-slate-600">Refreshing will replace your unsaved pricing settings with the saved configuration.</p><div className="mt-6 flex flex-wrap justify-end gap-3"><Button variant="secondary" onClick={() => setConfirmRefresh(false)}>Keep editing</Button><Button onClick={() => { setConfirmRefresh(false); void loadData(); }}>Discard & refresh</Button></div></Dialog>}
  </div>;
};
