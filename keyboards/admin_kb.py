# ==================== keyboards/admin_kb.py ====================
"""Клавиатуры админ-панели."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import MenuCallback


def admin_main_menu():
    """Главное меню админа."""
    builder = InlineKeyboardBuilder()
    buttons = [
        ("📊 Статистика", "stats"),
        ("📁 Файлы", "files"),
        ("📢 Каналы", "channels"),
        ("💬 Тексты и медиа", "texts"),
        ("📣 Рассылка", "broadcast"),
        ("👥 Пользователи", "users_list"),
        ("⚙️ Настройки", "settings"),
        ("💾 Бэкап", "backup"),
    ]
    for text, action in buttons:
        builder.button(text=text, callback_data=MenuCallback(action=action))
    builder.adjust(2)
    return builder.as_markup()