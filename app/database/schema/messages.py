from pydantic import BaseModel


class Query(BaseModel):
    query: str
    session_id: str
    user_id: int


class TokenCounter(BaseModel):
    query: str


class TitleCreate(BaseModel):
    session_id: str
    text_message: str
