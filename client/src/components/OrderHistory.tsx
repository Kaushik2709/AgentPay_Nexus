"use client";
import { useEffect, useState } from "react";
import { api, type AgentWorkflowResponse } from "@/lib/api";
import { RazorpayModal } from "./RazorpayModal";
import { Panel, Button } from "./ui";
type Order = { id: string; status: string; amount_inr: number; created_at: string;
  checkout?: AgentWorkflowResponse["razorpay_order"] };
export function OrderHistory() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [checkout, setCheckout] = useState<AgentWorkflowResponse["razorpay_order"]>();
  async function refresh() {
    try { setOrders(await api.getOrders()); setError(""); }
    catch (error) { setError(error instanceof Error ? error.message : "Order history unavailable."); }
  }
  useEffect(() => {
    let active = true;
    const load = () => api.getOrders().then(value => { if (active) setOrders(value); }).catch(error => { if (active) setError(String(error.message)); });
    void load(); const timer = setInterval(load, 10000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  return <div className="mt-6"><Panel title="Your orders" description="Recover checkout and check payment status after a refresh or interrupted connection." actions={<Button variant="secondary" onClick={refresh}>Refresh orders</Button>}>
    {error && <p role="alert" className="mb-3 text-sm text-red-700">{error}</p>}
    {orders.length === 0 ? <p className="text-sm text-slate-500">No orders yet.</p> : <ul className="divide-y">{orders.map(order => <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 py-4"><div><p className="font-mono text-xs">{order.id}</p><p className="mt-1 text-sm">₹{order.amount_inr.toLocaleString("en-IN")} · {order.status.replaceAll("_", " ")}</p>{order.status.includes("REVIEW") || order.status.includes("RECONCILIATION") ? <p className="mt-1 text-xs text-amber-800">Requires review. Do not pay again.</p> : null}</div>{order.checkout && <Button onClick={() => setCheckout(order.checkout)}>Resume checkout</Button>}</li>)}</ul>}
    {checkout && <RazorpayModal isOpen orderData={checkout} onClose={() => setCheckout(undefined)} onSuccess={() => { setCheckout(undefined); void refresh(); }} />}
  </Panel></div>;
}
