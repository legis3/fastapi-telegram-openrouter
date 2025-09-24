import asyncio
from fastapi import FastAPI
from .routes import router as api_router
from .bot import bot_router, start_polling
from aiogram import Dispatcher
from .settings import settings

app = FastAPI(title="FastAPI + Telegram + OpenRouter")
app.include_router(api_router, tags=["api"])

# Для webhook-режима добавим эндпоинт
from .bot import fastapi_router as webhook_router
app.include_router(webhook_router, tags=["telegram"])

# Один Dispatcher на всё приложение
dp = Dispatcher()
dp.include_router(bot_router)

@app.on_event("startup")
async def _on_startup():
    if settings.USE_WEBHOOK:
        # Ничего не запускаем — Telegram будет слать в /telegram/webhook
        print("Webhook mode: ожидаем запросы от Telegram")
    else:
        # Локальная разработка: long-polling в фоне
        asyncio.create_task(start_polling(dp))

@app.get("/")
async def root():
    return {"ok": True, "service": "fastapi-telegram-openrouter"}