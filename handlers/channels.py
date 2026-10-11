# ==================== handlers/channels.py ====================
"""
Хендлеры управления каналами: добавление, список, редактирование, проверка, удаление.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest

from database import (
    is_admin, add_channel, get_all_channels, get_channel,
    update_channel, delete_channel,
)
from callbacks import ChannelCallback, NavCallback
from states import AddChannelStates, EditChannelStates
from keyboards.channels_kb import (
    channels_menu, channels_list_kb, channel_detail_kb, channel_confirm_delete_kb,
)
from utils.ui import toast, breadcrumb, paginate
from utils.subscription import check_single_subscription

channels_router = Router(name="channels")


@channels_router.message(Command("cancel"), StateFilter(AddChannelStates))
@channels_router.message(Command("cancel"), StateFilter(EditChannelStates))
async def cmd_cancel_channels(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


@channels_router.callback_query(ChannelCallback.filter(F.action == "add"))
async def cq_channel_add(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AddChannelStates.title)
    await callback.message.edit_text(
        "<b>📢 Добавление канала</b>\n\n"
        "<b>Шаг 1/3:</b> Введите название канала.\n"
        "Используйте /cancel для отмены.",
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()


@channels_router.message(AddChannelStates.title)
async def add_channel_step_title(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AddChannelStates.chat_id_or_username)
    await message.answer(
        "<b>Шаг 2/3:</b> Отправьте @username или ID канала.\n"
        "Пример: <code>@holy_IPA</code> или <code>-1001234567890</code>",
        parse_mode="HTML"
    )


@channels_router.message(AddChannelStates.chat_id_or_username)
async def add_channel_step_chat_id(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    # Определяем chat_id и username
    chat_id = raw
    username = ""
    if raw.startswith("@") and not raw.startswith("-100"):
        username = raw
        try:
            chat = await bot.get_chat(raw)
            chat_id = str(chat.id)
        except Exception as e:
            await message.answer(f"❌ Не удалось получить канал: {e}")
            return
    else:
        username = ""

    await state.update_data(chat_id=chat_id, username=username)
    await state.set_state(AddChannelStates.invite_link)
    await message.answer(
        "<b>Шаг 3/3:</b> Отправьте пригласительную ссылку или <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@channels_router.message(AddChannelStates.invite_link)
async def add_channel_step_invite(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    invite = message.text.strip()
    if invite == "-":
        invite = ""

    data = await state.get_data()
    await add_channel(
        title=data["title"],
        chat_id=data["chat_id"],
        username=data.get("username", ""),
        invite_link=invite,
        is_required=1,
    )
    await state.clear()
    await message.answer("✅ Канал добавлен.")

    # Возврат к списку
    all_channels = await get_all_channels()
    paged, total_pages = paginate(all_channels, 0, per_page=5)
    await message.answer(
        breadcrumb("🏠", "📢 Управление каналами", "📋 Список") + "\n",
        reply_markup=channels_list_kb(paged, 0, total_pages),
        parse_mode="HTML"
    )


@channels_router.callback_query(ChannelCallback.filter(F.action == "list"))
@channels_router.callback_query(ChannelCallback.filter(F.action == "page"))
async def cq_channel_list(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    page = callback_data.page
    all_channels = await get_all_channels()
    paged, total_pages = paginate(all_channels, page, per_page=5)

    text = breadcrumb("🏠", "📢 Каналы", "📋 Список") + "\n"
    if not paged:
        text += "<i>Каналы не добавлены.</i>"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=channels_list_kb(paged, page, total_pages),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@channels_router.callback_query(ChannelCallback.filter(F.action == "noop"))
async def cq_channel_noop(callback: CallbackQuery):
    """Заглушка для счётчика страниц."""
    await callback.answer()


@channels_router.callback_query(ChannelCallback.filter(F.action == "edit"))
async def cq_channel_edit(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    ch = await get_channel(callback_data.channel_id)
    if not ch:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    active = "✅ Активен" if ch["is_active"] else "❌ Выключен"
    required = "🔒 Обязательный" if ch["is_required"] else "🔓 Необязательный"

    text = (
        f"<b>🏠 › 📢 Каналы › {ch['title'] or ch['username'] or ch['chat_id']}</b>\n\n"
        f"📝 <b>Название:</b> {ch['title'] or '—'}\n"
        f"🆔 <b>Chat ID:</b> <code>{ch['chat_id']}</code>\n"
        f"📎 <b>Username:</b> {ch['username'] or '—'}\n"
        f"🔗 <b>Приглашение:</b> {ch['invite_link'] or '—'}\n"
        f"📊 <b>Статус:</b> {active}\n"
        f"🔐 <b>Тип:</b> {required}\n"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=channel_detail_kb(ch["id"], bool(ch["is_active"]), bool(ch["is_required"])),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@channels_router.callback_query(ChannelCallback.filter(F.action == "edit_field"))
async def cq_channel_edit_field(callback: CallbackQuery, callback_data: ChannelCallback, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    field = callback_data.field
    channel_id = callback_data.channel_id
    if field in ("title", "invite_link"):
        labels = {"title": "название", "invite_link": "пригласительную ссылку"}
        await state.set_state(EditChannelStates.waiting_value)
        await state.update_data(channel_id=channel_id, field=field)
        await callback.message.edit_text(
            f"<b>✏️ Введите новое {labels[field]}</b>\nИспользуйте /cancel для отмены.",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Поле не редактируется", show_alert=True)


@channels_router.message(EditChannelStates.waiting_value)
async def edit_channel_value(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await update_channel(data["channel_id"], **{data["field"]: message.text.strip()})
    await state.clear()
    await message.answer("✅ Обновлено.")
    ch = await get_channel(data["channel_id"])
    if ch:
        active = "✅ Активен" if ch["is_active"] else "❌ Выключен"
        required = "🔒 Обязательный" if ch["is_required"] else "🔓 Необязательный"
        text = (
            f"<b>🏠 › 📢 Каналы › {ch['title'] or ch['username'] or ch['chat_id']}</b>\n\n"
            f"📝 <b>Название:</b> {ch['title'] or '—'}\n"
            f"🆔 <b>Chat ID:</b> <code>{ch['chat_id']}</code>\n"
            f"📎 <b>Username:</b> {ch['username'] or '—'}\n"
            f"🔗 <b>Приглашение:</b> {ch['invite_link'] or '—'}\n"
            f"📊 <b>Статус:</b> {active}\n"
            f"🔐 <b>Тип:</b> {required}\n"
        )
        await message.answer(
            text,
            reply_markup=channel_detail_kb(ch["id"], bool(ch["is_active"]), bool(ch["is_required"])),
            parse_mode="HTML"
        )


@channels_router.callback_query(ChannelCallback.filter(F.action == "toggle_active"))
async def cq_channel_toggle_active(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    ch = await get_channel(callback_data.channel_id)
    if ch:
        await update_channel(ch["id"], is_active=int(not ch["is_active"]))
    await callback.answer("✅ Переключено")
    await cq_channel_edit(callback, callback_data)


@channels_router.callback_query(ChannelCallback.filter(F.action == "toggle_required"))
async def cq_channel_toggle_required(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    ch = await get_channel(callback_data.channel_id)
    if ch:
        await update_channel(ch["id"], is_required=int(not ch["is_required"]))
    await callback.answer("✅ Переключено")
    await cq_channel_edit(callback, callback_data)


@channels_router.callback_query(ChannelCallback.filter(F.action == "check"))
async def cq_channel_check(callback: CallbackQuery, callback_data: ChannelCallback, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    ch = await get_channel(callback_data.channel_id)
    if not ch:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    # Проверяем реальный статус БОТА в канале (нужен админ для get_chat_member)
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=me.id)
        status = member.status
    except Exception as e:
        await callback.answer(
            f"❌ Канал недоступен: {e}\nПроверьте, что бот добавлен в канал.",
            show_alert=True
        )
        return

    if status in ("administrator", "creator"):
        await callback.answer(
            f"✅ Бот — администратор канала (статус: {status}).\nПроверка подписки работает.",
            show_alert=True
        )
    else:
        await callback.answer(
            f"⚠️ Бот имеет статус «{status}», а нужен АДМИНИСТРАТОР.\n"
            f"Без прав админа проверка подписки не работает!",
            show_alert=True
        )


@channels_router.callback_query(ChannelCallback.filter(F.action == "delete"))
async def cq_channel_delete(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>⚠️ Удалить этот канал?</b>",
        reply_markup=channel_confirm_delete_kb(callback_data.channel_id),
        parse_mode="HTML"
    )
    await callback.answer()


@channels_router.callback_query(ChannelCallback.filter(F.action == "confirm_delete"))
async def cq_channel_confirm_delete(callback: CallbackQuery, callback_data: ChannelCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await delete_channel(callback_data.channel_id)
    await callback.answer("✅ Канал удалён", show_alert=True)
    await cq_channel_list(callback, ChannelCallback(action="list", page=0))