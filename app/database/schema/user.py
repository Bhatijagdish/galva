from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    role: str
    is_verified: bool


#
# class User(BaseModel):
#     email: EmailStr
#     first_name: str
#     last_name: str
#     role: str
#     password: str
#     is_verified: bool
#     token: str


class UserOut(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str


class UserInDB(UserBase):
    hashed_password: str


class UserSignIn(BaseModel):
    email: EmailStr
    password: str


class UserPasswordReset(BaseModel):
    password: str
    token: str