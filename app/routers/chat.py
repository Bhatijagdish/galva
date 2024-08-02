import uuid

from fastapi import APIRouter, HTTPException, Depends, FastAPI, Body, File, UploadFile, Request
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from galva.business_logic import num_tokens_from_string
from database import (Query, TokenCounter, get_recent_messages, db_connection, insert_message,
                      logger, get_recent_messages_by_user_id, insert_session_title, TitleCreate,
                      get_titles_by_session_id)
from ai.openai_res import AsyncCallbackHandler, ConversationalAI
from sqlalchemy.orm import Session

router = APIRouter()
ai = ConversationalAI()


@router.post("/conversations")
async def chat(query: Query, db: Session = Depends(db_connection)):
    try:
        if not query.query or not query.session_id:
            error_message = "Both 'query' and 'session_id' must be provided"
            return JSONResponse(content={"error": error_message}, status_code=400)

        # history_id = str(uuid.uuid4())
        chat_history = get_recent_messages(db, session_id=query.session_id, user_id=query.user_id, page=1, limit=500)

        # insert_message(db, query.session_id, history_id, 'human', query.query, query.user_id)

        # stream_it = AsyncCallbackHandler(db, query.session_id, history_id, query.user_id)
        # gen = ai.create_gen(query.query, chat_history, stream_it)
        gen = ai.response_generator(query.query, chat_history)
        return StreamingResponse(gen, media_type="text/event-stream")
    except HTTPException as http_err:
        return JSONResponse(content={"error": str(http_err)}, status_code=http_err.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/ai_conversations")
async def chat_openai(query: Query, db: Session = Depends(db_connection)):
    stream_it = AsyncCallbackHandler()
    gen = ai.create_gen_openai(query.query, stream_it)
    return StreamingResponse(gen, media_type="text/event-stream")


@router.post("/get_token_count")
async def get_token_count(token_counter: TokenCounter):
    return {"tokens": num_tokens_from_string(token_counter.query)}


@router.get("/get_conversation/{session_id}")
async def get_conversation(session_id: str, user_id: int, db: Session = Depends(db_connection)):
    messages = get_recent_messages(db, session_id, user_id, page=1, limit=200)
    return messages


@router.get("/get_past_conversations/{user_id}")
async def get_conversation(user_id: int, page: int = 1, limit: int = 30, db: Session = Depends(db_connection)):
    messages = get_recent_messages_by_user_id(db, user_id, page=page, limit=limit)
    session_map = {}
    for message in messages:
        if message.session_id not in session_map:
            query = get_titles_by_session_id(db, message.session_id)
            if query is None:
                return JSONResponse(content="No titles listed", status_code=404)
            session_map[message.session_id] = {"id": query.id, "session_id": query.session_id, "title": query.title}
    return list(session_map.values())


@router.get("/get_titles_by_session_id/{session_id}")
async def get_titles_via_session_id(session_id: str, db: Session = Depends(db_connection)):
    query = get_titles_by_session_id(db, session_id)
    if query is None:
        return JSONResponse(content="No titles listed", status_code=404)
    return query.title


@router.post("/title-generation")
async def title_generation(query: TitleCreate, db: Session = Depends(db_connection)):
    title = await ai.title_generation(query.text_message)
    return insert_session_title(db, query.session_id, title)


@router.post("/save_message")
async def save_message(session_id: str, history_id: str, sender: str, message_text: str,
                       user_id: int, db: Session = Depends(db_connection)):
    message = insert_message(db, session_id, history_id, sender, message_text, user_id)
    return {"message_id": message.message_id}
