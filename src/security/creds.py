import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from src.config.ext import settings

class SecurityManager:
    """Gestor centralizado de seguridad"""
    
    # === PASSWORD MANAGEMENT ===
    def hash_password(self, password: str) -> str:
        """
        Hash password usando bcrypt (ya incluye salt automático)
        Más simple y seguro que doble hashing
        """
        # bcrypt automáticamente genera salt único para cada password
        hashed = bcrypt.hashpw(password=password.encode('utf-8'), salt=bcrypt.gensalt())
        return hashed.decode(encoding='utf-8')  # bcrypt devuelve string directamente
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar password"""
        try:
            return bcrypt.checkpw(password=plain_password.encode('utf-8'), hashed_password=hashed_password.encode(encoding='utf-8'))
        except Exception:
            return False
    
    
    # === JWT MANAGEMENT ===
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Crear JWT token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        })
        encoded_jwt = jwt.encode(claims=to_encode, key=settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verificar y decodificar JWT token"""
        try:
            payload = jwt.decode(
                token=token,
                key=settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            # Validar que tenga campos mínimos esperados
            if "sub" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            return payload

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

# Instancia singleton
security = SecurityManager()