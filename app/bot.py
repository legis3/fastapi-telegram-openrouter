import asyncio
import re
import contextlib
from time import monotonic
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from aiogram.enums import ChatAction, ParseMode
from aiogram.client.default import DefaultBotProperties
from .openrouter_client import stream_chat_completion
from .settings import settings
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import APIRouter, Request

bot_router = Router()
fastapi_router = APIRouter()


MDV2_SPECIALS = r'[_*\[\]()~`>#+\-=|{}.!]'
def escape_mdv2(text: str) -> str:
    return re.sub(f'({MDV2_SPECIALS})', r'\\\1', text)

MAX_TG_LEN = 4096                 # лимит Telegram
EDIT_INTERVAL_SEC = 1.5           # минимальный интервал между edit_text
CHUNK_EDIT_MIN_DIFF = 80          # не редактировать, если добавилось мало символов
FALLBACK_SEND_AFTER = 3           # после N подряд retry_after -> переключаемся на sendMessage
STATUS_PREFIX_MDV2 = "*Идёт анализ задачи…*"
MAX_TG_LEN = 4096

@bot_router.message(CommandStart())
async def start_cmd(m: Message):
    greeting = "Привет! Напиши сообщение — отвечу потоком через OpenRouter 🚀"
    await m.answer(escape_mdv2(greeting), parse_mode=ParseMode.MARKDOWN_V2)

def split_chunks(text: str, max_len: int = MAX_TG_LEN) -> list[str]:
    """Режем по абзацам/строкам, чтобы не ломать MarkdownV2."""
    res, cur = [], []
    cur_len = 0
    for part in text.split("\n"):
        add = (("\n" if cur else "") + part)
        if cur_len + len(add) > max_len:
            res.append("".join(cur))
            cur, cur_len = [part], len(part)
        else:
            cur.append(add)
            cur_len += len(add)
    if cur:
        res.append("".join(cur))
    return res

@bot_router.message(F.text)
async def handle_text_stream(m: Message):
    msgs = [{"role": "user", "content": m.text.strip()}]

    # 1) статус
    status_msg = await m.answer(STATUS_PREFIX_MDV2, parse_mode=ParseMode.MARKDOWN_V2)
    typing_task = asyncio.create_task(_typing_loop(m))

    try:
        buffer = ""
        last_edit = monotonic()
        edit_interval = 1.5
        last_len = 0

        async for chunk in stream_chat_completion(msgs):
            buffer += chunk
            # безопасный “черновик”: статус + экранированный контент
            now = monotonic()
            if now - last_edit >= edit_interval and len(buffer) - last_len >= 80:
                draft = STATUS_PREFIX_MDV2 + "\n\n" + escape_mdv2(buffer)
                # с запасом, чтобы не превысить 4096
                if len(draft) > MAX_TG_LEN:
                    draft = draft[:MAX_TG_LEN - 20] + "\\n_…обрезано_"
                with contextlib.suppress(Exception):
                    await status_msg.edit_text(draft, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
                last_edit, last_len = now, len(buffer)

        # 2) Финал: убираем префикс и показываем ТОЛЬКО ответ
        final_plain = buffer if buffer else "(пусто)"
        final_md = escape_mdv2(final_plain)

        # если влазит — просто редактируем существующее сообщение без префикса
        final_ok = STATUS_PREFIX_MDV2 + "\n\n" + final_md
        if len(final_md) <= MAX_TG_LEN:
            with contextlib.suppress(Exception):
                await status_msg.edit_text(final_md, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
        else:
            # слишком длинно: шлём куски новыми сообщениями и удаляем статус
            for chunk in split_chunks(final_md, MAX_TG_LEN):
                await m.answer(chunk, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
            with contextlib.suppress(Exception):
                await m.bot.delete_message(chat_id=m.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        await status_msg.edit_text("*Ошибка:* " + escape_mdv2(str(e)), parse_mode=ParseMode.MARKDOWN_V2)
    finally:
        typing_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task

async def _typing_loop(m: Message):
    try:
        while True:
            await m.bot.send_chat_action(chat_id=m.chat.id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        return

# --- запуск polling (как и раньше) ---
async def start_polling(dp: Dispatcher):
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        session=AiohttpSession(),
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )
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