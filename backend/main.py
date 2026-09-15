import os
import re
import time
import uuid
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal, engine
from models import ChatMessage, ChatSession
from rag import generate_artifact, generate_chat_response


def sanitize_chat_answer(text: str) -> str:
    """
    Remove generic preambles like 'Based on the provided transcript context, here's the answer...'
    from the LLM output to make the answer natural and direct.
    """
    if not text:
        return text

    patterns = [
        r"^Based on the provided transcript context,?\s*(here'?s the answer to the current question:?)?\s*",
        r"^Based on the provided transcript,?\s*(here'?s the answer:?)?\s*",
        r"^According to the provided transcript( context)?,?\s*",
        r"^Here is the answer to the current question:?\s*",
        r"^Based on the retrieved context,?\s*",
        r"^Based on the transcript context provided,?\s*",
    ]

    cleaned = text.strip()
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned.strip()



app = FastAPI(
    title="Lenny Growth Assistant API",
    description="Backend API for the Lenny Growth Assistant",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SourceItem(BaseModel):
    guest: str | None = None
    title: str | None = None
    url: str | None = None
    chunk_index: int = 0


class ChatApiRequest(BaseModel):
    session_id: str
    message: str
    provider: str = "ollama"

    @field_validator("session_id", "message")
    @classmethod
    def validate_not_empty(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must not be empty or whitespace.")
        return value.strip()


class ChatApiResponse(BaseModel):
    session_id: str
    message: str
    sources: list[SourceItem]
    provider: str = "ollama"


class ArtifactApiRequest(BaseModel):
    session_id: str
    prompt: str
    format: str = "markdown"
    provider: str = "ollama"

    @field_validator("session_id", "prompt")
    @classmethod
    def validate_not_empty(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must not be empty or whitespace.")
        return value.strip()

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        fmt = value.strip().lower()
        if fmt not in ("markdown", "html"):
            raise ValueError("Format must be either 'markdown' or 'html'.")
        return fmt


class ArtifactApiResponse(BaseModel):
    artifact_id: str
    session_id: str
    title: str
    format: str
    content: str


# Backwards-compatible models
class ChatRequest(ChatApiRequest):
    pass


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[dict]


@app.get("/")
def root():
    return {
        "message": "Lenny Growth Assistant API is running"
    }


@app.get("/health")
def health():
    db_status = "disconnected"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
    }


def handle_chat_logic(request: ChatApiRequest) -> dict:
    """Core logic to process chat session, load history, query RAG, and persist messages."""
    t_start = time.perf_counter()
    print(f"\n==================== [DIAGNOSTIC] POST /api/chat START ====================")
    print(f"[STAGE 1] Request received at {time.strftime('%H:%M:%S')} | Session ID: '{request.session_id}' | Provider: '{request.provider}' | Message: '{request.message}'")

    db = SessionLocal()
    t_db_start = time.perf_counter()

    try:
        # 1. Find or create session
        session = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == request.session_id)
            .first()
        )

        if not session:
            session = ChatSession(session_id=request.session_id)
            db.add(session)
            db.commit()
            db.refresh(session)

        # 2. Load previous conversation history for this session
        history_records = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.asc())
            .all()
        )

        conversation_history = [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in history_records
        ]

        # 3. Save user message
        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        db.commit()

        t_db_end = time.perf_counter()
        db_duration = t_db_end - t_db_start
        print(f"[STAGE 2] Database/Session History Lookup finished in {db_duration:.4f}s ({len(history_records)} history messages loaded)")

        # 4. Generate RAG response using Ollama & retrieved transcript sources
        try:
            result = generate_chat_response(
                question=request.message,
                conversation_history=conversation_history,
                limit=3,
                provider=request.provider,
            )
            result["message"] = sanitize_chat_answer(result.get("message", ""))
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM service (Ollama) is unavailable: {str(exc)}",
            ) from exc

        # 5. Save assistant response
        t_save_start = time.perf_counter()
        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=result["message"],
        )
        db.add(assistant_message)
        db.commit()
        t_save_end = time.perf_counter()

        t_total = time.perf_counter() - t_start
        print(f"[STAGE 7] Response returned & saved to DB in {t_save_end - t_save_start:.4f}s | TOTAL PIPELINE TIME: {t_total:.4f}s")
        print(f"==================== [DIAGNOSTIC] POST /api/chat END ====================\n")

        return {
            "session_id": request.session_id,
            "message": result["message"],
            "sources": result["sources"],
            "provider": request.provider,
        }

    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(db_err)}",
        ) from db_err
    finally:
        db.close()


@app.post("/api/chat", response_model=ChatApiResponse)
def chat_api(request: ChatApiRequest):
    return handle_chat_logic(request)


@app.post("/api/artifacts", response_model=ArtifactApiResponse)
def create_artifact_api(request: ArtifactApiRequest):
    db = SessionLocal()
    try:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == request.session_id)
            .first()
        )
        conversation_history = []
        if session:
            history_records = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.id.asc())
                .all()
            )
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in history_records
            ]

        try:
            artifact_data = generate_artifact(
                prompt=request.prompt,
                format=request.format,
                conversation_history=conversation_history,
                provider=request.provider,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Artifact generation failed: {str(exc)}",
            ) from exc

        artifact_id = f"art_{uuid.uuid4().hex[:10]}"

        return {
            "artifact_id": artifact_id,
            "session_id": request.session_id,
            "title": artifact_data["title"],
            "format": artifact_data["format"],
            "content": artifact_data["content"],
        }
    except SQLAlchemyError as db_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(db_err)}",
        ) from db_err
    finally:
        db.close()


@app.post("/chat")
def chat(request: ChatApiRequest):
    res = handle_chat_logic(request)
    return {
        "session_id": res["session_id"],
        "answer": res["message"],
        "message": res["message"],
        "sources": res["sources"],
        "provider": res["provider"],
    }
