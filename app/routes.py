# app/routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .schemas import ChatRequest, ChatResponse
from .openrouter_client import create_chat_completion, extract_text, stream_chat_completion

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
  
@router.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]

    async def token_generator():
        # первая "служебная" строка — чтобы фронт видел, что всё живо
        yield "Идёт анализ задачи....\n\n"
        try:
            async for chunk in stream_chat_completion(messages):
                # отдаём кусочки как есть
                yield chunk
        except Exception as e:
            # пробрасываем текст ошибки в поток (можно убрать в проде)
            yield f"\n\n[stream-error] {e}\n"

    # вариант: text/plain (любой клиент увидит чанки)
    return StreamingResponse(token_generator(), media_type="text/plain")