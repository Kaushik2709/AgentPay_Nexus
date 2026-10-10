"use client";
import { useState } from "react";
import { authClient } from "@/lib/auth-client";
import { demoAccounts } from "@/lib/demo-accounts";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { data: session, isPending } = authClient.useSession();
  const [signup, setSignup] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [needsCode, setNeedsCode] = useState(false);
  const [backup, setBackup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  if (isPending) return <main className="mx-auto max-w-md p-10" role="status">Loading your session…</main>;
  if (session) return <><div className="flex items-center justify-end gap-3 border-b bg-white px-6 py-2 text-sm"><span>{session.user.name}</span><button className="font-medium text-blue-700" onClick={() => { sessionStorage.removeItem("pending-purchase"); void authClient.signOut(); }}>Sign out</button></div>{children}</>;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email")); const password = String(data.get("password"));
    try {
      if (needsCode) {
        const code = String(data.get("code"));
        const result = backup ? await authClient.twoFactor.verifyBackupCode({ code }) : await authClient.twoFactor.verifyTotp({ code, trustDevice: false });
        if (result.error) setError(result.error.message || "Verification failed.");
        return;
      }
      const result = signup ? await authClient.signUp.email({ email, password, name: String(data.get("name")) }) : await authClient.signIn.email({ email, password });
      if (result.error) setError(result.error.message || "Authentication failed.");
      if (result.data && "twoFactorRedirect" in result.data && result.data.twoFactorRedirect) setNeedsCode(true);
    } catch { setError("Unable to reach authentication. Please try again."); }
    finally { setBusy(false); }
  }
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5"><section className="w-full max-w-md rounded-2xl border bg-white p-8 shadow-sm">
    <p className="text-sm font-semibold text-blue-700">AgentPay Nexus</p><h1 className="mt-3 text-2xl font-semibold">{needsCode ? "Verify your sign-in" : signup ? "Create your account" : "Sign in to your workspace"}</h1>
    <p className="mt-2 text-sm text-slate-600">Review purchases, manage spending, and track your orders.</p>
    <form onSubmit={submit} className="mt-6 space-y-4">
      {needsCode ? <label className="block text-sm font-medium">{backup ? "Backup code" : "Authenticator code"}<input name="code" required autoComplete="one-time-code" className="mt-1 w-full rounded-lg border p-3" /></label> : <>
        {signup && <label className="block text-sm font-medium">Name<input name="name" required maxLength={100} autoComplete="name" className="mt-1 w-full rounded-lg border p-3" /></label>}
        <label className="block text-sm font-medium">Email<input name="email" type="email" value={email} onChange={event => setEmail(event.target.value)} required autoComplete="email" className="mt-1 w-full rounded-lg border p-3" /></label>
        <label className="block text-sm font-medium">Password<input name="password" type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={12} autoComplete={signup ? "new-password" : "current-password"} className="mt-1 w-full rounded-lg border p-3" /></label>
        {signup && <p className="text-xs text-slate-500">Use at least 12 characters.</p>}
      </>}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button disabled={busy} className="w-full rounded-lg bg-blue-600 p-3 font-semibold text-white disabled:opacity-50">{busy ? "Please wait…" : needsCode ? "Verify code" : signup ? "Create account" : "Sign in"}</button>
    </form>{needsCode ? <button onClick={() => setBackup(!backup)} className="mt-5 text-sm font-medium text-blue-700">{backup ? "Use authenticator instead" : "Use a backup code"}</button> : <button disabled={busy} onClick={() => { setSignup(!signup); setError(""); }} className="mt-5 text-sm font-medium text-blue-700">{signup ? "Already have an account? Sign in" : "New here? Create an account"}</button>}
    {process.env.NEXT_PUBLIC_DEMO_ACCOUNTS === "true" && !needsCode && <section aria-labelledby="example-accounts" className="mt-6 border-t pt-5">
      <h2 id="example-accounts" className="text-sm font-semibold">Example accounts</h2>
      <p className="mt-1 text-xs text-slate-500">Local demo accounts. Use test payments only.</p>
      <div className="mt-3 space-y-3">{demoAccounts.map(account => <div key={account.role} className="rounded-lg bg-slate-50 p-3 text-sm">
        <p className="font-medium capitalize">{account.role}</p>
        <p className="mt-1 break-all text-slate-600">Email: {account.email}</p>
        <p className="break-all text-slate-600">Password: <code>{account.password}</code></p>
        <button type="button" disabled={busy} onClick={() => { setSignup(false); setError(""); setEmail(account.email); setPassword(account.password); }} className="mt-2 font-medium text-blue-700 disabled:opacity-50">Use {account.role} example</button>
      </div>)}</div>
    </section>}
  </section></main>;
}
