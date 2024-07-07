from pydantic import BaseModel


class Query(BaseModel):
    query: str
    session_id: str
    user_id: int


class TokenCounter(BaseModel):
    query: str
