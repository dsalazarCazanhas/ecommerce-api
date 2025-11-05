from sqlmodel import SQLModel, create_engine, Session
from src.config.ext import settings

# SqlModel engine setup
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def init_db():
    """Initialize the database and create tables"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Function to get the database session"""
    with Session(engine) as session:
        yield session