from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str
    password: str


class UserBase(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
