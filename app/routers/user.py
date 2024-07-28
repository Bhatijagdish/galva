import json
import os
from datetime import timedelta, datetime
from typing import List

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from lib import decode_access_token, verify_password, create_access_token, send_email, hash_password
from database import get_user, create_user, get_user_by_email, get_users, create_user_refresh_token
from database.schema.user import UserBase, UserOut, UserInDB, UserSignIn, UserPasswordReset, UserCreate
from sqlalchemy.orm import Session
from database.database import db_connection
from database import User
from bson import ObjectId
from loguru import logger

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/signin")
sender_email = os.getenv("EMAIL")
sender_email_pssword = os.getenv("PASSWORD")


async def get_current_user(access_token: str = Depends(oauth2_scheme),
                           db: Session = Depends(db_connection)):
    payload = decode_access_token(access_token)
    logger.success(payload)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid payload")
    user = get_user_by_email(db, email)
    if user is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content="User not found")
    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content="You do not have the necessary permissions",
        )
    return current_user


def create_verification_link(user: User):
    verification_link = f"{os.getenv('BACKEND_URL')}/api/users/verify/{user.token}"
    email_content = f"""
            <p>Hallo {user.first_name},<br>
            Herzlich willkommen bei GALVA.AI! Wir freuen uns, Sie als neues Mitglied begrüßen zu dürfen.<br><br>
            Um Ihre Registrierung abzuschließen und alle Funktionen von GALVA.AI nutzen zu können, bitten wir
            Sie, Ihre E-Mail-Adresse zu bestätigen. Klicken Sie dazu einfach auf den folgenden Link:<br><br>
            <a href="{verification_link}">Verification Link</a><br><br>
            Nach Bestätigung Ihrer E-Mail erhalten Sie vollen Zugriff auf alle Funktionen unserer Plattform.<br><br>
            Bei Fragen stehen wir Ihnen gerne zur Verfügung.<br><br><br>
            Freundliche Grüße,<br><br>
            Patrick Boehm<br>
            Founder GALVA.AI<br><br></p>
            """
    return email_content


@router.post("/signup")
async def register(user: UserCreate, db: Session = Depends(db_connection)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    db_user = create_user(db, user)
    email_content = create_verification_link(db_user)
    send_email(user.email, "Email Verification - Galva.AI", email_content, sender_email, sender_email_pssword)

    return JSONResponse(content={"message": "User successfully created. Please verify email."},
                        status_code=status.HTTP_200_OK)


@router.get("/verify/{token}")
async def verify_email(token: str, db: Session = Depends(db_connection)):
    user = db.query(User).filter(User.token == token).first()
    if user:
        user.is_verified = True
        user.token = ""
        db.commit()
        db.refresh(user)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"message": "Email verified. Please sign in."})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invalid Request")


@router.post("/forgot")
async def forgot_password(email: str, db: Session = Depends(db_connection)):
    user = get_user_by_email(db, email)
    if user:
        uid = ''.join([str(ObjectId()) for _ in range(10)])
        user.token = uid
        db.commit()
        db.refresh(user)
        reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password/{uid}"

        email_content = f"<p>Hi {user.first_name},<br> Please use the link to reset password.<br>" \
                        f"<a href='{reset_link}'>Click here</a>" \
                        f"<br><br>Patrick Boehm<br>" \
                        f"Founder GALVA.AI<br><br></p>"

        send_email(email, "Reset Password", email_content)

        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"message": "Please check email to reset password"})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect email")


@router.put("/reset/{token}")
async def reset_password(token: str, new_password: UserPasswordReset, db: Session = Depends(db_connection)):
    user = db.query(User).filter(User.token == token).first()
    if user:
        user.password = hash_password(new_password.password)
        user.token = ""
        db.commit()
        db.refresh(user)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"message": "Password successfully updated"})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid Request")


@router.post("/resend")
async def resend_verification(email: str, db: Session = Depends(db_connection)):
    user = get_user_by_email(db, email)
    if user:
        if not user.is_verified:
            uid = ''.join([str(ObjectId()) for _ in range(10)])
            user.token = uid
            db.commit()
            db.refresh(user)
            email_content = create_verification_link(user)

            send_email(user.email, "Email Verification - Galva.AI", email_content, sender_email, sender_email_pssword)

            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"message": "Email sent. Please verify"})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Request")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User Not Found")


@router.post("/signin")
async def signin(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db_connection)):
    user = get_user_by_email(db, form_data.username)
    if user and verify_password(form_data.password, user.password):
        if user.is_verified:
            access_token = create_access_token(data={"sub": user.email, "role": user.role})
            refresh_token_expires = timedelta(days=7)
            refresh_token = create_access_token(data={"sub": user.email, "role": user.role},
                                                expires_delta=refresh_token_expires)

            create_user_refresh_token(db, user.id, refresh_token, datetime.utcnow() + refresh_token_expires)

            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={
                                    "access_token": access_token,
                                    "refresh_token": refresh_token,
                                    "token_type": "bearer",
                                    "role": user.role,
                                    "user_id": user.id
                                })
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is not verified")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")


@router.get("/", response_model=List[UserBase])
async def get_users_route(page: int = 0, limit: int = 30, db: Session = Depends(db_connection),
                          current_admin_user: User = Depends(get_current_admin_user)):
    users = get_users(db=db, page=page, limit=limit)
    return [user for user in users]


@router.get("/{user_id}", response_model=UserBase)
async def read_user(user_id: int, db: Session = Depends(db_connection)):
    db_user = get_user(db, user_id=user_id)
    if db_user:
        return JSONResponse(status_code=status.HTTP_200_OK, content=db_user)
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(db_connection),
                      current_admin_user: User = Depends(get_current_admin_user)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        db.refresh(db_user)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "User deleted successfully"})
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
