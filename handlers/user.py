# ==================== handlers/user.py ====================
"""
Пользовательские хендлеры: /start, deep-link, проверка подписки, выдача файла.
"""

import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from database import (
    add_or_update_user, get_file_by_slug, get_text, get_media,
    increment_file_downloads, increment_downloads,
    is_maintenance, is_subscribe_required, is_admin,
)
from callbacks import SubsCallback, DownloadCallback, NavCallback
from keyboards.user_kb import subscribe_keyboard, file_delivery_keyboard, start_keyboard
from utils.subscription import check_subscription
from utils.ui import normalize_slug_arg
from config import DEFAULT_HOWTO_URL

logger = logging.getLogger(__name__)

user_router = Router(name="user")


async def send_start_photo(bot: Bot, chat_id: int, text: str, reply_markup=None):
    """Отправляет стартовое сообщение с фото, если задано."""
    media = await get_media("start_photo")
    if media and media.get("file_id"):
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=media["file_id"],
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return True
        except Exception:
            pass
    await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
    return False


async def handle_file_deeplink(message: Message, bot: Bot, payload: str):
    """
    Общая логика выдачи файла по payload вида 'file_<slug>'.
    Используется и deep-link, и обычным /start при ручном разборе.
    """
    if await is_maintenance():
        tech_text = await get_text("tech_works")
        await send_start_photo(bot, message.chat.id, tech_text)
        return

    slug = normalize_slug_arg(payload[len("file_"):])
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.full_name

    await add_or_update_user(user_id, username, first_name)

    file_data = await get_file_by_slug(slug)
    if not file_data:
        logger.warning("Файл не найден по slug=%r (deep-link от %s)", slug, user_id)
        not_found_text = await get_text("file_not_found")
        await send_start_photo(bot, message.chat.id, not_found_text)
        return

    if await is_subscribe_required():
        subscribed, not_subscribed_channels = await check_subscription(bot, user_id)
        if not subscribed:
            await send_subscribe_screen(bot, message.chat.id, slug, not_subscribed_channels)
            return

    await deliver_file(bot, message.chat.id, file_data, user_id)


@user_router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, bot: Bot, command: CommandObject):
    """
    Deep-link обработчик: https://t.me/MyBot?start=file_<slug>
    Обрабатывает любой deep-link, но реагирует только на префикс file_.
    """
    args = command.args or ""
    logger.info("Deep-link от %s: args=%r", message.from_user.id, args)

    # Не наш deep-link — показываем обычный старт
    if not args.startswith("file_"):
        await cmd_start(message, bot)
        return

    await handle_file_deeplink(message, bot, args)


