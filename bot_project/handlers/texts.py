# ==================== handlers/texts.py ====================
"""
Хендлеры управления текстами и медиа.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter

from database import (
    is_admin, get_all_texts, get_text, set_text, set_media, delete_media, get_media,
)
from callbacks import TextCallback, NavCallback
from states import EditTextStates, EditMediaStates
from keyboards.texts_kb import texts_menu, texts_list_kb, medias_menu_kb, media_edit_kb
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb

texts_router = Router(name="texts")


@texts_router.message(Command("cancel"), StateFilter(EditTextStates))
@texts_router.message(Command("cancel"), StateFilter(EditMediaStates))
async def cmd_cancel_texts(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


@texts_router.callback_query(TextCallback.filter(F.action == "list_texts"))
async def cq_texts_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    texts = await get_all_texts()
    await callback.message.edit_text(
        breadcrumb("🏠", "💬 Тексты и медиа", "📝 Тексты") + "\n\n<b>Выберите текст для редактирования:</b>",
        reply_markup=texts_list_kb(texts),
        parse_mode="HTML"
    )
    await callback.answer()


@texts_router.callback_query(TextCallback.filter(F.action == "edit_text"))
async def cq_texts_edit(callback: CallbackQuery, callback_data: TextCallback, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    key = callback_data.key
    current = await get_text(key)
    labels = {
        "start_text": "👋 Текст приветствия",
        "subscribe_text": "🔒 Текст «Подпишись»",
        "subscription_confirmed": "✅ Текст «Подписка подтверждена»",
        "file_not_found": "❌ Текст «Файл не найден»",
        "help_text": "ℹ️ Помощь",
        "support_username": "📞 Юзернейм поддержки",
        "support_text": "📞 Текст поддержки",
        "howto_button_text": "📖 Текст кнопки «Как установить?»",
        "tech_works": "🚧 Текст тех.работ",
    }
    label = labels.get(key, key)

    await state.set_state(EditTextStates.waiting_value)
    await state.update_data(text_key=key)
    await callback.message.edit_text(
        f"<b>✏️ Редактирование: {label}</b>\n\n"
        f"<b>Текущее значение:</b>\n<code>{current[:500]}</code>\n\n"
        f"Отправьте новый текст. Поддерживается HTML.\n"
        f"Используйте /cancel для отмены.",
        parse_mode="HTML"
    )
    await callback.answer()


@texts_router.message(EditTextStates.waiting_value)
async def edit_text_value(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data["text_key"]
    value = message.text or message.caption or ""

    await set_text(key, value)
    await state.clear()
    await message.answer("✅ Текст обновлён.")

    # Показываем меню текстов заново
    texts = await get_all_texts()
    await message.answer(
        breadcrumb("🏠", "💬 Тексты и медиа", "📝 Тексты") + "\n\n<b>Выберите текст для редактирования:</b>",
        reply_markup=texts_list_kb(texts),
        parse_mode="HTML"
    )


@texts_router.callback_query(TextCallback.filter(F.action == "medias_list"))
async def cq_medias_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        breadcrumb("🏠", "💬 Тексты и медиа", "🖼 Картинки") + "\n\n<b>Выберите экран для замены картинки:</b>",
        reply_markup=medias_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@texts_router.callback_query(TextCallback.filter(F.action == "edit_media"))
async def cq_media_edit(callback: CallbackQuery, callback_data: TextCallback, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    key = callback_data.key
    media = await get_media(key)
    labels = {
        "start_photo": "🖼 Картинка /start",
        "subscribe_photo": "🖼 Картинка подписки",
    }
    label = labels.get(key, key)

    # Показываем текущее фото если есть
    if media and media.get("file_id"):
        try:
            await callback.message.answer_photo(media["file_id"], caption=f"<b>Текущая картинка:</b> {label}", parse_mode="HTML")
        except Exception:
            pass

    await state.set_state(EditMediaStates.waiting_photo)
    await state.update_data(media_key=key)
    await callback.message.edit_text(
        f"<b>📷 Замена картинки для: {label}</b>\n\n"
        f"Отправьте новое фото. Используйте /cancel для отмены.",
        reply_markup=media_edit_kb(key),
        parse_mode="HTML"
    )
    await callback.answer()


@texts_router.message(EditMediaStates.waiting_photo, F.photo)
async def edit_media_photo(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data["media_key"]
    file_id = message.photo[-1].file_id

    await set_media(key, file_id, "photo")
    await state.clear()
    await message.answer("✅ Картинка обновлена.")

    await message.answer(
        breadcrumb("🏠", "💬 Тексты и медиа", "🖼 Картинки") + "\n\n<b>Выберите экран для замены картинки:</b>",
        reply_markup=medias_menu_kb(),
        parse_mode="HTML"
    )


@texts_router.callback_query(TextCallback.filter(F.action == "delete_media"))
async def cq_media_delete(callback: CallbackQuery, callback_data: TextCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await delete_media(callback_data.key)
    await callback.answer("🗑 Картинка удалена", show_alert=True)

    await callback.message.edit_text(
        breadcrumb("🏠", "💬 Тексты и медиа", "🖼 Картинки") + "\n\n<b>Выберите экран для замены картинки:</b>",
        reply_markup=medias_menu_kb(),
        parse_mode="HTML"
    )