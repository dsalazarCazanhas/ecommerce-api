from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.config.engine import init_db
from src.config.ext import settings
from src.api.v1.users import router as users_router
from src.api.v1.auth import router as auth_router
from src.api.v1.admin import router as admin_router
from src.api.v1.public import router as public_router
from src.security.auth import get_current_active_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la app"""
    init_db()
    yield

# Crear app FastAPI
app = FastAPI(
    title="E-commerce API",
    description="API for managing e-commerce operations",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET","POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Incluir routers

app.include_router(
    public_router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Public"]
)

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["Users"]
)

app.include_router(
    admin_router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["Administration"],
    dependencies=[Depends(get_current_active_admin)]
)

# Archivos estáticos
app.mount("/static", StaticFiles(directory="./statics"), name="static")

