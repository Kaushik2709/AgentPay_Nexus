"""Verify server-to-server identities issued after a Better Auth session check."""
import hashlib
import hmac
import os
import time
from contextvars import ContextVar
from fastapi import Request
from starlette.responses import JSONResponse

identity: ContextVar[dict | None] = ContextVar("identity", default=None)

def user_id() -> str:
    current = identity.get()
    return current["id"] if current else "aarav_buyer_01"

def buyer_id() -> str:
    return user_id() if identity.get() else "agent_aarav_99"

def is_admin() -> bool:
    return (identity.get() or {}).get("role") == "admin"

def can_manage_catalog() -> bool:
    return (identity.get() or {}).get("role") in {"seller", "admin"}

async def authenticate(request: Request, call_next):
    path = request.url.path
    if path == "/api/health" or path == "/api/razorpay/webhook":
        return await call_next(request)
    secret = os.getenv("BACKEND_AUTH_SECRET", "")
    uid = request.headers.get("x-user-id", "")
    role = request.headers.get("x-user-role", "")
    strong = request.headers.get("x-strong-auth", "0")
    timestamp = request.headers.get("x-auth-timestamp", "")
    signature = request.headers.get("x-auth-signature", "")
    try:
        fresh = abs(time.time() - int(timestamp)) <= 60
    except ValueError:
        fresh = False
    body = await request.body()
    target = path + ("?" + request.url.query if request.url.query else "")
    message = "\n".join([timestamp, request.method, target, uid, role, strong, hashlib.sha256(body).hexdigest()])
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not secret or not uid or role not in {"buyer", "seller", "admin"} or not fresh or not hmac.compare_digest(expected, signature):
        return JSONResponse({"detail": "A valid Better Auth session is required."}, status_code=401)
    admin_route = path.startswith(("/api/chaos", "/api/audit"))
    merchant_route = path.startswith("/api/merchant") or (path.startswith("/api/catalog") and request.method == "PATCH")
    if merchant_route and role not in {"seller", "admin"}:
        return JSONResponse({"detail": "Seller access required."}, status_code=403)
    if admin_route and role != "admin":
        return JSONResponse({"detail": "Administrator access required."}, status_code=403)
    token = identity.set({"id": uid, "role": role, "strong_auth": strong == "1"})
    try:
        return await call_next(request)
    finally:
        identity.reset(token)
