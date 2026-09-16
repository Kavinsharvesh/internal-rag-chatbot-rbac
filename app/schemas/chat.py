from typing import List
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""
    query: str
    answer: str
    sources: List[str]
    role: str
    status: str
