# src/models/auth.py

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

"""
RefreshToken - persistent record for each issued refresh token.

Enables server-side session control following:
    - OWASP ASVS v4.2 3.3 - individual token revocation
    - RFC 6749 10.4 - refresh token security considerations
    - Auth0 Rotation Docs - token family invalidation on reuse detection

Design notes:
    - The table is append-only during normal operation; tokens are revoked,
        never deleted while still relevant.
    - jti (JWT ID) is the PK - identical to the signed JWT jti claim.
    - Expired records should be periodically purged (background task,
        outside the scope of this module).
    - family_id groups all tokens from the same session chain; reuse detection
        revokes the entire family to force re-authentication.
"""


class RefreshToken(SQLModel, table=True):
    """
    One row per issued refresh token.
    Primary key: JWT jti claim, enabling O(1) lookup on every /refresh.
    """

    __tablename__ = "refresh_token"

    # JWT jti claim - always provided by the caller, never auto-generated here.
    # Allows invalidating or fetching an exact token without decoding the JWT.
    jti: UUID = Field(
        primary_key=True,
        description=(
            "JWT ID claim - unique identifier for this token. "
            "Matches the signed JWT jti claim exactly."
        ),
    )

    # Owner user FK - required for audit queries and family-level revocation.
    user_id: UUID = Field(
        foreign_key="user.id",
        index=True,
        description="User who owns this token.",
    )

    # All tokens generated through rotations of the same session share family_id.
    # When reuse is detected (replayed stolen token), the full family is revoked:
    # both attacker and legitimate user are forced to authenticate again.
    family_id: UUID = Field(
        index=True,
        description=(
            "Rotation family - all login rotations share this identifier. "
            "The entire family is revoked when reuse is detected."
        ),
    )

    # Soft-delete flag: True after successful rotation, logout, or reuse detection.
    # Hard-delete is intentionally avoided during normal operation.
    is_revoked: bool = Field(
        default=False,
        description="True when this token has been invalidated.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Issue timestamp (UTC).",
    )

    # Stored to support cleanup queries without decoding JWTs.
    # Mirrors the corresponding JWT exp claim.
    expires_at: datetime = Field(
        description="Expiration timestamp (UTC) - mirrors the JWT exp claim.",
    )


class IdempotencyStatus(str, Enum):
    """Lifecycle state for a persisted idempotency key."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IdempotencyRecord(SQLModel, table=True):
    """Server-side idempotency record bound to user and key."""

    __tablename__ = "idempotency_record"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            "scope",
            name="uq_idempotency_user_key_scope",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    scope: str = Field(index=True, min_length=1, max_length=64)
    idempotency_key: str = Field(index=True, min_length=1, max_length=64)
    request_hash: str = Field(min_length=64, max_length=64)
    status: IdempotencyStatus = Field(default=IdempotencyStatus.PROCESSING)
    response_status_code: int | None = Field(default=None)
    response_body: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
