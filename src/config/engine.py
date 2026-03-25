from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from src.config.ext import settings

# SqlModel engine setup
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True)


def init_db():
    """Initialize the database and create tables.

    Importing src.models here guarantees every SQLModel table class is loaded
    into the shared metadata/mapper registry before create_all() runs.
    This avoids partial registration bugs during real application startup.
    """
    import src.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Function to get the database session"""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
