import "server-only";
import { betterAuth } from "better-auth";
import Database from "better-sqlite3";
import { twoFactor } from "better-auth/plugins";

export const auth = betterAuth({
  appName: "AgentPay Nexus",
  plugins: [twoFactor()],
  database: new Database(process.env.BETTER_AUTH_DATABASE || "auth.db"),
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
  emailAndPassword: { enabled: true, minPasswordLength: 12 },
  session: { expiresIn: 60 * 60 * 24 * 7, updateAge: 60 * 60 * 24 },
  rateLimit: { enabled: true, storage: "database", window: 60, max: 30 },
});
