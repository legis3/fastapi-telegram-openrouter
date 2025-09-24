from pydantic import BaseModel
from typing import Literal

class Message(BaseModel):
    role: Literal["system","user","assistant"]
    content: str

class ChatRequest(BaseModel):
    user_id: str | None = None
    messages: list[Message]

class ChatResponse(BaseModel):
    content: str
    model: str | None = None
    finish_reason: str | None = None