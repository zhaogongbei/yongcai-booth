from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder secret keys that must never be accepted — if a deployment
# copies .env.example verbatim, the app must refuse to start.
_KNOWN_PLACEHOLDER_SECRET_KEYS = frozenset(
    {
        "",
        "generate-a-secret-key-here",
        "change-me",
        "your-secret-key",
        "your-secret-key-here",
        "changeme",
        "secret",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Application
    APP_NAME: str = "AI Booth API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database - default to SQLite for development
    DATABASE_URL: str = "sqlite+aiosqlite:///./aibooth.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0

    # Redis - optional in development
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security - MUST be set via .env or environment variable
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "GET,POST,PUT,DELETE,PATCH"
    CORS_HEADERS: str = "Content-Type,Authorization,X-Request-ID"

    # CSRF Protection
    CSRF_SECRET_KEY: str = ""  # Will default to SECRET_KEY if not set
    CSRF_COOKIE_SECURE: bool = False  # Set True in production
    CSRF_COOKIE_SAMESITE: str = "lax"

    # Security Headers
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self' http://localhost:* https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    PERMISSIONS_POLICY: str = "camera=(self), microphone=(), geolocation=(), payment=(), usb=()"
    # Cloudflare R2 - optional
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "aibooth-storage"
    R2_REGION: str = "auto"

    # Celery - optional
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@aibooth.app"
    SMTP_FROM_NAME: str = "AI Booth"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # AI Services
    OPENAI_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    REPLICATE_API_KEY: str = ""

    # Feature Flags
    ENABLE_AI_FEATURES: bool = True
    ENABLE_ANALYTICS: bool = True
    ENABLE_SUBSCRIPTIONS: bool = True

    @model_validator(mode="after")
    def validate_settings(self):
        # SECRET_KEY must not be empty or a known placeholder value
        if self.SECRET_KEY in _KNOWN_PLACEHOLDER_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY must be a strong random value set via .env or environment variable. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise RuntimeError(
                    "DEBUG must be False in production (ENVIRONMENT=production with DEBUG=True "
                    "leaks SQL/PII to logs). Set DEBUG=False."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "DATABASE_URL must be a PostgreSQL connection string in production. "
                    "SQLite is only supported for development."
                )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
