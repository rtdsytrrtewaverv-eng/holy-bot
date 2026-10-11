# ==================== utils/ui.py ====================
"""
UI-утилиты: toast, хлебные крошки, разделители, пагинация, build_menu.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Callable
import math
import re
import unicodedata


def divider() -> str:
    return "━━━━━━━━━━━━━━━━"


def sanitize_slug(slug: str) -> str:
    """
    Приводит slug к формату, допустимому в Telegram deep-link (?start=).
    Разрешены только A-Za-z0-9_-. Пробелы и прочие символы → '_'.
    Точки заменяются на '_' (Telegram не поддерживает '.' в start-параметре).
    """
    if not slug:
        return ""
    # Транслитерация кириллицы не нужна — заменяем недопустимые символы
    slug = slug.strip().lower()
    slug = re.sub(r"[^a-z0-9_\-]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def normalize_slug_arg(arg: str) -> str:
    """
    Нормализует slug из deep-link: убирает пробелы/заглавные и приводит
    недопустимые символы (например точку) к '_', чтобы сопоставление с БД
    было устойчивым даже к старым ссылкам.
    """
    arg = (arg or "").strip().lower()
    # Точки и прочие символы → '_' (как при создании файла)
    arg = re.sub(r"[^a-z0-9_\-]+", "_", arg)
    arg = re.sub(r"_+", "_", arg).strip("_")
    return arg


async def toast(callback, text: str, show_alert: bool = False):
    """Отправляет всплывающее уведомление."""
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception:
        pass


def breadcrumb(*parts: str) -> str:
    """Строит хлебную крошку: '🏠 › 📁 Файлы › ✏️ Редакт.'"""
    return " › ".join(f"<b>{p}</b>" for p in parts if p)


def paginate(items: list, page: int, per_page: int = 5) -> tuple:
    """
    Возвращает (срез элементов, общее число страниц).
    page — 0-индексированный.
    """
    total_pages = max(1, math.ceil(len(items) / per_page))
    start = page * per_page
    end = start + per_page
    return items[start:end], total_pages


def add_pagination_buttons(
    builder: InlineKeyboardBuilder,
    current_page: int,
    total_pages: int,
    callback_factory: Callable,
    **extra_params
):
    """
    Добавляет кнопки [⬅️] [1/5] [➡️] в builder.
    callback_factory вызывается как callback_factory(page=N, **extra_params).
    Параметр action должен быть 'page'.
    """
    if total_pages <= 1:
        return
    builder.row(
        InlineKeyboardButton(
            text="⬅️",
            callback_data=callback_factory(action="page", page=max(0, current_page - 1), **extra_params).pack()
        ),
        InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}",
            callback_data=callback_factory(action="noop", page=current_page, **extra_params).pack()
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=callback_factory(action="page", page=min(total_pages - 1, current_page + 1), **extra_params).pack()
        ),
        width=3
    )
    return builder


async def ignore_message_not_modified(func):
    """Декоратор, игнорирующий ошибку 'message is not modified'."""
    from aiogram.exceptions import TelegramBadRequest
    try:
        return await func
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        raise