from pydantic_settings import BaseSettings
import secrets

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "DATABASE_URL"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    SESSION_KEY: str = secrets.token_urlsafe(32)
    CSRF_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Cookie
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_HTTPONLY: bool = True
    
    # Admin
    ADMIN_TITLE: str = "E-commerce Admin"
    ADMIN_BASE_URL: str = "/admin"
    
    # CORS
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    ALLOWED_ORIGINS: list[str] = ["http://127.0.0.1", "http://localhost", "http://localhost:8000", "http://localhost:3000"]
    ALLOWED_METHODS: list[str] = ["GET", "POST", "PATCH", "DELETE"]
    
    # App
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "HOST"
    PORT: int = "PORT"
    
    class Config:
        env_file = ".env"

settings = Settings()