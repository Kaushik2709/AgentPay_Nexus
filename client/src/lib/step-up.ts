import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
export function stepUpToken(userId: string, sessionId: string, timestamp: string) {
  return createHmac("sha256", process.env.BACKEND_AUTH_SECRET!)
    .update(["step-up", userId, sessionId, timestamp].join("\n")).digest("hex");
}
export function validStepUp(cookie: string | undefined, userId: string, sessionId: string) {
  if (!cookie || !process.env.BACKEND_AUTH_SECRET) return false;
  const [timestamp, signature] = cookie.split(".");
  if (!timestamp || !signature || !/^\d+$/.test(timestamp) || !/^[a-f0-9]{64}$/.test(signature)) return false;
  const age = Date.now() / 1000 - Number(timestamp);
  if (age < 0 || age > 300) return false;
  return timingSafeEqual(Buffer.from(signature, "hex"), Buffer.from(stepUpToken(userId, sessionId, timestamp), "hex"));
}
