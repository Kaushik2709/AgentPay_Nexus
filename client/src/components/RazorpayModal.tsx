"use client";
import { useEffect, useRef, useState } from "react";
import { X, CreditCard, Download, CheckCircle2 } from "lucide-react";
import { api, type PaymentReceipt } from "@/lib/api";
import { loadCheckout } from "@/lib/razorpay-checkout";
import { ErrorNotice, errorMessage } from "./Feedback";
import { IconButton } from "./ui";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  orderData: { razorpay_order_id: string; amount_inr: number; currency: string; receipt: string; key_id: string; notes?: Record<string, unknown> };
  onSuccess: (receipt: PaymentReceipt) => void;
}
export function RazorpayModal({ isOpen, onClose, orderData, onSuccess }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [processing, setProcessing] = useState(false);
  const [receipt, setReceipt] = useState<PaymentReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The caller mounts a fresh dialog for each checkout.
  useEffect(() => {
    const element = dialog.current;
    const opener = document.activeElement;
    if (isOpen) element?.showModal();
    return () => { element?.close(); if (opener instanceof HTMLElement) requestAnimationFrame(() => { if (opener.isConnected) opener.focus({ preventScroll: true }); }); };
  }, [isOpen]);
  const reopen = () => { if (dialog.current?.isConnected && !dialog.current.open) dialog.current.showModal(); };
  async function checkout() {
    if (processing || receipt) return;
    setError(null);
    if (!orderData.key_id.startsWith("rzp_test_") || orderData.razorpay_order_id.startsWith("order_rzp_")) {
      setError("This is a placeholder order. Configure Razorpay test credentials on the server and create a new purchase to use checkout.");
      return;
    }
    setProcessing(true);
    try {
      await loadCheckout();
      const payment = new window.Razorpay!({
        key: orderData.key_id, order_id: orderData.razorpay_order_id,
        amount: Math.round(orderData.amount_inr * 100), currency: orderData.currency,
        name: "AgentPay Nexus", description: "Portfolio demo · test payment",
        theme: { color: "#2563eb" },
        modal: { ondismiss: () => { setProcessing(false); reopen(); } },
        handler: async (response) => {
          reopen();
          try {
            const result = await api.verifyPayment(response.razorpay_order_id, response.razorpay_payment_id, response.razorpay_signature);
            if (!result.success) throw new Error(result.message || "Payment verification failed.");
            if (result.status !== "PAID") throw new Error(result.message || "Payment captured; fulfillment needs review.");
            setReceipt(result.digital_receipt);
            onSuccess(result.digital_receipt);
          } catch (err) { setError("Checkout returned a payment, but server verification failed. Do not pay again; inspect the order. " + errorMessage(err)); }
          finally { setProcessing(false); }
        },
      });
      payment.on("payment.failed", (response) => {
        setError(response.error?.description || "The test payment failed. Close checkout to review the order.");
      });
      dialog.current?.close();
      payment.open();
    } catch (err) { setError(errorMessage(err)); setProcessing(false); reopen(); }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = `receipt-${orderData.razorpay_order_id}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <dialog ref={dialog} aria-labelledby="checkout-title" onCancel={event => { event.preventDefault(); if (!processing) onClose(); }}
    className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-2xl border border-slate-200 bg-white p-0 text-slate-900 shadow-xl backdrop:bg-slate-950/50">
    <div className="flex items-center justify-between border-b border-slate-200 p-5">
      <h2 id="checkout-title" className="text-lg font-semibold">Test checkout</h2>
      <IconButton label="Close checkout" disabled={processing} onClick={onClose}><X className="size-5" /></IconButton>
    </div>
    <div className="space-y-5 p-5">
      <ErrorNotice message={error} />
      {receipt ? <>
        <CheckCircle2 className="size-10 text-emerald-700" />
        <h3 className="text-xl font-semibold">Payment verified</h3>
        <p className="text-2xl font-bold">₹{receipt.amount.toLocaleString("en-IN")}</p>
        <p className="break-all text-xs text-slate-500">Payment: {receipt.payment_id}</p>
        <button type="button" onClick={download} className="btn-secondary w-full px-4 py-3"><Download className="size-4" />Download receipt</button>
        <button type="button" onClick={onClose} className="btn-primary w-full px-4 py-3">Done</button>
      </> : <>
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Order total</p>
          <p className="mt-1 text-3xl font-bold">₹{orderData.amount_inr.toLocaleString("en-IN")}</p>
          <p className="mt-3 break-all font-mono text-xs text-slate-500">{orderData.razorpay_order_id}</p>
        </div>
        <p className="text-sm leading-6 text-slate-600">Continue to Razorpay’s test checkout. Use test payment details only. Your payment is verified by the server before a receipt appears.</p>
        <button type="button" disabled={processing} onClick={checkout} className="btn-primary w-full px-4 py-3"><CreditCard className="size-4" />{processing ? "Waiting for checkout…" : "Open Razorpay test checkout"}</button>
      </>}
    </div>
  </dialog>;
}
