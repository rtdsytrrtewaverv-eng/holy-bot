# ==================== handlers/backup.py ====================
"""
Хендлеры бэкапа БД.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import is_admin, get_db_dump, restore_db
from callbacks import BackupCallback, NavCallback
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb

backup_router = Router(name="backup")


async def backup_menu_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Скачать БД", callback_data=BackupCallback(action="download"))
    builder.button(text="📤 Загрузить БД", callback_data=BackupCallback(action="upload"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(
        breadcrumb("🏠", "💾 Бэкап") + "\n\n<b>Скачайте или восстановите базу данных.</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@backup_router.callback_query(BackupCallback.filter(F.action == "download"))
async def cq_backup_download(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    try:
        data = await get_db_dump()
        from io import BytesIO
        from aiogram.types import BufferedInputFile
        file = BufferedInputFile(data, filename="bot_data.db")
        await bot.send_document(callback.from_user.id, file, caption="💾 Бэкап базы данных")
        await callback.answer("📥 Отправлено в ЛС", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@backup_router.callback_query(BackupCallback.filter(F.action == "upload"))
async def cq_backup_upload(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>📤 Отправьте файл .db для восстановления</b>\n\n"
        "⚠️ Текущая база будет перезаписана!\n"
        "Используйте /cancel для отмены.",
        reply_markup=back_and_menu("backup").as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@backup_router.message(F.document)
async def backup_upload_file(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    doc = message.document
    if not doc.file_name or not doc.file_name.endswith(".db"):
        await message.answer("❌ Отправьте файл с расширением .db")
        return

    try:
        file_data = await bot.download(doc)
        data = file_data.read()
        await restore_db(data)
        await message.answer("✅ База данных восстановлена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка восстановления: {e}")