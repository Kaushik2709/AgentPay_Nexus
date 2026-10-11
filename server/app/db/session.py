from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings, validate_database_pair
from app.db.models import Base

validate_database_pair(settings.DATABASE_URL, settings.SYNC_DATABASE_URL)

# psycopg async connections require a selector loop on Windows. Uvicorn's
# standard CLI loop setup respects this policy; Linux needs no special setup.
if settings.DATABASE_URL.startswith("postgresql+psycopg"):
    import sys
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Async Engine for FastAPI Routes
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync Engine for initialization / migrations / seeding
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    future=True
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def init_db():
    from app.db.migrations import migrate
    migrate(sync_engine)
