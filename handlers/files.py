# ==================== handlers/files.py ====================
"""
Хендлеры управления файлами: добавление, список, редактирование, удаление, ссылка.
"""

import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest

from database import (
    is_admin, add_file, get_all_files, count_files, get_file_by_id,
    update_file_field, update_file, delete_file, get_text,
    generate_unique_slug,
)
from callbacks import FileCallback, NavCallback, ConfirmCallback
from states import AddFileStates, EditFileStates, BatchFileStates
from keyboards.files_kb import (
    files_menu, file_list_kb, file_detail_kb, file_edit_fields_kb,
    file_confirm_delete_kb, batch_collecting_kb,
)
from utils.ui import toast, breadcrumb, paginate, sanitize_slug
from utils.files import extract_file, send_file, file_display_name

logger = logging.getLogger(__name__)

files_router = Router(name="files")


def _file_detail_text(file_data: dict) -> str:
    in_lib = "✅ Да" if file_data.get("in_library") else "❌ Нет"
    has_img = "✅ Есть" if file_data.get("image_file_id") else "— Нет"
    return (
        f"<b>🏠 › 📁 Файлы › 📄 {file_data['title'] or file_data['slug']}</b>\n\n"
        f"📝 <b>Название:</b> {file_data['title'] or '—'}\n"
        f"📄 <b>Описание:</b> {file_data['description'] or '—'}\n"
        f"🔤 <b>Slug:</b> <code>{file_data['slug']}</code>\n"
        f"📎 <b>Тип:</b> {file_data['file_type']}\n"
        f"🔗 <b>Ссылка «Как уст.»:</b> {file_data['howto_url'] or '(по умолчанию)'}\n"
        f"🖼 <b>Обложка:</b> {has_img}\n"
        f"📚 <b>В библиотеке:</b> {in_lib}\n"
        f"📥 <b>Скачиваний:</b> {file_data['downloads']}\n"
    )


async def _show_file_detail(callback: CallbackQuery, file_id: int):
    file_data = await get_file_by_id(file_id)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            _file_detail_text(file_data),
            reply_markup=file_detail_kb(file_id, bool(file_data.get("in_library"))),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@files_router.message(Command("cancel"), StateFilter(AddFileStates))
