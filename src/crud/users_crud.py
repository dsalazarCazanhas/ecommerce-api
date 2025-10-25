from sqlmodel import Session, select
from src.models.users import User

def get_user_by_username(username: str, session: Session) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()

def get_user_by_email(email: str, session: Session) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()

def create_user(user: User, session: Session) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def delete_user_by_username(username: str, session: Session) -> bool:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        return False
    session.delete(user)
    session.commit()
    return True

def update_user(user: User, session: Session) -> User | None:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
