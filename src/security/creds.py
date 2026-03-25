from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import HTTPException, status

from src.config.ext import settings

# === DATA CLASSES ===


@dataclass
class RefreshTokenData:
    """
    Bundles a newly issued refresh token with the metadata required
    to persist it in the database.

    Returned by SecurityManager.create_refresh_token() so the caller can:
        - Set the cookie with token
        - Insert the DB record with jti, family_id, and expires_at
    without an extra call into the security layer.
    """

    token: str  # Signed JWT ready to be set in a cookie
    jti: UUID  # jti claim - primary key in DB record
    family_id: UUID  # Rotation family inherited by the next refresh token
    expires_at: datetime  # UTC expiry - mirrors the JWT exp claim


# === SECURITY MANAGER ===


class SecurityManager:
    """Security manager for password hashing and JWT handling"""

    # === PASSWORD MANAGEMENT ===
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        """
        hashed = bcrypt.hashpw(password=password.encode("utf-8"), salt=bcrypt.gensalt())
        return hashed.decode(encoding="utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Check password against hashed value"""
        try:
            return bcrypt.checkpw(
                password=plain_password.encode("utf-8"),
                hashed_password=hashed_password.encode(encoding="utf-8"),
            )
        except Exception:
            return False

    # === JWT MANAGEMENT ===
    def _create_token(
        self,
        data: Dict[str, Any],
        token_type: str,
        expires_delta: Optional[timedelta] = None,
        jti: Optional[UUID] = None,
    ) -> str:
        """
        Generic signed JWT factory with standard claims.

        Parameters:
            data          - business payload (for example {"sub": username})
            token_type    - "access" or "refresh", embedded as a claim for
                                            explicit validation in /refresh
            expires_delta - custom lifetime; defaults to ACCESS_TOKEN_EXPIRE_MINUTES
                                            when omitted
            jti           - precomputed UUID from caller. When provided, it ensures
                                            the JWT jti claim and DB primary key are identical.
                                            When omitted, a UUID is generated internally (access tokens).
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                # Use caller-provided jti (Phase 2 refresh tokens) or generate one (access tokens).
                "jti": str(jti) if jti else str(uuid4()),
                "token_type": token_type,
            }
        )
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Issue an access JWT (token_type="access") and return only the token string.

        Access tokens are not persisted in DB. They are short-lived and validated
        cryptographically only (no DB lookup), keeping per-request latency low.
        """
        return self._create_token(
            data=data,
            token_type="access",
            expires_delta=expires_delta,
        )

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        family_id: Optional[UUID] = None,
    ) -> RefreshTokenData:
        """
        Issue a refresh JWT (token_type="refresh") and return DB metadata.

        Unlike create_access_token, this method returns RefreshTokenData so the
        caller can persist the token into refresh_token with the required fields.
        The jti and fid (family_id) claims are embedded in the JWT so /refresh can
        extract them without an extra DB query.

        Parameters:
            family_id - provide during rotation to keep the same session chain;
                                    omit on login to start a new family.
        """
        if expires_delta is None:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Compute jti and family_id here so claims exactly match DB values.
        token_jti = uuid4()
        token_family_id = family_id if family_id is not None else uuid4()
        expires_at = datetime.now(timezone.utc) + expires_delta

        # Embed family_id as fid so /refresh can read it directly from JWT
        # without an additional DB lookup during rotation.
        token_data = {**data, "fid": str(token_family_id)}

        token = self._create_token(
            data=token_data,
            token_type="refresh",
            expires_delta=expires_delta,
            jti=token_jti,
        )

        return RefreshTokenData(
            token=token,
            jti=token_jti,
            family_id=token_family_id,
            expires_at=expires_at,
        )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Check and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            if "sub" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )


security = SecurityManager()
