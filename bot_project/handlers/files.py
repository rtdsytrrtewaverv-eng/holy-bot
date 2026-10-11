# ==================== handlers/files.py ====================
"""
Хендлеры управления файлами: добавление, список, редактирование, удаление, ссылка.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest

from database import (
    is_admin, add_file, get_all_files, count_files, get_file_by_id,
    update_file_field, update_file, delete_file, get_text,
)
from callbacks import FileCallback, NavCallback, ConfirmCallback
from states import AddFileStates, EditFileStates
from keyboards.files_kb import (
    files_menu, file_list_kb, file_detail_kb, file_edit_fields_kb,
    file_confirm_delete_kb,
)
from utils.ui import toast, breadcrumb, paginate, sanitize_slug

files_router = Router(name="files")


@files_router.message(Command("cancel"), StateFilter(AddFileStates))
@files_router.message(Command("cancel"), StateFilter(EditFileStates))
async def cmd_cancel_files(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Действие отменено.")


@files_router.callback_query(FileCallback.filter(F.action == "add"))
async def cq_file_add(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AddFileStates.file)
    await callback.answer()
    await callback.message.edit_text(
        "<b>📤 Отправьте файл</b>\n\n"
        "Поддерживаются: документы, видео, аудио, голосовые.\n"
        "Отправьте файл или нажмите /cancel для отмены.",
        reply_markup=None,
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.file, F.content_type.in_({"document", "video", "audio", "voice"}))
async def add_file_step_file(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"
    else:
        await message.answer("❌ Неподдерживаемый тип. Отправьте документ, видео, аудио или голосовое.")
        return

    await state.update_data(file_id=file_id, file_type=file_type)
    await state.set_state(AddFileStates.slug)
    await message.answer(
        "<b>🔤 Введите slug</b>\n\n"
        "Slug — короткий уникальный идентификатор (латиница, цифры, дефисы).\n"
        "Пример: <code>my-cool-file</code>\n\n"
        "Используйте /cancel для отмены.",
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.slug)
async def add_file_step_slug(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    raw_slug = message.text.strip()
    slug = sanitize_slug(raw_slug)
    if not slug:
        await message.answer(
            "❌ Slug пустой после обработки. Используйте латиницу, цифры, дефис или подчёркивание.\n"
            "Пример: <code>yandex-music-809</code>",
            parse_mode="HTML"
        )
        return
    if slug != raw_slug.lower():
        await message.answer(
            f"ℹ️ Slug приведён к допустимому виду: <code>{slug}</code>\n"
            f"<i>(Telegram не поддерживает точки и другие символы в ссылках)</i>",
            parse_mode="HTML"
        )
    await state.update_data(slug=slug)
    await state.set_state(AddFileStates.title)
    await message.answer(
        "<b>📝 Введите название файла</b>\n\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.title)
async def add_file_step_title(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if title == "-":
        title = ""
    await state.update_data(title=title)
    await state.set_state(AddFileStates.description)
    await message.answer(
        "<b>📄 Введите описание файла</b>\n\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.description)
async def add_file_step_description(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    description = message.text.strip()
    if description == "-":
        description = ""
    await state.update_data(description=description)
    await state.set_state(AddFileStates.howto_url)
    await message.answer(
        "<b>🔗 Введите ссылку для кнопки «Как установить?»</b>\n\n"
        "Или отправьте <code>-</code> чтобы использовать по умолчанию.",
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.howto_url)
async def add_file_step_howto(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    howto_url = message.text.strip()
    if howto_url == "-":
        howto_url = ""

    data = await state.get_data()

    try:
        fid = await add_file(
            slug=data["slug"],
            file_type=data["file_type"],
            file_id=data["file_id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            howto_url=howto_url,
        )
        await state.clear()
        link = f"https://t.me/{(await message.bot.get_me()).username}?start=file_{data['slug']}"
        await message.answer(
            f"<b>✅ Файл добавлен!</b>\n\n"
            f"🔗 <b>Ссылка для поста:</b>\n<code>{link}</code>\n\n"
            f"Скопируйте и вставьте в кнопку поста канала.",
            parse_mode="HTML"
        )
        # Возврат в меню файлов
        await message.answer(
            f"<b>🏠 › 📁 Управление файлами</b>\n",
            reply_markup=files_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@files_router.callback_query(FileCallback.filter(F.action == "list"))
@files_router.callback_query(FileCallback.filter(F.action == "page"))
async def cq_file_list(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    page = callback_data.page
    all_files = await get_all_files(limit=999999, offset=0)
    paged, total_pages = paginate(all_files, page, per_page=5)

    text = f"<b>🏠 › 📁 Управление файлами › 📋 Список</b>\n\n"
    if not paged:
        text += "<i>Файлы не добавлены.</i>"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=file_list_kb(paged, page, total_pages),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@files_router.callback_query(FileCallback.filter(F.action == "noop"))
async def cq_file_noop(callback: CallbackQuery):
    """Заглушка для счётчика страниц."""
    await callback.answer()


@files_router.callback_query(FileCallback.filter(F.action == "edit"))
async def cq_file_edit(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    file_data = await get_file_by_id(callback_data.file_id)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    text = (
        f"<b>🏠 › 📁 Файлы › 📄 {file_data['title'] or file_data['slug']}</b>\n\n"
        f"📝 <b>Название:</b> {file_data['title'] or '—'}\n"
        f"📄 <b>Описание:</b> {file_data['description'] or '—'}\n"
        f"🔤 <b>Slug:</b> <code>{file_data['slug']}</code>\n"
        f"📎 <b>Тип:</b> {file_data['file_type']}\n"
        f"🔗 <b>Ссылка «Как уст.»:</b> {file_data['howto_url'] or '(по умолчанию)'}\n"
        f"📥 <b>Скачиваний:</b> {file_data['downloads']}\n"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=file_detail_kb(callback_data.file_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@files_router.callback_query(FileCallback.filter(F.action == "edit_field"))
async def cq_file_edit_field(callback: CallbackQuery, callback_data: FileCallback, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    field = callback_data.field
    file_id = callback_data.file_id

    if field in ("title", "description", "howto_url", "slug"):
        field_labels = {
            "title": "название",
            "description": "описание",
            "howto_url": "ссылку «Как установить?»",
            "slug": "slug",
        }
        await state.set_state(EditFileStates.waiting_value)
        await state.update_data(file_id=file_id, field=field)
        await callback.message.edit_text(
            f"<b>✏️ Введите новое {field_labels[field]}</b>\n\n"
            f"Используйте /cancel для отмены.",
            parse_mode="HTML"
        )
        await callback.answer()
    elif field == "file_id":
        await state.set_state(EditFileStates.waiting_file)
        await state.update_data(file_id=file_id)
        await callback.message.edit_text(
            "<b>📤 Отправьте новый файл</b>\n\n"
            "Документ, видео, аудио или голосовое.\n"
            "Используйте /cancel для отмены.",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Неизвестное поле", show_alert=True)


@files_router.message(EditFileStates.waiting_value)
async def edit_file_value(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    file_id = data["file_id"]
    field = data["field"]
    value = message.text.strip()

    if field == "slug":
        cleaned = sanitize_slug(value)
        if not cleaned:
            await message.answer("❌ Slug пустой после обработки. Попробуйте снова или /cancel.")
            return
        if cleaned != value.lower():
            await message.answer(f"ℹ️ Slug приведён к <code>{cleaned}</code>", parse_mode="HTML")
        value = cleaned

    await update_file_field(file_id, field, value)
    await state.clear()
    await message.answer("✅ Значение обновлено.")

    file_data = await get_file_by_id(file_id)
    if file_data:
        text = (
            f"<b>🏠 › 📁 Файлы › 📄 {file_data['title'] or file_data['slug']}</b>\n\n"
            f"📝 <b>Название:</b> {file_data['title'] or '—'}\n"
            f"📄 <b>Описание:</b> {file_data['description'] or '—'}\n"
            f"🔤 <b>Slug:</b> <code>{file_data['slug']}</code>\n"
            f"📎 <b>Тип:</b> {file_data['file_type']}\n"
            f"🔗 <b>Ссылка «Как уст.»:</b> {file_data['howto_url'] or '(по умолчанию)'}\n"
            f"📥 <b>Скачиваний:</b> {file_data['downloads']}\n"
        )
        await message.answer(text, reply_markup=file_detail_kb(file_id), parse_mode="HTML")


@files_router.message(EditFileStates.waiting_file, F.content_type.in_({"document", "video", "audio", "voice"}))
async def edit_file_file(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    file_id_db = data["file_id"]

    if message.document:
        new_file_id = message.document.file_id
        file_type = "document"
    elif message.video:
        new_file_id = message.video.file_id
        file_type = "video"
    elif message.audio:
        new_file_id = message.audio.file_id
        file_type = "audio"
    elif message.voice:
        new_file_id = message.voice.file_id
        file_type = "voice"
    else:
        return

    await update_file(file_id_db, file_id=new_file_id, file_type=file_type)
    await state.clear()
    await message.answer("✅ Файл обновлён.")

    file_data = await get_file_by_id(file_id_db)
    if file_data:
        text = (
            f"<b>🏠 › 📁 Файлы › 📄 {file_data['title'] or file_data['slug']}</b>\n\n"
            f"📝 <b>Название:</b> {file_data['title'] or '—'}\n"
            f"📄 <b>Описание:</b> {file_data['description'] or '—'}\n"
            f"🔤 <b>Slug:</b> <code>{file_data['slug']}</code>\n"
            f"📎 <b>Тип:</b> {file_data['file_type']}\n"
            f"📥 <b>Скачиваний:</b> {file_data['downloads']}\n"
        )
        await message.answer(text, reply_markup=file_detail_kb(file_id_db), parse_mode="HTML")


@files_router.callback_query(FileCallback.filter(F.action == "delete"))
async def cq_file_delete(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>⚠️ Вы уверены, что хотите удалить этот файл?</b>",
        reply_markup=file_confirm_delete_kb(callback_data.file_id),
        parse_mode="HTML"
    )
    await callback.answer()


@files_router.callback_query(FileCallback.filter(F.action == "confirm_delete"))
async def cq_file_confirm_delete(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await delete_file(callback_data.file_id)
    await callback.answer("✅ Файл удалён", show_alert=True)
    await cq_file_list(callback, FileCallback(action="list", page=0))


@files_router.callback_query(FileCallback.filter(F.action == "link"))
async def cq_file_link(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    file_data = await get_file_by_id(callback_data.file_id)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start=file_{file_data['slug']}"
    await callback.answer(f"🔗 {link}", show_alert=True)


@files_router.callback_query(FileCallback.filter(F.action == "preview"))
async def cq_file_preview(callback: CallbackQuery, callback_data: FileCallback):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    file_data = await get_file_by_id(callback_data.file_id)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    await callback.answer("📤 Отправляю предпросмотр...")
    try:
        if file_data["file_type"] == "video":
            await callback.message.answer_video(file_data["file_id"])
        elif file_data["file_type"] == "audio":
            await callback.message.answer_audio(file_data["file_id"])
        elif file_data["file_type"] == "voice":
            await callback.message.answer_voice(file_data["file_id"])
        else:
            await callback.message.answer_document(file_data["file_id"])
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)