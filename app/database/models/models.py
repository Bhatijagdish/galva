from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Enum, CheckConstraint, Text
from sqlalchemy.orm import relationship
from database.database import Base


class Messages(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String, nullable=False)
    history_id = Column(String, nullable=False)
    sender = Column(String, CheckConstraint("sender IN ('ai', 'human')"), nullable=False)
    message_text = Column(Text, nullable=False)
    timestamp = Column(String, server_default=func.now())

    user = relationship("User", back_populates="messages")
    session = relationship("Titles", back_populates="messages")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default="user")
    timestamp = Column(String, server_default=func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    messages = relationship("Messages", back_populates="user")


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class PDF(Base):
    __tablename__ = "pdfs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, unique=True, index=True)


class Titles(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('messages.session_id'), nullable=False)
    title = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    messages = relationship("Messages", back_populates="session")
