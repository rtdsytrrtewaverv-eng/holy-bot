# ==================== utils/broadcast_handler.py ====================
"""
Логика выполнения рассылок. Запускается асинхронно.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from database import get_all_users, update_broadcast
from utils.files import send_file

logger = logging.getLogger(__name__)


async def execute_broadcast(
    bot: Bot,
    broadcast_id: int,
    message_type: str,
    message_content: str,
    button_text: str = "",
    button_url: str = "",
    filter_type: str = "all",
    caption: str = "",
):
    """
    Выполняет рассылку по фильтру.
    message_content — для text это текст; для остальных — file_id.
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    only_active = (filter_type == "active")
    only_subscribed = (filter_type == "subscribed")
    users = await get_all_users(only_active=only_active, only_subscribed=only_subscribed)

    sent, failed = 0, 0

    reply_markup = None
    if button_text and button_url:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=button_text, url=button_url)]]
        )

    for user in users:
        user_id = user["user_id"]
        try:
            if message_type == "text":
                await bot.send_message(
                    chat_id=user_id,
                    text=message_content,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            else:
                # Любой файл: фото, видео, документ, аудио, GIF и т.д.
                await send_file(
                    bot, user_id, message_type, message_content,
                    caption=caption or None,
                    reply_markup=reply_markup,
                )
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            failed += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception as e:
            logger.warning("Рассылка: не отправлено %s: %s", user_id, e)
            failed += 1
        await asyncio.sleep(0.05)

    await update_broadcast(
        broadcast_id,
        sent=sent,
        failed=failed,
        status="completed"
    )