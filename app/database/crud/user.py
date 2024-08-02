from datetime import datetime

from sqlalchemy.orm import Session
from lib import hash_password
from database.models import User, RefreshToken
from database.schema import UserBase, UserCreate
from bson import ObjectId


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session, page: int, limit: int):
    skip = (page - 1) * limit
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_verified=user.is_verified,
        token=''.join([str(ObjectId()) for _ in range(10)])
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: UserBase):
    db_user = db.query(User).filter(User.id == user_id).first()
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    db.delete(db_user)
    db.commit()
    return db_user


def create_user_refresh_token(db: Session, user_id: int, refresh_token: str, expires_at: datetime):
    db_refresh_token = RefreshToken(user_id=user_id, token=refresh_token, expires_at=expires_at)
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    return db_refresh_token
