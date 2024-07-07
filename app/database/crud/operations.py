from sqlalchemy.orm import Session
from database import Messages


def insert_message(db: Session, session_id: str, history_id: str, sender: str, message_text: str, user_id: int):
    message = Messages(session_id=session_id, user_id=user_id, history_id=history_id, sender=sender,
                       message_text=message_text)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(db: Session, session_id: str, user_id: int, limit: int) -> list:
    query = db.query(Messages).filter(Messages.session_id == session_id, Messages.user_id == user_id) \
        .order_by(Messages.timestamp.desc()).limit(limit).all()
    return [(msg.sender, msg.message_text) for msg in query[::-1]]
