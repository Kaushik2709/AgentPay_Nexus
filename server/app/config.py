import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url
from pathlib import Path


def validate_database_pair(async_url, sync_url):
    """Reject split-brain persistence without logging URLs or credentials."""
    left, right = make_url(async_url), make_url(sync_url)
    if left.get_backend_name() != right.get_backend_name():
        raise ValueError("Async and sync database URLs must target the same database.")
    if left.get_backend_name() == "sqlite":
        if not left.database or not right.database or ":memory:" in {left.database, right.database}:
            raise ValueError("Application SQLite configuration requires a persistent shared file.")
        same = Path(left.database).resolve() == Path(right.database).resolve()
    else:
        same = ((left.host, left.port or 5432, left.database, left.username) ==
                (right.host, right.port or 5432, right.database, right.username))
    if not same:
        raise ValueError("Async and sync database URLs must target the same database.")

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentPay Nexus Backend"
    PROJECT_VERSION: str = "1.1.0"
    API_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentpay.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "sqlite:///./agentpay.db")
    
    # Razorpay Test Mode Credentials
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    
    # Merchant Defaults
    DEFAULT_MERCHANT_MARGIN_FLOOR: float = float(os.getenv("DEFAULT_MERCHANT_MARGIN_FLOOR", "0.20"))
    
    # Safety Defaults
    DEFAULT_MAX_TX_AMOUNT: float = float(os.getenv("DEFAULT_MAX_TX_AMOUNT", "25000.0"))
    DEFAULT_DAILY_VELOCITY_CAP: float = float(os.getenv("DEFAULT_DAILY_VELOCITY_CAP", "50000.0"))
    PRICE_DRIFT_TOLERANCE_PCT: float = float(os.getenv("PRICE_DRIFT_TOLERANCE_PCT", "3.0"))
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
