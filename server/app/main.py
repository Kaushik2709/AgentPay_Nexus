import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import authenticate, user_id, identity
from app.config import settings
from app.db.seed import seed_database
from app.api.catalog_router import router as catalog_router
from app.api.agent_router import router as agent_router
from app.api.razorpay_router import router as razorpay_router
from app.api.policy_router import router as policy_router
from app.api.merchant_router import router as merchant_router
from app.api.audit_router import router as audit_router
from app.api.chaos_router import router as chaos_router

import sys
import io
import asyncio
from contextlib import suppress

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed DB with real catalog items, policies, merchant info & genesis block
    print(f"[STARTUP] Initializing {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}...")
    seed_database()
    from app.maintenance import maintain_orders
    maintenance = asyncio.create_task(maintain_orders())
    print("[STARTUP] Real catalog, policies, and cryptographic genesis ledger initialized.")
    yield
    maintenance.cancel()
    with suppress(asyncio.CancelledError):
        await maintenance
    # Shutdown
    print("[SHUTDOWN] Shutting down AgentPay Nexus backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Autonomous Multi-Agent Commerce & Settlement Engine on Razorpay Test Rails",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in settings.CORS_ORIGINS if origin != "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(authenticate)

@app.get("/api/me")
async def current_identity():
    return {"user_id": user_id(), "role": (identity.get() or {}).get("role", "buyer")}

# Mount all API routers
app.include_router(catalog_router, prefix=settings.API_PREFIX)
app.include_router(agent_router, prefix=settings.API_PREFIX)
app.include_router(razorpay_router, prefix=settings.API_PREFIX)
app.include_router(policy_router, prefix=settings.API_PREFIX)
app.include_router(merchant_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(chaos_router, prefix=settings.API_PREFIX)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": "production_testnet",
        "payment_rails": "Razorpay Test-Mode APIs",
        "agent_protocol": "AgentPay ACP / MCP JSON-LD"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