@files_router.message(Command("cancel"), StateFilter(EditFileStates))
@files_router.message(Command("cancel"), StateFilter(BatchFileStates))
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
        "Поддерживается <b>любой файл с любым расширением</b>:\n"
        "документы (.zip, .ipa, .apk, .exe, .pdf и т.д.), видео, аудио, "
        "голосовые, GIF, фото, стикеры.\n\n"
        "Отправьте файл или нажмите /cancel для отмены.",
        reply_markup=None,
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.file)
async def add_file_step_file(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    file_type, file_id = extract_file(message)
    if not file_id:
        await message.answer(
            "❌ Не вижу вложения. Отправьте файл (документ, видео, аудио и т.п.)."
        )
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
    await state.update_data(howto_url=howto_url)
    await state.set_state(AddFileStates.image)
    await message.answer(
        "<b>🖼 Отправьте обложку-картинку (опционально)</b>\n\n"
        "Она будет показана перед файлом.\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.message(AddFileStates.image, F.photo)
async def add_file_step_image(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=file_id)
    await _finalize_add_file(message, state)


@files_router.message(AddFileStates.image)
async def add_file_step_image_skip(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "-":
        await state.update_data(image_file_id="")
    await _finalize_add_file(message, state)


async def _finalize_add_file(message: Message, state: FSMContext):
    data = await state.get_data()

    try:
        fid = await add_file(
            slug=data["slug"],
            file_type=data["file_type"],
            file_id=data["file_id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            howto_url=data.get("howto_url", ""),
        )
        if data.get("image_file_id"):
            await update_file(fid, image_file_id=data["image_file_id"])
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


# ═══════════════════════════════════════════════════════════
# МАССОВОЕ ДОБАВЛЕНИЕ ФАЙЛОВ
# ═══════════════════════════════════════════════════════════

@files_router.callback_query(FileCallback.filter(F.action == "add_many"))
async def cq_file_add_many(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(BatchFileStates.collecting)
    await state.update_data(batch=[])
    await callback.answer()
    await callback.message.edit_text(
        "<b>📦 Массовое добавление файлов</b>\n\n"
        "Отправьте <b>несколько файлов</b> подряд — по одному сообщению на файл.\n"
        "Поддерживается любой тип: документы, видео, аудио, голосовые, GIF, фото, стикеры.\n\n"
        "Когда закончите — нажмите <b>«Готово»</b>.\n"
        "Slug будет сгенерирован автоматически из имени файла.\n\n"
        "Используйте /cancel для отмены.",
        reply_markup=batch_collecting_kb(),
        parse_mode="HTML"
    )


@files_router.message(BatchFileStates.collecting)
async def batch_collect(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    file_type, file_id = extract_file(message)
    if not file_id:
        await message.answer(
            "❌ Не вижу вложения. Отправьте файл или нажмите «Готово», чтобы завершить."
        )
        return

    name = file_display_name(message)
    data = await state.get_data()
    batch = data.get("batch", [])
    batch.append({
        "file_type": file_type,
        "file_id": file_id,
        "name": name,
        "caption": (message.caption or "").strip(),
    })
    await state.update_data(batch=batch)
    await message.answer(
        f"✅ Добавлено в очередь: <b>{len(batch)}</b>\n"
        f"<i>{_html_escape(name)}</i>\n\n"
        "Отправьте ещё файл или нажмите «Готово».",
        parse_mode="HTML"
    )


@files_router.callback_query(BatchFileStates.collecting, FileCallback.filter(F.action == "batch_done"))
async def cq_batch_done(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    batch = data.get("batch", [])
    if not batch:
        await callback.answer("❌ Очередь пуста — отправьте хотя бы один файл", show_alert=True)
        return

    await callback.answer()
    await state.set_state(BatchFileStates.title)
    await callback.message.edit_text(
        f"<b>📝 Файлов в очереди: {len(batch)}</b>\n\n"
        "Введите <b>название</b> — оно будет у всех файлов.\n"
        "Если у файла было своё название (фото с подписью), оно сохранится отдельно.\n"
        "Отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.callback_query(BatchFileStates.collecting, FileCallback.filter(F.action == "batch_cancel"))
async def cq_batch_cancel(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.answer("🚫 Отменено")
    await callback.message.edit_text(
        "<b>🏠 › 📁 Управление файлами</b>\n",
        reply_markup=files_menu(),
        parse_mode="HTML"
    )


@files_router.message(BatchFileStates.title)
async def batch_step_title(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if title == "-":
        title = ""
    await state.update_data(batch_title=title)
    await state.set_state(BatchFileStates.description)
    await message.answer(
        "<b>📄 Введите описание для всех файлов</b>\n\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.message(BatchFileStates.description)
async def batch_step_description(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    description = message.text.strip()
    if description == "-":
        description = ""
    await state.update_data(batch_description=description)
    await state.set_state(BatchFileStates.howto_url)
    await message.answer(
        "<b>🔗 Введите ссылку для кнопки «Как установить?»</b>\n\n"
        "Или отправьте <code>-</code> чтобы использовать по умолчанию.",
        parse_mode="HTML"
    )


@files_router.message(BatchFileStates.howto_url)
async def batch_step_howto(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    howto_url = message.text.strip()
    if howto_url == "-":
        howto_url = ""
    await state.update_data(batch_howto_url=howto_url)
    await state.set_state(BatchFileStates.image)
    await message.answer(
        "<b>🖼 Отправьте общую обложку-картинку (опционально)</b>\n\n"
        "Она будет показана перед каждым файлом.\n"
        "Или отправьте <code>-</code> чтобы пропустить.",
        parse_mode="HTML"
    )


@files_router.message(BatchFileStates.image, F.photo)
async def batch_step_image(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.update_data(batch_image=message.photo[-1].file_id)
    await _finalize_batch(message, state)


@files_router.message(BatchFileStates.image)
async def batch_step_image_skip(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "-":
        await state.update_data(batch_image="")
    await _finalize_batch(message, state)


async def _finalize_batch(message: Message, state: FSMContext):
    data = await state.get_data()
    batch = data.get("batch", [])
    title = data.get("batch_title", "")
    description = data.get("batch_description", "")
    howto_url = data.get("batch_howto_url", "")
    image = data.get("batch_image", "")

    me = await message.bot.get_me()
    added = []
    errors = []

    for item in batch:
        try:
            base = item.get("caption") or item.get("name") or "file"
            slug = await generate_unique_slug(base)
            item_title = item.get("caption") or title
            fid = await add_file(
                slug=slug,
                file_type=item["file_type"],
                file_id=item["file_id"],
                title=item_title,
                description=description,
                howto_url=howto_url,
            )
            if image:
                await update_file(fid, image_file_id=image)
            link = f"https://t.me/{me.username}?start=file_{slug}"
            added.append((slug, link))
        except Exception as e:
            logger.error("Массовое добавление: ошибка для %r: %s", item.get("name"), e)
            errors.append(f"{item.get('name')}: {e}")

    await state.clear()

    lines = [f"<b>✅ Добавлено файлов: {len(added)}</b>\n"]
    for slug, link in added:
        lines.append(f"• <code>{slug}</code>\n  <code>{link}</code>")
    if errors:
        lines.append(f"\n<b>❌ Ошибок: {len(errors)}</b>")
        for err in errors[:10]:
            lines.append(f"• {_html_escape(err)}")

    text = "\n".join(lines)
    # Telegram ограничивает сообщение 4096 символами — делим при необходимости
    for chunk in _split_message(text, 3900):
        await message.answer(chunk, parse_mode="HTML")

    await message.answer(
        "<b>🏠 › 📁 Управление файлами</b>\n",
        reply_markup=files_menu(),
        parse_mode="HTML"
    )


def _html_escape(s: str) -> str:
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _split_message(text: str, size: int):
    """Делит длинный текст по строкам на части не больше size символов."""
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > size:
            if current:
                parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


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
    await _show_file_detail(callback, callback_data.file_id)


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
    elif field == "image_file_id":
        await state.set_state(EditFileStates.waiting_image)
        await state.update_data(file_id=file_id)
        await callback.message.edit_text(
            "<b>🖼 Отправьте новую обложку-картинку</b>\n\n"
            "Или отправьте <code>-</code> чтобы удалить обложку.\n"
            "Используйте /cancel для отмены.",
            parse_mode="HTML"
        )
        await callback.answer()
    elif field == "toggle_library":
        file_data = await get_file_by_id(file_id)
        if file_data:
            new_val = 0 if file_data.get("in_library") else 1
            await update_file_field(file_id, "in_library", new_val)
        await callback.answer("✅ Обновлено")
        await cq_file_edit(callback, callback_data)
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
        await message.answer(
            _file_detail_text(file_data),
            reply_markup=file_detail_kb(file_id, bool(file_data.get("in_library"))),
            parse_mode="HTML"
        )


@files_router.message(EditFileStates.waiting_file)
async def edit_file_file(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    file_id_db = data["file_id"]

    file_type, new_file_id = extract_file(message)
    if not new_file_id:
        await message.answer("❌ Не вижу вложения. Отправьте файл или /cancel.")
        return

    await update_file(file_id_db, file_id=new_file_id, file_type=file_type)
    await state.clear()
    await message.answer("✅ Файл обновлён.")

    file_data = await get_file_by_id(file_id_db)
    if file_data:
        await message.answer(
            _file_detail_text(file_data),
            reply_markup=file_detail_kb(file_id_db, bool(file_data.get("in_library"))),
            parse_mode="HTML"
        )


@files_router.message(EditFileStates.waiting_image, F.photo)
async def edit_file_image(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    file_id_db = data["file_id"]
    new_image = message.photo[-1].file_id

    await update_file(file_id_db, image_file_id=new_image)
    await state.clear()
    await message.answer("✅ Обложка обновлена.")

    file_data = await get_file_by_id(file_id_db)
    if file_data:
        await message.answer(
            _file_detail_text(file_data),
            reply_markup=file_detail_kb(file_id_db, bool(file_data.get("in_library"))),
            parse_mode="HTML"
        )


@files_router.message(EditFileStates.waiting_image)
async def edit_file_image_skip(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    file_id_db = data["file_id"]
    if message.text and message.text.strip() == "-":
        await update_file(file_id_db, image_file_id="")
        await state.clear()
        await message.answer("🗑 Обложка удалена.")
        file_data = await get_file_by_id(file_id_db)
        if file_data:
            await message.answer(
                _file_detail_text(file_data),
                reply_markup=file_detail_kb(file_id_db, bool(file_data.get("in_library"))),
                parse_mode="HTML"
            )
    else:
        await message.answer("❌ Отправьте фото или <code>-</code> чтобы удалить обложку, либо /cancel.", parse_mode="HTML")


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
        await send_file(
            callback.bot,
            callback.message.chat.id,
            file_data["file_type"],
            file_data["file_id"],
        )
    except Exception as e:
        logger.error("Ошибка предпросмотра файла: %s", e)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)