# ==================== handlers/settings.py ====================
"""
Хендлеры настроек: подписка, тех.работы, админы.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    is_admin, get_setting, set_setting, set_admin, get_user,
)
from callbacks import SettingsCallback, NavCallback
from states import AddAdminStates
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb

settings_router = Router(name="settings")


@settings_router.message(Command("cancel"), StateFilter(AddAdminStates))
async def cmd_cancel_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


async def settings_menu_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    sub_req = await get_setting("subscribe_required")
    maint = await get_setting("maintenance_mode")

    sub_status = "✅ Включена" if sub_req == "1" else "❌ Выключена"
    maint_status = "🚧 Включены" if maint == "1" else "✅ Выключены"

    text = (
        f"{breadcrumb('🏠', '⚙️ Настройки')}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔒 <b>Проверка подписки:</b> {sub_status}\n"
        f"🚧 <b>Тех.работы:</b> {maint_status}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Вкл/Выкл подписку", callback_data=SettingsCallback(action="toggle_subscribe"))
    builder.button(text="🚧 Вкл/Выкл тех.работы", callback_data=SettingsCallback(action="toggle_maintenance"))
    builder.button(text="➕ Добавить админа", callback_data=SettingsCallback(action="add_admin"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@settings_router.callback_query(SettingsCallback.filter(F.action == "toggle_subscribe"))
async def cq_toggle_subscribe(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    current = await get_setting("subscribe_required")
    new_val = "0" if current == "1" else "1"
    await set_setting("subscribe_required", new_val)
    await callback.answer(f"✅ Проверка подписки {'включена' if new_val == '1' else 'выключена'}", show_alert=True)
    await settings_menu_handler(callback)


@settings_router.callback_query(SettingsCallback.filter(F.action == "toggle_maintenance"))
async def cq_toggle_maintenance(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    current = await get_setting("maintenance_mode")
    new_val = "0" if current == "1" else "1"
    await set_setting("maintenance_mode", new_val)
    await callback.answer(f"✅ Тех.работы {'включены' if new_val == '1' else 'выключены'}", show_alert=True)
    await settings_menu_handler(callback)


@settings_router.callback_query(SettingsCallback.filter(F.action == "add_admin"))
async def cq_add_admin(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(AddAdminStates.user_id)
    await callback.message.edit_text(
        "<b>➕ Добавление админа</b>\n\n"
        "Отправьте Telegram ID пользователя.\n"
        "Используйте /cancel для отмены.",
        reply_markup=back_and_menu("settings").as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@settings_router.message(AddAdminStates.user_id)
async def add_admin_user_id(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID.")
        return

    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден в боте. Пусть сначала напишет /start.")
        return

    await set_admin(user_id, True)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{user_id}</code> теперь админ.", parse_mode="HTML")