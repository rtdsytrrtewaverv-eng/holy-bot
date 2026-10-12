# ==================== utils/files.py ====================
"""
Универсальная работа с файлами Telegram.
Извлекает file_id и тип из ЛЮБОГО сообщения с вложением,
а также отправляет файл нужного типа.
"""

import logging

from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)


def extract_file(message: Message):
    """
    Достаёт (file_type, file_id) из сообщения с любым вложением.
    Возвращает (None, None), если вложения нет.
    """
    if message.document:
        return "document", message.document.file_id
    if message.video:
        return "video", message.video.file_id
    if message.animation:
        return "animation", message.animation.file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.voice:
        return "voice", message.voice.file_id
    if message.video_note:
        return "video_note", message.video_note.file_id
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.sticker:
        return "sticker", message.sticker.file_id
    return None, None


def file_display_name(message: Message) -> str:
    """Человекочитаемое имя файла для показа админу."""
    if message.document and message.document.file_name:
        return message.document.file_name
    if message.video and message.video.file_name:
        return message.video.file_name
    if message.audio and message.audio.file_name:
        return message.audio.file_name
    ftype, _ = extract_file(message)
    return ftype or "файл"


async def send_file(bot: Bot, chat_id: int, file_type: str, file_id: str,
                    caption: str = None, reply_markup=None, parse_mode: str = "HTML"):
    """
    Отправляет файл нужного типа. Поддерживает все типы Telegram.
    Возвращает отправленное сообщение или None при ошибке.
    """
    ft = (file_type or "document").lower()
    kwargs = {"chat_id": chat_id}
    if caption:
        kwargs["caption"] = caption
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    if caption and parse_mode:
        kwargs["parse_mode"] = parse_mode

    if ft == "video":
        return await bot.send_video(video=file_id, **kwargs)
    if ft == "animation":
        return await bot.send_animation(animation=file_id, **kwargs)
    if ft == "audio":
        return await bot.send_audio(audio=file_id, **kwargs)
    if ft == "voice":
        return await bot.send_voice(voice=file_id, **kwargs)
    if ft == "video_note":
        return await bot.send_video_note(video_note=file_id, **kwargs)
    if ft == "photo":
        return await bot.send_photo(photo=file_id, **kwargs)
    if ft == "sticker":
        return await bot.send_sticker(sticker=file_id, **kwargs)
    # по умолчанию — документ (любое расширение)
    return await bot.send_document(document=file_id, **kwargs)
