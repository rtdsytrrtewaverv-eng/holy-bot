# ==================== keyboards/user_kb.py ====================
"""Клавиатуры для пользовательской части."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callbacks import SubsCallback, DownloadCallback, MenuCallback, LibraryCallback


def subscribe_keyboard(slug: str = "", channels: list = None, button_text: str = "Подписаться",
                       from_library: bool = False):
    """
    Экран: «Подпишись».
    channels — список каналов (dict) для кнопок подписки.
    Если каналов нет — одна кнопка на @holy_IPA.
    from_library — кнопка «Я подписался» открывает библиотеку после проверки.
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
                builder.button(text=title, url=url)
    else:
        builder.button(text=button_text, url="https://t.me/holy_IPA")

    if from_library:
        check_cb = LibraryCallback(action="check")
    else:
        check_cb = SubsCallback(action="check", slug=slug)

    builder.button(text="Я подписался", callback_data=check_cb)
    builder.adjust(1)
    return builder.as_markup()


def file_delivery_keyboard(slug: str, howto_url: str, howto_text: str = "Как установить?",
                           howto_style: str = None, back_style: str = None):
    """
    Экран выдачи файла (сам файл уже отправлен выше):
    [Как установить?]  (URL-кнопка)
    [Главное меню]
    """
    builder = InlineKeyboardBuilder()
    if howto_url:
        builder.button(text=howto_text, url=howto_url, style=howto_style)
    builder.button(
        text="Главное меню",
        callback_data=SubsCallback(action="main_menu", slug=""),
        style=back_style
    )
    builder.adjust(1)
    return builder.as_markup()


def start_keyboard(is_admin: bool = False, library_button_text: str = "Библиотека",
                   library_enabled: bool = True, main_style: str = None):
    """
    Клавиатура на /start.
    [Помощь] — всем.
    [Библиотека] — если включена.
    [Админка] — только администраторам.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Помощь", callback_data=SubsCallback(action="help", slug=""), style=main_style)
    if library_enabled:
        builder.button(
            text=library_button_text or "Библиотека",
            callback_data=LibraryCallback(action="open"),
            style=main_style
        )
    if is_admin:
        builder.button(text="Админка", callback_data=MenuCallback(action="admin_panel"), style=main_style)
    builder.adjust(1)
    return builder.as_markup()


async def library_keyboard(files: list, page: int, total_pages: int, style: str = None):
    """Клавиатура списка приложений в библиотеке."""
    builder = InlineKeyboardBuilder()
    for f in files:
        label = (f.get("title") or f.get("slug") or "").strip()
        if len(label) > 40:
            label = label[:37] + "..."
        builder.button(
            text=label,
            callback_data=LibraryCallback(action="show", file_id=f["id"]),
            style=style
        )
    builder.adjust(1)

    if total_pages > 1:
        builder.row(
            InlineKeyboardButton(
                text="←",
                callback_data=LibraryCallback(action="page", page=max(0, page - 1)).pack()
            ),
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data=LibraryCallback(action="noop", page=page).pack()
            ),
            InlineKeyboardButton(
                text="→",
                callback_data=LibraryCallback(action="page", page=min(total_pages - 1, page + 1)).pack()
            ),
            width=3
        )
    builder.button(
        text="Главное меню",
        callback_data=SubsCallback(action="main_menu", slug="")
    )
    return builder.as_markup()
