import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.config.engine import init_db
from src.config.ext import settings
from src.api.v1.users import router as users_router
from src.api.v1.auth import router as auth_router

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
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Incluir routers

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["Users"]
)

# Archivos estáticos
app.mount("/static", StaticFiles(directory="./statics"), name="static")

# Favicon endpoint
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join('statics', 'favicon.ico'))

# Estado de la app endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Endpoints básicos
@app.get("/")
async def read_root():
    return {
        "title": app.title,
        "description": app.description,
        "version": app.version
    }

