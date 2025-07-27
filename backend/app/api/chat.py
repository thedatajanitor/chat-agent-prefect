from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    session_id: str
    timestamp: Optional[datetime] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    timestamp: datetime
    flow_run_id: Optional[str] = None


class ChatSession(BaseModel):
    session_id: str
    created_at: datetime
    messages: List[ChatMessage]
    is_active: bool


@router.post("/start", response_model=ChatSession)
async def start_chat_session():
    """Start a new chat session"""
    session_id = f"session_{datetime.now().timestamp()}"
    return ChatSession(
        session_id=session_id,
        created_at=datetime.now(),
        messages=[],
        is_active=True
    )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(session_id: str):
    """Get chat session details"""
    # TODO: Implement session retrieval from storage
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions/{session_id}/end")
async def end_chat_session(session_id: str):
    """End a chat session"""
    # TODO: Implement session ending logic
    return {"message": f"Session {session_id} ended"}