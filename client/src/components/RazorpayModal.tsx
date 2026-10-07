"use client";

import React, { useState } from "react";
import { 
  X, 
  CreditCard, 
  CheckCircle2, 
  Lock, 
  Download, 
  QrCode
} from "lucide-react";
import confetti from "canvas-confetti";
import { api } from "@/lib/api";

interface RazorpayModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderData: {
    razorpay_order_id: string;
    amount_inr: number;
    currency: string;
    receipt: string;
    key_id: string;
    notes?: Record<string, any>;
  };
  onSuccess: (receipt: any) => void;
}

export const RazorpayModal: React.FC<RazorpayModalProps> = ({
  isOpen,
  onClose,
  orderData,
  onSuccess,
}) => {
  const [paymentMethod, setPaymentMethod] = useState<"card" | "upi">("card");
  const [processing, setProcessing] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [digitalReceipt, setDigitalReceipt] = useState<any>(null);

  if (!isOpen || !orderData) return null;

  const handleSimulatePayment = async () => {
    setProcessing(true);
    try {
      const paymentId = `pay_rzp_${Math.random().toString(36).substring(2, 12)}`;
      const testSecret = process.env.NEXT_PUBLIC_RAZORPAY_KEY_SECRET || "v8x9DUcOfGgUyJwOZ6GeOihJ";
      
      const encoder = new TextEncoder();
      const keyData = encoder.encode(testSecret);
      const msgData = encoder.encode(`${orderData.razorpay_order_id}|${paymentId}`);
      
      const cryptoKey = await window.crypto.subtle.importKey(
        "raw",
        keyData,
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
      );
      const sigBuffer = await window.crypto.subtle.sign("HMAC", cryptoKey, msgData);
      const sigArray = Array.from(new Uint8Array(sigBuffer));
      const signature = sigArray.map(b => b.toString(16).padStart(2, '0')).join('');

      const result = await api.verifyPayment(orderData.razorpay_order_id, paymentId, signature);

      if (result.success) {
        setPaymentSuccess(true);
        setDigitalReceipt(result.digital_receipt);
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 }
        });
        onSuccess(result.digital_receipt);
      }
    } catch (err: any) {
      alert("Payment verification failed: " + err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleDownloadReceipt = () => {
    if (!digitalReceipt) return;
    const blob = new Blob([JSON.stringify(digitalReceipt, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Razorpay_Receipt_${orderData.razorpay_order_id}.json`;
    a.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden transition-all text-slate-900">
        {/* Razorpay Brand Header */}
        <div className="bg-blue-600 text-white p-4 flex items-center justify-between border-b border-blue-700">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center border border-white/20">
              <CreditCard className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold font-heading">Razorpay Test Rails Checkout</div>
              <div className="text-[11px] text-blue-100 font-mono">Order #{orderData.razorpay_order_id}</div>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-blue-100 hover:text-white transition-colors p-1 rounded-md cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!paymentSuccess ? (
          <div className="p-5 space-y-4">
            {/* Amount Banner */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-mono block font-medium">Amount Payable</span>
                <span className="text-xl font-bold font-mono text-slate-900">
                  ₹{Number(orderData.amount_inr).toLocaleString()}
                </span>
              </div>
              <div className="text-right">
                <span className="nexus-badge badge-blue text-[10px] font-mono">
                  Testnet Mode
                </span>
                <span className="text-[10px] text-slate-500 font-mono block mt-1">
                  Receipt: {orderData.receipt}
                </span>
              </div>
            </div>

            {/* Payment Method Switcher */}
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setPaymentMethod("card")}
                className={`py-2 px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  paymentMethod === "card"
                    ? "bg-blue-50 border-blue-300 text-blue-700 shadow-2xs"
                    : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900"
                }`}
              >
                <CreditCard className="w-3.5 h-3.5" />
                <span>Test Card Rails</span>
              </button>

              <button
                onClick={() => setPaymentMethod("upi")}
                className={`py-2 px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  paymentMethod === "upi"
                    ? "bg-blue-50 border-blue-300 text-blue-700 shadow-2xs"
                    : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900"
                }`}
              >
                <QrCode className="w-3.5 h-3.5" />
                <span>UPI / Autopay</span>
              </button>
            </div>

            {/* Simulated Method Details */}
            {paymentMethod === "card" ? (
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-600">
                  <span>Card Number:</span>
                  <span className="text-slate-900 font-medium">•••• •••• •••• 4242</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Expiry:</span>
                  <span className="text-slate-900 font-medium">12 / 28</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Authorization:</span>
                  <span className="text-emerald-700 font-semibold">Pre-Authorized Agent AI</span>
                </div>
              </div>
            ) : (
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-600">
                  <span>VPA Handle:</span>
                  <span className="text-blue-700 font-semibold">agentic_buyer@razorpay</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Protocol:</span>
                  <span className="text-slate-900">NPCI UAP Mandate Rails</span>
                </div>
              </div>
            )}

            {/* HMAC Non-repudiation note */}
            <div className="flex items-center gap-2 text-[11px] text-blue-950 bg-blue-50 p-2.5 rounded-lg border border-blue-200">
              <Lock className="w-4 h-4 text-blue-600 shrink-0" />
              <span>
                Backend verifies cryptographic HMAC-SHA256 signature for non-repudiation before releasing funds.
              </span>
            </div>

            {/* Pay Simulation Button */}
            <button
              onClick={handleSimulatePayment}
              disabled={processing}
              className="w-full btn-emerald py-2.5 text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer"
            >
              {processing ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Verifying HMAC-SHA256 Signature...</span>
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  <span>Authorize & Settle ₹{Number(orderData.amount_inr).toLocaleString()}</span>
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="p-6 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900 font-heading">
                Payment Settled Successfully!
              </h3>
              <p className="text-xs text-slate-500 mt-1 font-mono">
                Order #{orderData.razorpay_order_id} committed to cryptographic ledger
              </p>
            </div>

            {digitalReceipt && (
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-left text-xs font-mono space-y-1.5">
                <div className="flex justify-between text-slate-600">
                  <span>Payment ID:</span>
                  <span className="text-slate-900 font-medium">{digitalReceipt.payment_id}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Amount Settled:</span>
                  <span className="text-emerald-700 font-bold">₹{digitalReceipt.amount_inr}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>HMAC Verified:</span>
                  <span className="text-emerald-700 font-bold">YES (Valid Nonce)</span>
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button
                onClick={handleDownloadReceipt}
                className="flex-1 btn-secondary py-2 text-xs font-semibold flex items-center justify-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Receipt</span>
              </button>

              <button
                onClick={onClose}
                className="flex-1 btn-primary py-2 text-xs font-semibold"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
