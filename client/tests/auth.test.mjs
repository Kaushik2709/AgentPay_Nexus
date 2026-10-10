import assert from "node:assert/strict";
import { test } from "node:test";
import Database from "better-sqlite3";
import { betterAuth } from "better-auth";
import { twoFactor } from "better-auth/plugins";
import { getMigrations } from "better-auth/db/migration";
import { createOTP } from "@better-auth/utils/otp";
import { base32 } from "@better-auth/utils/base32";

test("Better Auth registration, revocation, ownership and TOTP in an ephemeral database", async () => {
  const database = new Database(":memory:");
  const auth = betterAuth({ database, secret: "isolated-test-secret-with-more-than-32-characters",
    baseURL: "http://localhost:3000", emailAndPassword: { enabled: true, minPasswordLength: 12 },
    plugins: [twoFactor()], advanced: { database: { validateSchema: false } } });
  await (await getMigrations(auth.options)).runMigrations();
  let cookie = "";
  async function call(path, body) {
    const response = await auth.handler(new Request(`http://localhost:3000/api/auth/${path}`, {
      method: body ? "POST" : "GET", headers: { "Content-Type": "application/json", "Origin": "http://localhost:3000", Cookie: cookie },
      body: body ? JSON.stringify(body) : undefined }));
    const jar = new Map(cookie.split("; ").filter(Boolean).map(part => [part.slice(0,part.indexOf("=")),part.slice(part.indexOf("=")+1)]));
    for (const raw of response.headers.getSetCookie()) {
      const pair=raw.split(";")[0]; const offset=pair.indexOf("=");
      jar.set(pair.slice(0,offset),pair.slice(offset+1));
    }
    cookie=[...jar].map(([key,value])=>`${key}=${value}`).join("; ");
    return { status: response.status, body: await response.json() };
  }
  try {
    assert.equal((await call("get-session")).body,null);
    const signup=await call("sign-up/email",{email:"memory-test@example.test",password:"MemoryOnly!12345",name:"Memory Test"});
    assert.equal(signup.status,200);
    const session=(await call("get-session")).body;
    assert.equal(session.user.email,"memory-test@example.test");
    const enrollment=await call("two-factor/enable",{password:"MemoryOnly!12345"});
    assert.equal(enrollment.status,200);
    const secret=new TextDecoder().decode(base32.decode(new URL(enrollment.body.totpURI).searchParams.get("secret")));
    assert.equal((await call("two-factor/verify-totp",{code:"wrong"})).status,401);
    assert.equal((await call("two-factor/verify-totp",{code:await createOTP(secret).totp()})).status,200);
    assert.equal((await call("get-session")).body.user.twoFactorEnabled,true);
    assert.equal((await call("sign-out",{})).status,200);
    assert.equal((await call("get-session")).body,null);
    assert.equal((await call("sign-in/email",{email:"memory-test@example.test",password:"WrongPassword123"})).status,401);
    const signin=await call("sign-in/email",{email:"memory-test@example.test",password:"MemoryOnly!12345"});
    assert.equal(signin.body.twoFactorRedirect,true);
    assert.equal((await call("get-session")).body,null);
    assert.equal((await call("two-factor/verify-totp",{code:await createOTP(secret).totp(),trustDevice:false})).status,200);
    assert.equal((await call("get-session")).body.user.id,session.user.id);
  } finally { database.close(); }
});
