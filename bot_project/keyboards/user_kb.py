# ==================== keyboards/user_kb.py ====================
"""Клавиатуры для пользовательской части."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import SubsCallback, DownloadCallback


def subscribe_keyboard(slug: str = "", channels: list = None, button_text: str = "📢 Подписаться"):
    """
    Экран: «Подпишись».
    channels — список каналов (dict) для кнопок подписки.
    Если каналов нет — одна кнопка на @holy_IPA.
    """
    builder = InlineKeyboardBuilder()

    if channels:
        for ch in channels:
            # Приоритет: invite_link → username → chat_id
            url = ch.get("invite_link") or ""
            if not url and ch.get("username"):
                uname = ch["username"].lstrip("@")
                url = f"https://t.me/{uname}"
            if not url and str(ch.get("chat_id", "")).startswith("-100"):
                url = f"https://t.me/c/{str(ch['chat_id'])[4:]}"
            if url:
                title = ch.get("title") or ch.get("username") or "Канал"
                builder.button(text=f"📢 {title}", url=url)
    else:
        builder.button(text=button_text, url="https://t.me/holy_IPA")

    builder.button(
        text="✅ Я подписался",
        callback_data=SubsCallback(action="check", slug=slug)
    )
    builder.adjust(1)
    return builder.as_markup()


def file_delivery_keyboard(slug: str, howto_url: str, howto_text: str = "📖 Как установить?"):
    """
    Экран выдачи файла (сам файл уже отправлен выше):
    [📖 Как установить?]  (URL-кнопка)
    [🏠 Главное меню]
    """
    builder = InlineKeyboardBuilder()
    if howto_url:
        builder.button(text=howto_text, url=howto_url)
    builder.button(
        text="🏠 Главное меню",
        callback_data=SubsCallback(action="main_menu", slug="")
    )
    builder.adjust(1)
    return builder.as_markup()


def start_keyboard():
    """Клавиатура на /start: [ℹ️ Помощь]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="ℹ️ Помощь", callback_data=SubsCallback(action="help", slug=""))
    return builder.as_markup()