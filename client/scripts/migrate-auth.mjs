import { betterAuth } from "better-auth";
import Database from "better-sqlite3";
import { getMigrations } from "better-auth/db/migration";
import { twoFactor } from "better-auth/plugins";
if (!process.env.BETTER_AUTH_SECRET) throw new Error("BETTER_AUTH_SECRET must be configured.");
const database = new Database(process.env.BETTER_AUTH_DATABASE || "auth.db");
const auth = betterAuth({ database, secret: process.env.BETTER_AUTH_SECRET, plugins: [twoFactor()],
  emailAndPassword: { enabled: true }, rateLimit: { enabled: true, storage: "database" } });
const { runMigrations } = await getMigrations(auth.options);
await runMigrations();
database.close();
console.log("Better Auth schema migrated.");
