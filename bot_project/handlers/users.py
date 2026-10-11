# ==================== handlers/users.py ====================
"""
Хендлеры управления пользователями: список, поиск, карточка, бан/разбан.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    is_admin, get_all_users, get_user, set_banned,
)
from callbacks import UserCallback, NavCallback
from states import UserSearchStates
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb, paginate, add_pagination_buttons

users_router = Router(name="users")


@users_router.message(Command("cancel"), StateFilter(UserSearchStates))
async def cmd_cancel_users(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


async def users_list_handler(callback: CallbackQuery, page: int = 0):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    all_users = await get_all_users()
    paged, total_pages = paginate(all_users, page, per_page=5)

    text = breadcrumb("🏠", "👥 Пользователи") + "\n"
    if not paged:
        text += "<i>Нет пользователей.</i>"

    builder = InlineKeyboardBuilder()
    for u in paged:
        badge = "🚫" if u["is_banned"] else "👤"
        admin_badge = " ⭐" if u["is_admin"] else ""
        label = u.get("username") or u.get("first_name") or str(u["user_id"])
        if len(label) > 30:
            label = label[:27] + "..."
        builder.button(
            text=f"{badge}{admin_badge} {label}",
            callback_data=UserCallback(action="card", user_id=u["user_id"])
        )
    builder.adjust(1)

    add_pagination_buttons(builder, page, total_pages, UserCallback)

    # Кнопка поиска
    builder.button(text="🔍 Поиск", callback_data=UserCallback(action="search"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@users_router.callback_query(UserCallback.filter(F.action == "list"))
async def cq_users_list(callback: CallbackQuery, callback_data: UserCallback):
    await users_list_handler(callback, callback_data.page)


@users_router.callback_query(UserCallback.filter(F.action == "page"))
async def cq_users_page(callback: CallbackQuery, callback_data: UserCallback):
    await users_list_handler(callback, callback_data.page)


@users_router.callback_query(UserCallback.filter(F.action == "noop"))
async def cq_users_noop(callback: CallbackQuery):
    """Заглушка для счётчика страниц."""
    await callback.answer()


@users_router.callback_query(UserCallback.filter(F.action == "card"))
async def cq_user_card(callback: CallbackQuery, callback_data: UserCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    user = await get_user(callback_data.user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    banned = "🚫 Забанен" if user["is_banned"] else "✅ Активен"
    admin = "⭐ Админ" if user["is_admin"] else "👤 Пользователь"

    text = (
        f"{breadcrumb('🏠', '👥 Пользователи', str(user['user_id']))}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"📛 <b>Username:</b> @{user['username'] or '—'}\n"
        f"📝 <b>Имя:</b> {user['first_name'] or '—'}\n"
        f"📅 <b>Присоединился:</b> {user['joined_at'] or '—'}\n"
        f"📥 <b>Скачиваний:</b> {user['files_downloaded']}\n"
        f"📊 <b>Статус:</b> {banned}\n"
        f"🔐 <b>Роль:</b> {admin}\n"
        f"━━━━━━━━━━━━━━━━"
    )

    builder = InlineKeyboardBuilder()
    if user["is_banned"]:
        builder.button(
            text="✅ Разбанить",
            callback_data=UserCallback(action="unban", user_id=user["user_id"])
        )
    else:
        builder.button(
            text="🚫 Забанить",
            callback_data=UserCallback(action="ban", user_id=user["user_id"])
        )
    builder.attach(
        InlineKeyboardBuilder().button(
            text="⬅️ К списку",
            callback_data=UserCallback(action="list", page=0)
        )
    )
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@users_router.callback_query(UserCallback.filter(F.action == "ban"))
async def cq_user_ban(callback: CallbackQuery, callback_data: UserCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await set_banned(callback_data.user_id, True)
    await callback.answer("🚫 Пользователь забанен", show_alert=True)
    await cq_user_card(callback, callback_data)


@users_router.callback_query(UserCallback.filter(F.action == "unban"))
async def cq_user_unban(callback: CallbackQuery, callback_data: UserCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await set_banned(callback_data.user_id, False)
    await callback.answer("✅ Пользователь разбанен", show_alert=True)
    await cq_user_card(callback, callback_data)


@users_router.callback_query(UserCallback.filter(F.action == "search"))
async def cq_user_search(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(UserSearchStates.query)
    await callback.message.edit_text(
        "<b>🔍 Поиск пользователя</b>\n\n"
        "Отправьте ID, @username или имя.\n"
        "Используйте /cancel для отмены.",
        reply_markup=back_and_menu("users").as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@users_router.message(UserSearchStates.query)
async def search_user(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    query = message.text.strip()
    found = None

    # Поиск по ID
    if query.isdigit():
        found = await get_user(int(query))

    # Поиск по username
    if not found:
        clean = query.lstrip("@")
        all_users = await get_all_users()
        for u in all_users:
            if u.get("username") == clean:
                found = u
                break
            if u.get("first_name") and query.lower() in u["first_name"].lower():
                found = u
                break

    await state.clear()

    if found:
        banned = "🚫 Забанен" if found["is_banned"] else "✅ Активен"
        admin = "⭐ Админ" if found["is_admin"] else "👤 Пользователь"
        text = (
            f"{breadcrumb('🏠', '👥 Пользователи', str(found['user_id']))}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{found['user_id']}</code>\n"
            f"📛 <b>Username:</b> @{found['username'] or '—'}\n"
            f"📝 <b>Имя:</b> {found['first_name'] or '—'}\n"
            f"📅 <b>Присоединился:</b> {found['joined_at'] or '—'}\n"
            f"📥 <b>Скачиваний:</b> {found['files_downloaded']}\n"
            f"📊 <b>Статус:</b> {banned}\n"
            f"🔐 <b>Роль:</b> {admin}\n"
            f"━━━━━━━━━━━━━━━━"
        )

        builder = InlineKeyboardBuilder()
        if found["is_banned"]:
            builder.button(text="✅ Разбанить", callback_data=UserCallback(action="unban", user_id=found["user_id"]))
        else:
            builder.button(text="🚫 Забанить", callback_data=UserCallback(action="ban", user_id=found["user_id"]))
        builder.attach(back_and_menu("users"))
        builder.adjust(1)

        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer("❌ Пользователь не найден.", reply_markup=back_and_menu("users").as_markup())