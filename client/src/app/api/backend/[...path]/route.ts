import { createHash, createHmac } from "node:crypto";
import { auth } from "@/lib/auth";
import { cookies } from "next/headers";
import { validStepUp } from "@/lib/step-up";

export const runtime = "nodejs";
async function proxy(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return Response.json({ detail: "Sign in to continue." }, { status: 401 });
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    if (!origin || origin !== new URL(request.url).origin)
      return Response.json({ detail: "Invalid request origin." }, { status: 403 });
  }
  const secret = process.env.BACKEND_AUTH_SECRET;
  if (!secret) return Response.json({ detail: "Authentication bridge is not configured." }, { status: 503 });
  const { path } = await context.params;
  if (path.some(segment => !/^[a-zA-Z0-9_-]+$/.test(segment)))
    return Response.json({ detail: "Invalid API path." }, { status: 400 });
  const apiPath = `/api/${path.join("/")}${new URL(request.url).search}`;
  const body = request.method === "GET" ? "" : await request.text();
  const admins = (process.env.ADMIN_USER_IDS || "").split(",").map(value => value.trim());
  const sellers = (process.env.SELLER_USER_IDS || "").split(",").map(value => value.trim());
  const role = admins.includes(session.user.id) ? "admin" : sellers.includes(session.user.id) ? "seller" : "buyer";
  const strong = session.user.twoFactorEnabled && validStepUp((await cookies()).get("nexus-step-up")?.value, session.user.id, session.session.id) ? "1" : "0";
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const digest = createHash("sha256").update(body).digest("hex");
  const signature = createHmac("sha256", secret)
    .update([timestamp, request.method, apiPath, session.user.id, role, strong, digest].join("\n")).digest("hex");
  try {
    const response = await fetch(`${process.env.BACKEND_URL || "http://127.0.0.1:8000"}${apiPath}`, {
      method: request.method, body: body || undefined, cache: "no-store",
      headers: { "Content-Type": "application/json", "X-User-Id": session.user.id,
        "X-User-Role": role, "X-Strong-Auth": strong, "X-Auth-Timestamp": timestamp, "X-Auth-Signature": signature,
        ...(request.headers.get("idempotency-key") ? { "Idempotency-Key": request.headers.get("idempotency-key")! } : {}) },
      signal: AbortSignal.timeout(120000),
    });
    return new Response(await response.text(), { status: response.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ detail: "Backend unavailable. Check your order status before retrying a purchase." }, { status: 503 });
  }
}
export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
