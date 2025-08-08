from sqlmodel import SQLModel, create_engine, Session
from src.config.ext import settings

# Engine con SQLModel
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def init_db():
    """Inicializar base de datos"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency para obtener sesión de DB"""
    with Session(engine) as session:
        yield session