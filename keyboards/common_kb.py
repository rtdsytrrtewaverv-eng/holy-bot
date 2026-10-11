# ==================== keyboards/common_kb.py ====================
"""Общие клавиатуры: назад, главное меню, подтверждение."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import NavCallback, ConfirmCallback


def back_button(section: str = "", page: int = 0):
    """Кнопка «⬅️ Назад»."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=NavCallback(action="back", section=section, page=page))
    return builder.as_markup()


def main_menu_button():
    """Кнопка «🏠 Главное меню»."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data=NavCallback(action="main", section="", page=0))
    return builder


def back_and_menu(section: str = "", page: int = 0):
    """Кнопки [⬅️ Назад] [🏠 Главное меню]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=NavCallback(action="back", section=section, page=page))
    builder.button(text="🏠 Главное меню", callback_data=NavCallback(action="main", section="", page=0))
    return builder


def confirm_buttons(context: str = ""):
    """Кнопки [✅ Да] [❌ Отмена]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=ConfirmCallback(action="yes", context=context))
    builder.button(text="❌ Отмена", callback_data=ConfirmCallback(action="no", context=context))
    return builder