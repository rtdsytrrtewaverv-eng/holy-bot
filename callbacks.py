# ==================== callbacks.py ====================
"""
CallbackData фабрики для всех inline-кнопок бота.
"""

from aiogram.filters.callback_data import CallbackData


class MenuCallback(CallbackData, prefix="menu"):
    """Главное меню и базовая навигация."""
    action: str  # admin_panel, stats, files, channels, texts, broadcast, users_list, settings, backup, back, main_menu


class FileCallback(CallbackData, prefix="file"):
    """Управление файлами."""
    action: str  # list, add, edit, edit_field, delete, confirm_delete, cancel_delete, link, preview, page
    file_id: int = 0
    field: str = ""  # slug, title, description, howto_url, file_type, file_id
    page: int = 0


class ChannelCallback(CallbackData, prefix="ch"):
    """Управление каналами."""
    action: str  # list, add, edit, edit_field, delete, confirm_delete, cancel_delete, toggle_active, toggle_required, check, page
    channel_id: int = 0
    field: str = ""
    page: int = 0


class TextCallback(CallbackData, prefix="txt"):
    """Управление текстами и медиа."""
    action: str  # list_texts, edit_text, medias_list, edit_media, delete_media, page
    key: str = ""
    page: int = 0


class SubsCallback(CallbackData, prefix="subs"):
    """Проверка подписки."""
    action: str  # check, subscribed, not_subscribed
    slug: str = ""


class UserCallback(CallbackData, prefix="usr"):
    """Управление пользователями."""
    action: str  # list, card, ban, unban, search, page
    user_id: int = 0
    page: int = 0


class BroadcastCallback(CallbackData, prefix="bc"):
    """Рассылки."""
    action: str  # new, choose_filter, send, cancel, page
    filter_type: str = ""  # all, subscribed, active
    broadcast_id: int = 0
    page: int = 0


class SettingsCallback(CallbackData, prefix="set"):
    """Настройки."""
    action: str  # toggle_subscribe, toggle_maintenance, add_admin, page


class BackupCallback(CallbackData, prefix="bak"):
    """Бэкап."""
    action: str  # download, upload, confirm_upload


class NavCallback(CallbackData, prefix="nav"):
    """Универсальная навигация."""
    action: str  # back, main, page
    section: str = ""
    page: int = 0


class ConfirmCallback(CallbackData, prefix="cfm"):
    """Подтверждения (Да/Нет)."""
    action: str  # yes, no
    context: str = ""  # произвольный контекст (например, file:5)


class DownloadCallback(CallbackData, prefix="dl"):
    """Кнопка скачивания файла."""
    slug: str = ""