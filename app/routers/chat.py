import uuid

from fastapi import APIRouter, HTTPException, Depends, FastAPI, Body, File, UploadFile, Request
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from galva.business_logic import num_tokens_from_string
from database import Query, TokenCounter, get_recent_messages, db_connection, insert_message, logger
from ai.openai_res import AsyncCallbackHandler, ConversationalAI
from sqlalchemy.orm import Session

router = APIRouter()
ai = ConversationalAI()


@router.post("/conversations")
async def chat(query: Query, db: Session = Depends(db_connection)):
    # stream_it = AsyncCallbackHandler()
    # gen = ai.create_gen(query.query, stream_it)
    # return StreamingResponse(gen, media_type="text/event-stream")
    try:
        if not query.query or not query.session_id:
            error_message = "Both 'query' and 'session_id' must be provided"
            return JSONResponse(content={"error": error_message}, status_code=400)

        history_id = str(uuid.uuid4())

        # Collecting the message objects from db
        chat_history = get_recent_messages(db, session_id=query.session_id, user_id=query.user_id, limit=50)

        insert_message(db, query.session_id, history_id, 'human', query.query, query.user_id)

        stream_it = AsyncCallbackHandler(db, query.session_id, history_id, query.user_id)

        gen = ai.create_gen(query.query, chat_history, stream_it)

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
    messages = get_recent_messages(db, session_id, user_id, limit=50)
    return messages


@router.post("/save_message")
async def save_message(session_id: str, history_id: str, sender: str, message_text: str,
                       user_id: int, db: Session = Depends(db_connection)):
    message = insert_message(db, session_id, history_id, sender, message_text, user_id)
    return {"message_id": message.message_id}
