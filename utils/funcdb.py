from sqlmodel import SQLModel, Session, select

from configs.engine import engine
from src.models.users import User


def get_user_by_username(username: str) -> User:
    with Session(engine) as session:
        result = session.exec(select(User).where(User.username == username))
        return result.first()

def get_total_entries_by_model(model: SQLModel) -> int:
    with Session(engine) as session:
        result = session.exec(select(model)).all()

    return len(result)