@user_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Обычный /start (без deep-link параметра)."""
    logger.info("Обычный /start от %s: text=%r", message.from_user.id, message.text)

    # Защита: если Telegram всё же передал payload (например без пробела),
    # пробуем обработать его как deep-link вручную
    raw = (message.text or "").strip()
    if " " in raw:
        payload = raw.split(" ", 1)[1].strip()
        if payload.startswith("file_"):
            logger.info("Ручной разбор deep-link из /start: %r", payload)
            await handle_file_deeplink(message, bot, payload)
            return

    if await is_maintenance():
        tech_text = await get_text("tech_works")
        await send_start_photo(bot, message.chat.id, tech_text)
        return

    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.full_name

    await add_or_update_user(user_id, username, first_name)

    start_text_tpl = await get_text("start_text")
    start_text = start_text_tpl.format(
        username=f"@{username}" if username else first_name
    )
    await send_start_photo(bot, message.chat.id, start_text, reply_markup=start_keyboard())

    if await is_admin(user_id):
        from keyboards.admin_kb import admin_main_menu
        await message.answer(
            "<b>👑 Админ-панель</b>\n\nВыберите раздел:",
            reply_markup=admin_main_menu(),
            parse_mode="HTML"
        )


async def send_subscribe_screen(bot: Bot, chat_id: int, slug: str, channels: list = None):
    """Отправляет экран подписки с фото (если задано) и кнопками подписки."""
    sub_text = await get_text("subscribe_text")
    kb = subscribe_keyboard(slug, channels)
    media = await get_media("subscribe_photo")
    if media and media.get("file_id"):
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=media["file_id"],
                caption=sub_text,
                reply_markup=kb,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass
    await bot.send_message(
        chat_id, sub_text,
        reply_markup=kb,
        parse_mode="HTML", disable_web_page_preview=True
    )


async def send_file_by_type(bot: Bot, chat_id: int, file_type: str, file_id: str):
    """
    Отправляет файл нужного типа БЕЗ подписи и кнопок.
    Так файл уходит надёжно — даже если текст/разметка сломаны.
    """
    ft = (file_type or "document").lower()
    if ft == "video":
        return await bot.send_video(chat_id=chat_id, video=file_id)
    if ft == "audio":
        return await bot.send_audio(chat_id=chat_id, audio=file_id)
    if ft == "voice":
        return await bot.send_voice(chat_id=chat_id, voice=file_id)
    if ft == "animation":
        return await bot.send_animation(chat_id=chat_id, animation=file_id)
    # по умолчанию — документ
    return await bot.send_document(chat_id=chat_id, document=file_id)


async def deliver_file(bot: Bot, chat_id: int, file_data: dict, user_id: int):
    """
    Выдаёт файл: сначала отправляет САМ ФАЙЛ, затем отдельным сообщением —
    описание с кнопками. Это надёжнее, чем caption, который может не пройти
    из-за длины/разметки и «утащить» за собой весь файл.
    """
    howto_url = file_data.get("howto_url") or DEFAULT_HOWTO_URL
    howto_text = await get_text("howto_button_text") or "📖 Как установить?"
    conf_text_tpl = await get_text("subscription_confirmed")
    conf_text = conf_text_tpl.format(
        title=file_data.get("title", file_data["slug"]),
        description=file_data.get("description", "")
    )

    # 1) Отправляем сам файл (без caption)
    file_sent = False
    try:
        await send_file_by_type(bot, chat_id, file_data["file_type"], file_data["file_id"])
        file_sent = True
        await increment_file_downloads(file_data["slug"])
        await increment_downloads(user_id)
    except Exception as e:
        logger.error(
            "Не удалось отправить файл slug=%r file_type=%r file_id=%r: %s",
            file_data.get("slug"), file_data.get("file_type"),
            str(file_data.get("file_id"))[:40], e
        )

    # 2) Отправляем описание с кнопками
    try:
        await bot.send_message(
            chat_id,
            conf_text,
            reply_markup=file_delivery_keyboard(file_data["slug"], howto_url, howto_text),
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error("Не удалось отправить описание файла: %s", e)
        # последняя попытка — без разметки
        try:
            plain = f"🎁 Ваш файл: {file_data.get('title', file_data['slug'])}"
            await bot.send_message(chat_id, plain,
                                   reply_markup=file_delivery_keyboard(file_data["slug"], howto_url, howto_text))
        except Exception as e2:
            logger.error("Не удалось отправить даже простое описание: %s", e2)

    # 3) Если файл не ушёл — честно сообщаем об ошибке
    if not file_sent:
        await bot.send_message(
            chat_id,
            "⚠️ <b>Файл не удалось отправить.</b>\n\n"
            "Администратору: обновите файл в админке "
            "(📁 Файлы → файл → 📎 Заменить файл), "
            "так как file_id мог устареть.",
            parse_mode="HTML"
        )


@user_router.callback_query(SubsCallback.filter(F.action == "check"))
async def cq_subscribe_check(callback: CallbackQuery, callback_data: SubsCallback, bot: Bot):
    """Проверка подписки после нажатия «✅ Я подписался»."""
    user_id = callback.from_user.id
    slug = callback_data.slug

    file_data = await get_file_by_slug(slug)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        not_found_text = await get_text("file_not_found")
        await bot.send_message(user_id, not_found_text, parse_mode="HTML")
        return

    subscribed, _ = await check_subscription(bot, user_id)
    if subscribed:
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await deliver_file(bot, user_id, file_data, user_id)
    else:
        await callback.answer("❌ Вы ещё не подписаны!", show_alert=True)


@user_router.callback_query(SubsCallback.filter(F.action == "help"))
async def cq_help(callback: CallbackQuery):
    """Кнопка «ℹ️ Помощь»."""
    help_text = await get_text("help_text")
    await callback.message.answer(help_text, parse_mode="HTML")
    await callback.answer()


@user_router.callback_query(SubsCallback.filter(F.action == "main_menu"))
async def cq_main_menu(callback: CallbackQuery, bot: Bot):
    """Кнопка «🏠 Главное меню» — возврат на стартовый экран."""
    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    start_text_tpl = await get_text("start_text")
    start_text = start_text_tpl.format(
        username=f"@{username}" if username else first_name
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_start_photo(bot, user_id, start_text, reply_markup=start_keyboard())
    await callback.answer()


@user_router.callback_query(DownloadCallback.filter())
async def cq_download_file(callback: CallbackQuery, callback_data: DownloadCallback, bot: Bot):
    """Кнопка «📥 Скачать файл» — отправляет файл."""
    slug = callback_data.slug
    user_id = callback.from_user.id
    file_data = await get_file_by_slug(slug)

    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    await callback.answer("📥 Отправляю...")

    try:
        if file_data["file_type"] == "document":
            await bot.send_document(chat_id=user_id, document=file_data["file_id"])
        elif file_data["file_type"] == "video":
            await bot.send_video(chat_id=user_id, video=file_data["file_id"])
        elif file_data["file_type"] == "audio":
            await bot.send_audio(chat_id=user_id, audio=file_data["file_id"])
        elif file_data["file_type"] == "voice":
            await bot.send_voice(chat_id=user_id, voice=file_data["file_id"])
        else:
            await bot.send_document(chat_id=user_id, document=file_data["file_id"])
    except Exception:
        await callback.answer("❌ Ошибка отправки", show_alert=True)
        return

    await increment_file_downloads(slug)
    await increment_downloads(user_id)


# ═══════════════════════════════════════════════════════════
# Команда /support
# ═══════════════════════════════════════════════════════════

@user_router.message(Command("support"))
async def cmd_support(message: Message):
    support_tpl = await get_text("support_text")
    support_username = await get_text("support_username")
    text = support_tpl.format(username=support_username)
    await message.answer(text, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
# Команда /help
# ═══════════════════════════════════════════════════════════

@user_router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = await get_text("help_text")
    await message.answer(help_text, parse_mode="HTML")