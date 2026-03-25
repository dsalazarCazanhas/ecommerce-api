from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known placeholder values that must not reach a production deployment.
_WEBHOOK_SECRET_PLACEHOLDERS = frozenset({"", "whsec_replace_me", "whsec_test"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")

    # Security
    SECRET_KEY: str = Field(..., description="JWT secret key")
    SESSION_KEY: str = Field(..., description="Session secret key")
    CSRF_KEY: str = Field(..., description="CSRF secret key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    MAX_FAILED_LOGIN_ATTEMPTS: int = Field(default=5, ge=1)

    # Cookie
    COOKIE_SECURE: bool = Field(default=True)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = Field(default="strict")
    COOKIE_HTTPONLY: bool = Field(default=True)

    # Admin
    ADMIN_TITLE: str = Field(default="E-commerce Admin")
    ADMIN_BASE_URL: str = Field(default="/admin")

    # CORS
    ALLOWED_HOSTS: list[str] = Field(default=["localhost", "127.0.0.1"])
    ALLOWED_ORIGINS: list[str] = Field(
        default=[
            "http://127.0.0.1",
            "http://localhost",
            "http://localhost:8000",
            "http://localhost:3000",
        ]
    )
    ALLOWED_METHODS: list[str] = Field(default=["GET", "POST", "PATCH", "DELETE"])
    ALLOWED_HEADERS: list[str] = Field(
        default=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "Idempotency-Key",
        ]
    )
    TRUSTED_HOST_WWW_REDIRECT: bool = Field(default=False)

    # App
    DEBUG: bool = Field(default=True)
    API_V1_STR: str = Field(default="/api/v1")
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8000, ge=1, le=65535)
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    GZIP_MINIMUM_SIZE: int = Field(default=1000, ge=0)
    IDEMPOTENCY_RECORD_TTL_HOURS: int = Field(default=48, ge=1)

    # Stripe
    # STRIPE_API_KEY  — credentials your server uses to call Stripe's API
    #                   (your server → Stripe).
    # STRIPE_WEBHOOK_SECRET — signing secret Stripe embeds in every webhook
    #                   delivery so you can verify the request truly came from
    #                   Stripe (Stripe → your server).  Stripe generates this
    #                   value and returns it once in the `secret` field when you
    #                   create a WebhookEndpoint:
    #
    #                     stripe.WebhookEndpoint.create(
    #                         enabled_events=["checkout.session.completed", ...],
    #                         url="https://yourdomain.com/api/v1/stripe/webhook",
    #                     )
    #
    #                   Copy the returned `secret` (whsec_...) here.  Without it
    #                   any actor can forge payment events against your webhook.
    STRIPE_API_KEY: str = Field(...)
    STRIPE_WEBHOOK_SECRET: str = Field(default="")

    @field_validator("SECRET_KEY", "SESSION_KEY", "CSRF_KEY")
    @classmethod
    def validate_secret_key_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("Secret keys must be at least 32 characters long")
        return value

    @model_validator(mode="after")
    def validate_stripe_webhook_secret_in_production(self) -> "Settings":
        """Prevent startup in production with a missing or placeholder webhook secret.

        STRIPE_WEBHOOK_SECRET is the HMAC-SHA256 signing key Stripe embeds in
        every webhook delivery.  Omitting it disables signature verification and
        allows any unauthenticated actor to forge payment events.
        Reference: https://docs.stripe.com/webhooks#verify-official-libraries
        """
        if self.ENVIRONMENT == "production":
            if self.STRIPE_WEBHOOK_SECRET in _WEBHOOK_SECRET_PLACEHOLDERS:
                raise ValueError(
                    "STRIPE_WEBHOOK_SECRET must be set to a real whsec_... value "
                    "in production.  Obtain it by calling "
                    "stripe.WebhookEndpoint.create() and saving the returned "
                    "`secret` field."
                )
        return self


settings = Settings()
