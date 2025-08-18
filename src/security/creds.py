import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
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
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')  # bcrypt devuelve string directamente
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar password"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
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
        print(settings.SECRET_KEY)
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar y decodificar JWT token"""
        try:

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            return payload
        except JWTError:
            return None

# Instancia singleton
security = SecurityManager()