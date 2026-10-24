"""Application configuration loaded from environment variables."""
import os
from urllib.parse import quote_plus


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(os.getenv('DB_USER', 'root'))}:"
        f"{quote_plus(os.getenv('DB_PASSWORD', ''))}@"
        f"{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '3306')}/"
        f"{os.getenv('DB_NAME', 'health_claims_simulator')}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
