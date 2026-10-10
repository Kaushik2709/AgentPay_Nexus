import { betterAuth } from "better-auth";
import Database from "better-sqlite3";
import { twoFactor } from "better-auth/plugins";
import { readFileSync, writeFileSync } from "node:fs";
import { demoAccounts } from "../src/lib/demo-accounts.ts";

const url = process.env.BETTER_AUTH_URL || "http://localhost:3000";
if (process.env.NEXT_PUBLIC_DEMO_ACCOUNTS !== "true" || !["localhost", "127.0.0.1", "[::1]"].includes(new URL(url).hostname))
  throw new Error("Demo seeding requires local Better Auth and NEXT_PUBLIC_DEMO_ACCOUNTS=true.");
if (!process.env.BETTER_AUTH_SECRET) throw new Error("Configure BETTER_AUTH_SECRET first.");
const database = new Database(process.env.BETTER_AUTH_DATABASE || "auth.db");
const auth = betterAuth({ database, secret: process.env.BETTER_AUTH_SECRET, baseURL: url,
  plugins: [twoFactor()], emailAndPassword: { enabled: true, minPasswordLength: 12 } });
try {
  for (const account of demoAccounts) {
    let user = database.prepare('SELECT id FROM "user" WHERE email = ?').get(account.email);
    if (!user) user = (await auth.api.signUpEmail({ body: { name: account.name, email: account.email, password: account.password } })).user;
    // Verify an existing account rather than silently replacing its password.
    await auth.api.signInEmail({ body: { email: account.email, password: account.password } });
    if (account.role === "seller") {
      const ids = new Set((process.env.SELLER_USER_IDS || "").split(",").map(id => id.trim()).filter(Boolean));
      ids.add(user.id);
      let env = readFileSync(".env.local", "utf8");
      const line = `SELLER_USER_IDS=${[...ids].join(",")}`;
      env = /^SELLER_USER_IDS=.*$/m.test(env) ? env.replace(/^SELLER_USER_IDS=.*$/m, line) : `${env.trimEnd()}\n${line}\n`;
      writeFileSync(".env.local", env);
    }
    console.log(`Ready: ${account.role} ${account.email}`);
  }
} finally { database.close(); }
