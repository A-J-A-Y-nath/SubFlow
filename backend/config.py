import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def normalize_database_url(url: str | None) -> str:
    """
    Ensure the database URL uses the correct SQLAlchemy driver scheme.
    Neon and Heroku provide 'postgres://...', which SQLAlchemy requires
    to be 'postgresql://' or 'postgresql+psycopg2://'.
    """
    if not url:
        # Default to local SQLite database for instant zero-config local development
        base_dir = os.path.abspath(os.path.dirname(__file__))
        return f"sqlite:///{os.path.join(base_dir, 'subflow_dev.db')}"

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


class BaseConfig:
    """Base configuration shared across environments."""
    SECRET_KEY = os.getenv("SECRET_KEY", "subflow-hackathon-super-secret-key-change-in-prod")
    
    # Neon PostgreSQL / SQLAlchemy
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-subflow-secret-key-2026-hackathon")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_HOURS", "8")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30")))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",")

    # API Prefix
    API_PREFIX = "/api/v1"


class DevelopmentConfig(BaseConfig):
    """Development configuration with debugging enabled."""
    DEBUG = True
    ENV = "development"


class TestingConfig(BaseConfig):
    """Testing configuration with fast SQLite in-memory database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-key-32-chars-long-minimum-secure!"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(BaseConfig):
    """Production configuration for deployment."""
    DEBUG = False
    TESTING = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
