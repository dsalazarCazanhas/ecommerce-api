from sqlmodel import create_engine, SQLModel
from configs.ext import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=True)
# Initialize the Database
def init_db():
    SQLModel.metadata.create_all(engine)