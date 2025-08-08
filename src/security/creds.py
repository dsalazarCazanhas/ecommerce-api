import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from src.config.ext import settings

class SecurityManager:
    """Gestor centralizado de seguridad"""
    
    def __init__(self):
        # Solo si realmente necesitas encriptar tokens (generalmente no es necesario)
        self.cipher_suite = Fernet(settings.ENCRYPTION_KEY) if hasattr(settings, 'ENCRYPTION_KEY') else None
    
    # === PASSWORD MANAGEMENT ===
    
    def hash_password(self, password: str) -> str:
        """
        Hash password usando bcrypt (ya incluye salt automático)
        Más simple y seguro que doble hashing
        """
        # Agregar pepper si quieres capa extra (opcional)
        peppered_password = f"{password}{settings.PASSWORD_PEPPER}" if hasattr(settings, 'PASSWORD_PEPPER') else password
        
        # bcrypt automáticamente genera salt único para cada password
        hashed = bcrypt.hashpw(peppered_password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')  # bcrypt devuelve string directamente
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar password"""
        try:
            # Agregar pepper si se usó al hashear
            peppered_password = f"{plain_password}{settings.PASSWORD_PEPPER}" if hasattr(settings, 'PASSWORD_PEPPER') else plain_password
            
            return bcrypt.checkpw(peppered_password.encode('utf-8'), hashed_password.encode('utf-8'))
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
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar y decodificar JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"]  # ¡Array, no string!
            )
            return payload
        except JWTError:
            return None
    
    # === TOKEN ENCRYPTION (solo si realmente lo necesitas) ===
    
    def encrypt_token(self, token: str) -> str:
        """Encriptar token con Fernet (opcional)"""
        if not self.cipher_suite:
            raise ValueError("Encryption not configured")
        return self.cipher_suite.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Desencriptar token"""
        if not self.cipher_suite:
            raise ValueError("Encryption not configured")
        return self.cipher_suite.decrypt(encrypted_token.encode()).decode()

# Instancia singleton
security = SecurityManager()

# Funciones de conveniencia (mantienen tu API actual)
def hash_password(password: str) -> str:
    return security.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return security.verify_password(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    return security.create_access_token(data, expires_delta)

def verify_token(token: str) -> Optional[dict]:
    return security.verify_token(token)

def encrypt_token(token: str) -> str:
    return security.encrypt_token(token)

def decrypt_token(encrypted_token: str) -> str:
    return security.decrypt_token(encrypted_token)