"use client";
import { useState } from "react";
import { authClient } from "@/lib/auth-client";
import { Panel, Button } from "./ui";
export function SecuritySettings() {
  const { data: session } = authClient.useSession();
  const [enrollment, setEnrollment] = useState<{ secret: string; codes: string[] }>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const enabled = session?.user.twoFactorEnabled;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    const form = event.currentTarget; const data = new FormData(form);
    try {
      if (!enabled && !enrollment) {
        const result = await authClient.twoFactor.enable({ password: String(data.get("password")) });
        if (result.error) throw new Error(result.error.message);
        if (result.data && "totpURI" in result.data) setEnrollment({ secret: new URL(result.data.totpURI).searchParams.get("secret") || "", codes: result.data.backupCodes });
      } else if (!enabled) {
        const result = await authClient.twoFactor.verifyTotp({ code: String(data.get("code")), trustDevice: false });
        if (result.error) throw new Error(result.error.message);
        setEnrollment(undefined); setMessage("Authenticator enabled. Keep your backup codes in a safe place.");
        await authClient.getSession();
      } else {
        const response = await fetch("/api/step-up", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: String(data.get("code")) }) });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Verification failed.");
        setMessage("High-value approvals are unlocked for five minutes in this session.");
      }
      form.reset();
    } catch (error) { setError(error instanceof Error ? error.message : "Verification failed."); }
    finally { setBusy(false); }
  }
  return <Panel title="Account security" description="Use an authenticator app to protect sign-in and authorize high-value purchases.">
    {enrollment && <div className="mb-4 rounded-lg border bg-slate-50 p-4 text-sm"><p>Add this setup key to your authenticator as a time-based account:</p><code className="mt-2 block break-all">{enrollment.secret}</code><p className="mt-4 font-medium">Save these recovery codes before continuing:</p><pre className="mt-2 whitespace-pre-wrap text-xs">{enrollment.codes.join("\n")}</pre></div>}
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      {!enabled && !enrollment ? <label className="text-sm font-medium">Confirm your password<input required name="password" type="password" autoComplete="current-password" className="mt-1 block rounded-lg border p-3" /></label> : <label className="text-sm font-medium">Authenticator code<input required name="code" inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" className="mt-1 block rounded-lg border p-3" /></label>}
      <Button type="submit" loading={busy}>{enabled ? "Verify high-value approvals" : enrollment ? "Confirm authenticator" : "Set up authenticator"}</Button>
    </form>{error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}{message && <p role="status" className="mt-3 text-sm text-emerald-700">{message}</p>}
  </Panel>;
}
