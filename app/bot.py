from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from fastapi import APIRouter, Request
from .openrouter_client import create_chat_completion, extract_text
from .settings import settings

bot_router = Router()
fastapi_router = APIRouter()

@bot_router.message(CommandStart())
async def start_cmd(m: Message):
    await m.answer("Привет! Напиши мне сообщение — отвечу через OpenRouter 🚀")

@bot_router.message(F.text)
async def handle_text(m: Message):
    msgs = [{"role": "user", "content": m.text}]
    resp = await create_chat_completion(msgs)
    text, *_ = extract_text(resp)
    await m.answer(text or "Пустой ответ 🤷")

# --- Long-polling runner (локально)
from aiogram import Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

async def start_polling(dp: Dispatcher):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=AiohttpSession())
    await dp.start_polling(bot)

# --- Webhook (прод) ---
@fastapi_router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(bot_router)  # использовать те же хэндлеры
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}