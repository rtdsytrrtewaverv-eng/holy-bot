# ==================== handlers/backup.py ====================
"""
Хендлеры бэкапа БД.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import is_admin, get_db_dump, restore_db, backup_stats
from callbacks import BackupCallback, NavCallback
from keyboards.common_kb import back_and_menu
from utils.ui import toast, breadcrumb

backup_router = Router(name="backup")


async def backup_menu_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    try:
        stats = await backup_stats()
        info = (
            f"<b>В бэкап войдёт:</b>\n"
            f"📁 Файлов: <b>{stats['files']}</b>\n"
            f"📚 В библиотеке: <b>{stats['library']}</b>\n"
            f"📢 Каналов: <b>{stats['channels']}</b>\n"
            f"👥 Пользователей: <b>{stats['users']}</b>"
        )
    except Exception:
        info = ""

    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Скачать БД", callback_data=BackupCallback(action="download"))
    builder.button(text="📤 Загрузить БД", callback_data=BackupCallback(action="upload"))
    builder.attach(back_and_menu("admin"))
    builder.adjust(1)

    await callback.message.edit_text(
        breadcrumb("🏠", "💾 Бэкап") + "\n\n"
        "<b>Скачайте или восстановите базу данных.</b>\n\n"
        f"{info}\n\n"
        "<i>Файл bot_data.db содержит все приложения, файлы, каналы, "
        "тексты и настройки. Сами файлы хранятся в Telegram, поэтому "
        "переносятся вместе с ботом (при том же токене).</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@backup_router.callback_query(BackupCallback.filter(F.action == "download"))
async def cq_backup_download(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer("📥 Готовлю бэкап...")
    try:
        data = await get_db_dump()
        from aiogram.types import BufferedInputFile
        from datetime import datetime
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file = BufferedInputFile(data, filename=f"bot_data_{stamp}.db")
        await bot.send_document(
            callback.from_user.id, file,
            caption=(
                "💾 <b>Бэкап базы данных</b>\n\n"
                "Сохраните этот файл — в нём все приложения, файлы, "
                "каналы, тексты и настройки. Загрузите его на новом "
                "хостинге через 📤 Загрузить БД."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@backup_router.callback_query(BackupCallback.filter(F.action == "upload"))
async def cq_backup_upload(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>📤 Восстановление базы данных</b>\n\n"
        "Отправьте файл <code>.db</code> (скачанный через 📥 Скачать БД).\n\n"
        "⚠️ Текущая база будет <b>полностью заменена</b> данными из файла.\n"
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

    await message.answer("⏳ Восстанавливаю базу данных...")
    try:
        file_data = await bot.download(doc)
        data = file_data.read()
        await restore_db(data)
        stats = await backup_stats()
        await message.answer(
            "✅ <b>База данных восстановлена!</b>\n\n"
            f"📁 Файлов: <b>{stats['files']}</b>\n"
            f"📚 В библиотеке: <b>{stats['library']}</b>\n"
            f"📢 Каналов: <b>{stats['channels']}</b>\n"
            f"👥 Пользователей: <b>{stats['users']}</b>\n\n"
            "Все приложения и файлы на месте.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка восстановления: {e}")