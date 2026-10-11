# ==================== keyboards/texts_kb.py ====================
"""Клавиатуры управления текстами и медиа."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import TextCallback, NavCallback, MenuCallback
from keyboards.common_kb import back_and_menu


def texts_menu():
    """Меню: 🖼 Картинки, тексты."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Картинки", callback_data=TextCallback(action="medias_list"))
    builder.button(text="📝 Тексты", callback_data=TextCallback(action="list_texts"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)
    return builder.as_markup()


def texts_list_kb(texts: list):
    """Список текстов для редактирования."""
    builder = InlineKeyboardBuilder()
    labels = {
        "start_text": "👋 Приветствие",
        "subscribe_text": "🔒 Текст подписки",
        "subscription_confirmed": "✅ Подписка подтверждена",
        "file_not_found": "❌ Файл не найден",
        "help_text": "ℹ️ Помощь",
        "support_username": "📞 Юзернейм поддержки",
        "support_text": "📞 Текст поддержки",
        "howto_button_text": "📖 Текст кнопки «Как уст.»",
        "tech_works": "🚧 Тех.работы",
    }
    for t in texts:
        label = labels.get(t["key"], t["key"])
        builder.button(
            text=f"📝 {label}",
            callback_data=TextCallback(action="edit_text", key=t["key"])
        )
    builder.attach(back_and_menu("texts_menu"))
    builder.adjust(1)
    return builder.as_markup()


def medias_menu_kb():
    """Список медиа для замены."""
    builder = InlineKeyboardBuilder()
    items = [
        ("🖼 Картинка /start", "start_photo"),
        ("🖼 Картинка подписки", "subscribe_photo"),
    ]
    for label, key in items:
        builder.button(
            text=label,
            callback_data=TextCallback(action="edit_media", key=key)
        )
    builder.attach(back_and_menu("texts_menu"))
    builder.adjust(1)
    return builder.as_markup()


def media_edit_kb(key: str):
    """Кнопки для конкретной картинки: [📷 Заменить] [🗑 Удалить]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📷 Заменить", callback_data=TextCallback(action="edit_media", key=key))
    builder.button(text="🗑 Удалить", callback_data=TextCallback(action="delete_media", key=key))
    builder.attach(back_and_menu("medias_list"))
    builder.adjust(1)
    return builder.as_markup()