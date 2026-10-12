# ==================== keyboards/files_kb.py ====================
"""Клавиатуры управления файлами."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import FileCallback, NavCallback, ConfirmCallback
from keyboards.common_kb import back_and_menu
from utils.ui import add_pagination_buttons


def files_menu():
    """Меню файлов: [➕ Добавить] [📋 Список]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить файл", callback_data=FileCallback(action="add"))
    builder.button(text="📋 Список файлов", callback_data=FileCallback(action="list", page=0))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)
    return builder.as_markup()


def file_list_kb(files: list, page: int, total_pages: int):
    """Список файлов с пагинацией."""
    builder = InlineKeyboardBuilder()
    for f in files:
        label = f"{f['title'] or f['slug']}"
        if len(label) > 40:
            label = label[:37] + "..."
        builder.button(
            text=f"📄 {label}",
            callback_data=FileCallback(action="edit", file_id=f["id"])
        )
    builder.adjust(1)
    if total_pages > 1:
        add_pagination_buttons(builder, page, total_pages, FileCallback)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=NavCallback(action="back", section="files_menu").pack()),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=NavCallback(action="main").pack()),
        width=2
    )
    return builder.as_markup()


def file_detail_kb(file_id: int, in_library: bool = True):
    """Детали файла: [✏️][🖼][📚][🔗][👁][🗑]."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=FileCallback(action="edit_field", file_id=file_id, field="title"))
    builder.button(text="🖼 Обложка", callback_data=FileCallback(action="edit_field", file_id=file_id, field="image_file_id"))
    lib_text = "📚 Убрать из библиотеки" if in_library else "📚 Добавить в библиотеку"
    builder.button(text=lib_text, callback_data=FileCallback(action="edit_field", file_id=file_id, field="toggle_library"))
    builder.button(text="🔗 Получить ссылку", callback_data=FileCallback(action="link", file_id=file_id))
    builder.button(text="👁 Предпросмотр", callback_data=FileCallback(action="preview", file_id=file_id))
    builder.button(text="🗑 Удалить", callback_data=FileCallback(action="delete", file_id=file_id))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=FileCallback(action="list", page=0).pack()),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=NavCallback(action="main").pack()),
        width=2
    )
    return builder.as_markup()


def file_edit_fields_kb(file_id: int):
    """Выбор поля для редактирования."""
    builder = InlineKeyboardBuilder()
    fields = [
        ("📝 Название", "title"),
        ("📄 Описание", "description"),
        ("🔗 Ссылка «Как уст.»", "howto_url"),
        ("📎 Slug", "slug"),
        ("🖼 Обложка", "image_file_id"),
        ("📂 Заменить файл", "file_id"),
    ]
    for label, field in fields:
        builder.button(
            text=label,
            callback_data=FileCallback(action="edit_field", file_id=file_id, field=field)
        )
    builder.attach(back_and_menu("files_menu"))
    builder.adjust(1)
    return builder.as_markup()


def file_confirm_delete_kb(file_id: int):
    """Подтверждение удаления файла."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, удалить",
        callback_data=FileCallback(action="confirm_delete", file_id=file_id)
    )
    builder.button(
        text="❌ Отмена",
        callback_data=FileCallback(action="edit", file_id=file_id)
    )
    builder.adjust(1)
    return builder.as_markup()