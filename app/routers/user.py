from datetime import timedelta, datetime
from typing import List

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from lib import decode_access_token, verify_password, create_access_token
from database import get_user, create_user, get_user_by_email, get_users, create_user_refresh_token
from database.schema.user import UserCreate, UserBase
from sqlalchemy.orm import Session
from database.database import db_connection
from database import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


async def get_current_user(access_token: str = Depends(oauth2_scheme), db: Session = Depends(db_connection)):
    payload = decode_access_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        return JSONResponse(status_code=400, content="Invalid payload")
    user = get_user_by_email(db, email)
    if user is None:
        return JSONResponse(status_code=404, content="User not found")
    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the necessary permissions",
        )
    return current_user


@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(db_connection)):
    db_user = create_user(db, user)
    return {"message": "User registered successfully", "user_id": db_user.id}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db_connection)):
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content="Incorrect username or password"
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token_expires = timedelta(days=7)
    refresh_token = create_access_token(data={"sub": user.email, "role": user.role},
                                        expires_delta=refresh_token_expires)

    create_user_refresh_token(db, user.id, refresh_token, datetime.utcnow() + refresh_token_expires)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id
    }


@router.get("/all-users", response_model=List[UserBase])
async def get_users_route(skip: int = 0, limit: int = 30, db: Session = Depends(db_connection),
                          current_admin_user: User = Depends(get_current_admin_user)):
    users = get_users(db=db, skip=skip, limit=limit)
    return [user for user in users]


@router.get("/{user_id}", response_model=UserBase)
async def read_user(user_id: int, db: Session = Depends(db_connection)):
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        return JSONResponse(status_code=404, content="User not found")
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(db_connection),
                      current_admin_user: User = Depends(get_current_admin_user)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        return JSONResponse(status_code=404, content="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}
