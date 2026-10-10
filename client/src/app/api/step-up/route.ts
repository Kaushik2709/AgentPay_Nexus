import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { stepUpToken } from "@/lib/step-up";
export const runtime = "nodejs";
export async function POST(request: Request) {
  if (request.headers.get("origin") !== new URL(request.url).origin)
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session?.user.twoFactorEnabled) return NextResponse.json({ detail: "Enable authenticator verification first." }, { status: 403 });
  if (!process.env.BACKEND_AUTH_SECRET) return NextResponse.json({ detail: "Authentication bridge unavailable." }, { status: 503 });
  let code: unknown;
  try { code = (await request.json()).code; } catch { return NextResponse.json({ detail: "Invalid request." }, { status: 400 }); }
  if (typeof code !== "string" || !/^\d{6}$/.test(code)) return NextResponse.json({ detail: "Enter a six-digit authenticator code." }, { status: 422 });
  // Use the HTTP handler so Better Auth's endpoint rate limits also apply.
  const verification = await auth.handler(new Request(new URL("/api/auth/two-factor/verify-totp", request.url), {
    method: "POST", headers: request.headers, body: JSON.stringify({ code, trustDevice: false }) }));
  if (!verification.ok) return NextResponse.json({ detail: "Authenticator verification failed. Try a fresh code." }, { status: verification.status });
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const response = NextResponse.json({ success: true, expiresIn: 300 });
  response.cookies.set("nexus-step-up", `${timestamp}.${stepUpToken(session.user.id, session.session.id, timestamp)}`, {
    httpOnly: true, secure: process.env.NODE_ENV === "production" && request.url.startsWith("https:"), sameSite: "strict", path: "/", maxAge: 300 });
  return response;
}
