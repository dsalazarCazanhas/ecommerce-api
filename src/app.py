from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.v1.admin import router as admin_router
from src.api.v1.auth import router as auth_router
from src.api.v1.cart import router as cart_router
from src.api.v1.products import router as products_router
from src.api.v1.public import router as public_router
from src.api.v1.stripe import router as stripe_router
from src.api.v1.users import router as users_router
from src.config.engine import Session, engine, init_db
from src.config.ext import settings
from src.crud import idempotency_crud
from src.security.auth import get_current_active_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan context manager"""
    init_db()
    with Session(engine) as session:
        idempotency_crud.prune_stale_records(
            session,
            ttl_hours=settings.IDEMPOTENCY_RECORD_TTL_HOURS,
        )
    yield


# FastAPI app instance
app = FastAPI(
    title="E-commerce API",
    description="API for managing e-commerce operations",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
    www_redirect=settings.TRUSTED_HOST_WWW_REDIRECT,
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MINIMUM_SIZE)

# Routers
app.include_router(
    public_router, prefix=f"{settings.API_V1_STR}", tags=["Public"], dependencies=[]
)

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"],
    dependencies=[],
)

app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])

app.include_router(
    admin_router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["Administration"],
    dependencies=[Depends(get_current_active_admin)],
)

app.include_router(
    products_router,
    prefix=f"{settings.API_V1_STR}/products",
    tags=["Products"],
)

app.include_router(
    cart_router,
    prefix=f"{settings.API_V1_STR}/cart",
    tags=["Cart"],
)

app.include_router(
    stripe_router,
    prefix=f"{settings.API_V1_STR}/stripe",
    tags=["Stripe"],
)

# Static files
app.mount("/static", StaticFiles(directory="statics", html=False), name="static")
