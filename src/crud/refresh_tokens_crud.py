# src/crud/refresh_tokens_crud.py
"""
CRUD for the refresh_token table.

All revocation logic is centralized here so reuse-detection rules are applied
consistently regardless of which endpoint triggers them.

References:
    - OWASP ASVS v4.2 3.3 - server-side session revocation
    - RFC 6749 10.4 - refresh token security considerations
    - Auth0 Token Rotation Docs - token family invalidation pattern
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from src.models.auth import RefreshToken


def create(
    *,
    session: Session,
    jti: UUID,
    user_id: UUID,
    family_id: UUID,
    expires_at: datetime,
) -> RefreshToken:
    """
    Persist a newly issued refresh token.

    Called after each successful login and each successful rotation.
    The record is used to validate future /refresh calls and detect reuse.
    """
    record = RefreshToken(
        jti=jti,
        user_id=user_id,
        family_id=family_id,
        expires_at=expires_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_by_jti(*, session: Session, jti: UUID) -> Optional[RefreshToken]:
    """
    Fetch a token by its JWT ID.

    Returns None when the jti was never stored. This can happen with:
        - Tokens issued before Phase 2 deployment (graceful rejection)
        - Forged or tampered tokens
    Both cases are treated as untrusted and rejected by the endpoint.
    """
    return session.get(RefreshToken, jti)


def revoke(*, session: Session, jti: UUID) -> None:
    """
    Mark a single token as revoked.

    Called when:
        - A token is successfully rotated (old jti revoked before issuing the new token)
        - Logout receives a valid, parseable refresh_token cookie
    No-op when the record does not exist or is already revoked.
    """
    record = session.get(RefreshToken, jti)
    if record and not record.is_revoked:
        record.is_revoked = True
        session.add(record)
        session.commit()


def revoke_family(*, session: Session, family_id: UUID) -> None:
    """
    Revoke every active token in a token family.

    Called on reuse detection: a previously rotated jti (is_revoked=True) was
    presented again, indicating possible token theft or replay.
    Revoking the full family forces re-authentication for both attacker and
    legitimate user (token family pattern - RFC 6749 10.4).
    """
    # Select only active family tokens to minimize writes.
    statement = select(RefreshToken).where(
        RefreshToken.family_id == family_id,
        RefreshToken.is_revoked == False,  # noqa: E712 - SQLModel boolean comparison
    )
    records = session.exec(statement).all()
    for record in records:
        record.is_revoked = True
        session.add(record)
    session.commit()
