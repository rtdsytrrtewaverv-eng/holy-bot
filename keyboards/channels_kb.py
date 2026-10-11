# ==================== keyboards/channels_kb.py ====================
"""Клавиатуры управления каналами."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import ChannelCallback, NavCallback
from keyboards.common_kb import back_and_menu
from utils.ui import add_pagination_buttons


def channels_menu():
    """Меню каналов: [➕ Добавить] [📋 Список]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить канал", callback_data=ChannelCallback(action="add"))
    builder.button(text="📋 Список каналов", callback_data=ChannelCallback(action="list", page=0))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)
    return builder.as_markup()


def channels_list_kb(channels: list, page: int, total_pages: int):
    """Список каналов с пагинацией."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        active = "✅" if ch["is_active"] else "❌"
        required = "🔒" if ch["is_required"] else "🔓"
        label = ch["title"] or ch["username"] or ch["chat_id"]
        if len(label) > 30:
            label = label[:27] + "..."
        builder.button(
            text=f"{active}{required} {label}",
            callback_data=ChannelCallback(action="edit", channel_id=ch["id"])
        )
    builder.adjust(1)
    if total_pages > 1:
        add_pagination_buttons(builder, page, total_pages, ChannelCallback)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=NavCallback(action="back", section="channels_menu").pack()),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=NavCallback(action="main").pack()),
        width=2
    )
    return builder.as_markup()


def channel_detail_kb(channel_id: int, is_active: bool, is_required: bool):
    """Детальный вид канала."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=ChannelCallback(action="edit_field", channel_id=channel_id, field="title"))
    toggle_active = "❌ Выключить" if is_active else "✅ Включить"
    toggle_required = "🔓 Необязательный" if is_required else "🔒 Обязательный"
    builder.button(text=toggle_active, callback_data=ChannelCallback(action="toggle_active", channel_id=channel_id))
    builder.button(text=toggle_required, callback_data=ChannelCallback(action="toggle_required", channel_id=channel_id))
    builder.button(text="✅ Проверить", callback_data=ChannelCallback(action="check", channel_id=channel_id))
    builder.button(text="🗑 Удалить", callback_data=ChannelCallback(action="delete", channel_id=channel_id))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=ChannelCallback(action="list", page=0).pack()),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=NavCallback(action="main").pack()),
        width=2
    )
    return builder.as_markup()


def channel_edit_fields_kb(channel_id: int):
    """Поля для редактирования канала."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Название", callback_data=ChannelCallback(action="edit_field", channel_id=channel_id, field="title"))
    builder.button(text="🔗 Пригласительная ссылка", callback_data=ChannelCallback(action="edit_field", channel_id=channel_id, field="invite_link"))
    builder.attach(back_and_menu("channels_menu"))
    builder.adjust(1)
    return builder.as_markup()


def channel_confirm_delete_kb(channel_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=ChannelCallback(action="confirm_delete", channel_id=channel_id))
    builder.button(text="❌ Отмена", callback_data=ChannelCallback(action="edit", channel_id=channel_id))
    builder.adjust(1)
    return builder.as_markup()