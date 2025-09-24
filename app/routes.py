# app/routes.py
from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from .openrouter_client import create_chat_completion, extract_text

router = APIRouter()

@router.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    try:
        resp = await create_chat_completion(messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e}")
    content, model, finish = extract_text(resp)
    return ChatResponse(content=content, model=model, finish_reason=finish)