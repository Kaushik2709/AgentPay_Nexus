import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

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
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_TUTtQXLU7uisGX")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "v8x9DUcOfGgUyJwOZ6GeOihJ")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "nexus_webhook_sec_44332211")
    
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
