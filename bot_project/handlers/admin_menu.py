# ==================== handlers/admin_menu.py ====================
"""
Главное меню админки и навигация.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import is_admin
from callbacks import MenuCallback, NavCallback
from keyboards.admin_kb import admin_main_menu
from keyboards.files_kb import files_menu
from keyboards.channels_kb import channels_menu
from keyboards.texts_kb import texts_menu
from utils.ui import toast, breadcrumb

admin_menu_router = Router(name="admin_menu")


def admin_only():
    """Decorator-like filter: проверяет права админа."""
    async def _check(callback: CallbackQuery, bot: Bot):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет доступа", show_alert=True)
            return False
        return True
    return _check


@admin_menu_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin — вход в админ-панель."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer(
        "<b>👑 Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )


@admin_menu_router.callback_query(MenuCallback.filter())
async def cq_admin_menu(callback: CallbackQuery, callback_data: MenuCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    action = callback_data.action

    if action == "stats":
        from handlers.stats import show_stats
        await callback.answer()
        await show_stats(callback)
    elif action == "files":
        await toast(callback, "📁 Файлы")
        await callback.message.edit_text(
            breadcrumb("🏠", "📁 Управление файлами") + "\n",
            reply_markup=files_menu(),
            parse_mode="HTML"
        )
    elif action == "channels":
        await toast(callback, "📢 Каналы")
        await callback.message.edit_text(
            breadcrumb("🏠", "📢 Управление каналами") + "\n",
            reply_markup=channels_menu(),
            parse_mode="HTML"
        )
    elif action == "texts":
        await toast(callback, "💬 Тексты и медиа")
        await callback.message.edit_text(
            breadcrumb("🏠", "💬 Тексты и медиа") + "\n",
            reply_markup=texts_menu(),
            parse_mode="HTML"
        )
    elif action == "broadcast":
        from handlers.broadcast import broadcast_menu_handler
        await broadcast_menu_handler(callback)
    elif action == "users_list":
        from handlers.users import users_list_handler
        await users_list_handler(callback)
    elif action == "settings":
        from handlers.settings import settings_menu_handler
        await settings_menu_handler(callback)
    elif action == "backup":
        from handlers.backup import backup_menu_handler
        await backup_menu_handler(callback)


# ═══════════════════════════════════════════════════════════
# Навигация (Назад / Главное меню)
# ═══════════════════════════════════════════════════════════

@admin_menu_router.callback_query(NavCallback.filter(F.action == "back"))
async def cq_nav_back(callback: CallbackQuery, callback_data: NavCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    section = callback_data.section

    if section == "admin":
        await callback.message.edit_text(
            "<b>👑 Админ-панель</b>\n\nВыберите раздел:",
            reply_markup=admin_main_menu(),
            parse_mode="HTML"
        )
    elif section == "files_menu":
        await callback.message.edit_text(
            breadcrumb("🏠", "📁 Управление файлами") + "\n",
            reply_markup=files_menu(),
            parse_mode="HTML"
        )
    elif section == "channels_menu":
        await callback.message.edit_text(
            breadcrumb("🏠", "📢 Управление каналами") + "\n",
            reply_markup=channels_menu(),
            parse_mode="HTML"
        )
    elif section == "texts_menu":
        await callback.message.edit_text(
            breadcrumb("🏠", "💬 Тексты и медиа") + "\n",
            reply_markup=texts_menu(),
            parse_mode="HTML"
        )
    elif section == "settings":
        from handlers.settings import settings_menu_handler
        await settings_menu_handler(callback)
    elif section == "broadcast":
        from handlers.broadcast import broadcast_menu_handler
        await broadcast_menu_handler(callback)
    elif section == "users":
        from handlers.users import users_list_handler
        await users_list_handler(callback)
    elif section == "stats":
        from handlers.stats import show_stats
        await show_stats(callback)
    elif section == "backup":
        from handlers.backup import backup_menu_handler
        await backup_menu_handler(callback)
    else:
        await callback.message.edit_text(
            "<b>👑 Админ-панель</b>\n\nВыберите раздел:",
            reply_markup=admin_main_menu(),
            parse_mode="HTML"
        )
    await callback.answer()


@admin_menu_router.callback_query(NavCallback.filter(F.action == "main"))
async def cq_nav_main(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>👑 Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_menu_router.callback_query(NavCallback.filter(F.action == "noop"))
async def cq_noop(callback: CallbackQuery):
    """Заглушка для не-интерактивных кнопок (например, счётчик страниц)."""
    await callback.answer()