# ==================== handlers/settings.py ====================
"""
Хендлеры настроек: подписка, тех.работы, админы, цвета кнопок, библиотека.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    is_admin, get_setting, set_setting, set_admin, get_user,
)
from callbacks import SettingsCallback
from states import AddAdminStates
from keyboards.common_kb import back_and_menu
from utils.ui import breadcrumb

settings_router = Router(name="settings")

STYLE_LABELS = {
    "primary": "🔵 Синяя",
    "success": "🟢 Зелёная",
    "danger": "🔴 Красная",
    "": "⚪ По умолчанию",
}

STYLE_KEYS = {
    "style_main": ("button_style_main", "Цвет кнопок меню"),
    "style_file": ("button_style_file", "Цвет кнопок на экране файла"),
    "style_howto": ("button_style_howto", "Цвет кнопки «Как установить?»"),
    "style_library": ("button_style_library", "Цвет кнопок библиотеки"),
    "style_back": ("button_style_back", "Цвет кнопки «Главное меню»"),
}


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
    lib = await get_setting("library_enabled")

    sub_status = "✅ Включена" if sub_req == "1" else "❌ Выключена"
    maint_status = "🚧 Включены" if maint == "1" else "✅ Выключены"
    lib_status = "✅ Включена" if lib != "0" else "❌ Выключена"

    text = (
        f"{breadcrumb('🏠', '⚙️ Настройки')}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔒 <b>Проверка подписки:</b> {sub_status}\n"
        f"🚧 <b>Тех.работы:</b> {maint_status}\n"
        f"📚 <b>Библиотека:</b> {lib_status}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<i>Библиотека доступна только подписчикам указанных каналов.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Вкл/Выкл подписку", callback_data=SettingsCallback(action="toggle_subscribe"))
    builder.button(text="🚧 Вкл/Выкл тех.работы", callback_data=SettingsCallback(action="toggle_maintenance"))
    builder.button(text="📚 Вкл/Выкл библиотеку", callback_data=SettingsCallback(action="toggle_library"))
    builder.button(text="🎨 Цвета кнопок", callback_data=SettingsCallback(action="styles"))
    builder.button(text="➕ Добавить админа", callback_data=SettingsCallback(action="add_admin"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


def _styles_menu_kb():
    builder = InlineKeyboardBuilder()
    for action, (key, label) in STYLE_KEYS.items():
        builder.button(text=label, callback_data=SettingsCallback(action=action))
    builder.attach(back_and_menu("settings"))
    builder.adjust(1)
    return builder


async def styles_menu_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    lines = ["<b>🎨 Цвета кнопок</b>\n"]
    for action, (key, label) in STYLE_KEYS.items():
        cur = (await get_setting(key)) or ""
        lines.append(f"• {label}: {STYLE_LABELS.get(cur, '⚪ По умолчанию')}")
    lines.append("\n<i>Нажмите на пункт, чтобы выбрать цвет.</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=_styles_menu_kb().as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


async def _style_choice_handler(callback: CallbackQuery, action: str):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    key, label = STYLE_KEYS[action]
    current = (await get_setting(key)) or ""

    builder = InlineKeyboardBuilder()
    for value, text in STYLE_LABELS.items():
        mark = "✅ " if value == current else ""
        builder.button(
            text=f"{mark}{text}",
            callback_data=SettingsCallback(action=f"choose|{action}|{value}")
        )
    builder.button(text="⬅️ Назад", callback_data=SettingsCallback(action="styles"))
    builder.adjust(1)

    await callback.message.edit_text(
        f"<b>🎨 {label}</b>\n\nВыберите цвет кнопок:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@settings_router.callback_query(SettingsCallback.filter(F.action == "styles"))
async def cq_styles(callback: CallbackQuery):
    await styles_menu_handler(callback)


@settings_router.callback_query(SettingsCallback.filter(F.action.in_({"style_main", "style_file", "style_howto", "style_library", "style_back"})))
async def cq_style_choice(callback: CallbackQuery, callback_data: SettingsCallback):
    await _style_choice_handler(callback, callback_data.action)


@settings_router.callback_query(SettingsCallback.filter(F.action.startswith("choose|")))
async def cq_style_apply(callback: CallbackQuery, callback_data: SettingsCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    try:
        _, action, value = callback_data.action.split("|", 2)
    except ValueError:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    if action not in STYLE_KEYS:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    key, label = STYLE_KEYS[action]
    await set_setting(key, value)
    await callback.answer(f"✅ {label}: {STYLE_LABELS.get(value, value)}", show_alert=True)
    await _style_choice_handler(callback, action)


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


@settings_router.callback_query(SettingsCallback.filter(F.action == "toggle_library"))
async def cq_toggle_library(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    current = await get_setting("library_enabled")
    new_val = "1" if current == "0" else "0"
    await set_setting("library_enabled", new_val)
    await callback.answer(f"✅ Библиотека {'включена' if new_val == '1' else 'выключена'}", show_alert=True)
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
