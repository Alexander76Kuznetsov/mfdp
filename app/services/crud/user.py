from models.all_models import User
from typing import List, Optional
import bcrypt


def get_all_users(session) -> List[User]:
    return session.query(User).all()

def get_user_by_id(id: int, session) -> Optional[User]:
    users = session.get(User, id) 
    if users:
        return users 
    return None

def get_user_by_username(username: str, session) -> Optional[User]:
    user = session.query(User).filter(User.username == username).first()
    if user:
        return user 
    return None

def get_user_by_email(email: str, session) -> Optional[User]:
    user = session.query(User).filter(User.email == email).first()
    if user:
        return user 
    return None

def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed
    
def create_user(new_user: User, session) -> None:
    session.add(new_user) 
    session.commit() 
    session.refresh(new_user)