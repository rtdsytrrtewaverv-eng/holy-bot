# ==================== handlers/broadcast.py ====================
"""
Хендлеры рассылок.
"""

import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter

from database import (
    is_admin, create_broadcast,
)
from callbacks import BroadcastCallback, NavCallback
from states import BroadcastStates
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb
from utils.broadcast_handler import execute_broadcast

broadcast_router = Router(name="broadcast")


@broadcast_router.message(Command("cancel"), StateFilter(BroadcastStates))
async def cmd_cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


async def broadcast_menu_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    builder = back_and_menu("admin")
    # Добавляем кнопку "Новая рассылка" первой
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📣 Создать рассылку", callback_data=BroadcastCallback(action="new"))
    kb.attach(builder)
    kb.adjust(1)

    await callback.message.edit_text(
        breadcrumb("🏠", "📣 Рассылка") + "\n\n<b>Создайте новую рассылку или вернитесь назад.</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@broadcast_router.callback_query(BroadcastCallback.filter(F.action == "new"))
async def cq_broadcast_new(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(BroadcastStates.message_content)
    await callback.message.edit_text(
        "<b>📣 Новая рассылка</b>\n\n"
        "Отправьте сообщение для рассылки:\n"
        "• Текст (поддерживает HTML)\n"
        "• Фото (с подписью или без)\n"
        "• Видео\n\n"
        "Используйте /cancel для отмены.\n"
        "Затем вы сможете добавить кнопку.",
        parse_mode="HTML"
    )
    await callback.answer()


@broadcast_router.message(BroadcastStates.message_content)
async def broadcast_content(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    msg_type = "text"
    msg_content = message.text or message.caption or ""

    if message.photo:
        msg_type = "photo"
        msg_content = message.photo[-1].file_id
    elif message.video:
        msg_type = "video"
        msg_content = message.video.file_id

    await state.update_data(msg_type=msg_type, msg_content=msg_content)
    await state.set_state(BroadcastStates.button_text)
    await message.answer(
        "<b>🔘 Добавьте кнопку (опционально)</b>\n\n"
        "Отправьте <b>текст кнопки</b> (например: «Перейти в канал»).\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@broadcast_router.message(BroadcastStates.button_text)
async def broadcast_button_text(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    btn_text = message.text.strip()
    if btn_text == "-":
        btn_text = ""
    await state.update_data(button_text=btn_text)
    if btn_text:
        await state.set_state(BroadcastStates.button_url)
        await message.answer(
            "<b>🔗 Отправьте URL для кнопки</b>\n\n"
            "Например: <code>https://t.me/holy_IPA</code>",
            parse_mode="HTML"
        )
    else:
        await finish_broadcast(message, state, "")


@broadcast_router.message(BroadcastStates.button_url)
async def broadcast_button_url(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    url = message.text.strip()
    await finish_broadcast(message, state, url)


async def finish_broadcast(message: Message, state: FSMContext, button_url: str):
    data = await state.get_data()
    msg_type = data["msg_type"]
    msg_content = data["msg_content"]
    button_text = data.get("button_text", "")
    await state.clear()

    # Выбор фильтра
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Всем", callback_data=BroadcastCallback(action="send", filter_type="all", broadcast_id=0))
    kb.button(text="✅ Подписанным", callback_data=BroadcastCallback(action="send", filter_type="subscribed", broadcast_id=0))
    kb.button(text="🟢 Активным", callback_data=BroadcastCallback(action="send", filter_type="active", broadcast_id=0))
    kb.attach(back_and_menu("broadcast"))
    kb.adjust(1)

    await state.update_data(
        msg_type=msg_type,
        msg_content=msg_content,
        button_text=button_text,
        button_url=button_url,
    )
    await message.answer(
        "<b>👥 Выберите аудиторию для рассылки:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@broadcast_router.callback_query(BroadcastCallback.filter(F.action == "send"))
async def cq_broadcast_send(callback: CallbackQuery, callback_data: BroadcastCallback, state: FSMContext, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    if not data:
        await callback.answer("❌ Данные утеряны, начните заново", show_alert=True)
        return

    filter_type = callback_data.filter_type
    msg_type = data["msg_type"]
    msg_content = data["msg_content"]
    button_text = data.get("button_text", "")
    button_url = data.get("button_url", "")

    bc_id = await create_broadcast(callback.from_user.id, msg_type, msg_content)
    await state.clear()

    await callback.answer("📣 Рассылка запущена!")
    await callback.message.edit_text(
        "<b>📣 Рассылка выполняется...</b>\n\n"
        f"Тип: {msg_type}\n"
        f"Аудитория: {filter_type}\n"
        f"ID рассылки: {bc_id}",
        parse_mode="HTML"
    )

    # Запускаем в фоне
    asyncio.create_task(
        execute_broadcast(
            bot=bot,
            broadcast_id=bc_id,
            message_type=msg_type,
            message_content=msg_content,
            button_text=button_text,
            button_url=button_url,
            filter_type=filter_type,
        )
    )