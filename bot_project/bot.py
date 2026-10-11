# ==================== bot.py ====================
"""
Точка входа Telegram-бота «Файл за подписку» на aiogram 3.x.
Запуск: python bot.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest

from config import BOT_TOKEN, ADMIN_ID
from database import init_db

# Настройка вывода в UTF-8, чтобы русский текст и эмодзи не падали
# в консоли Windows (cp1251)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_handlers = [logging.StreamHandler(sys.stdout)]
try:
    _handlers.append(logging.FileHandler("bot.log", encoding="utf-8"))
except Exception:
    # На некоторых хостингах файловая система read-only — пишем только в stdout
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())

# Регистрация хендлеров
from handlers.user import user_router
from handlers.admin_menu import admin_menu_router
from handlers.files import files_router
from handlers.texts import texts_router
from handlers.channels import channels_router
from handlers.stats import stats_router
from handlers.broadcast import broadcast_router
from handlers.users import users_router
from handlers.settings import settings_router
from handlers.backup import backup_router

dp.include_router(user_router)
dp.include_router(admin_menu_router)
dp.include_router(files_router)
dp.include_router(texts_router)
dp.include_router(channels_router)
dp.include_router(stats_router)
dp.include_router(broadcast_router)
dp.include_router(users_router)
dp.include_router(settings_router)
dp.include_router(backup_router)


# ═══════════════════════════════════════════════════════════
# Глобальный обработчик ошибок — чтобы бот не «молчал»
# ═══════════════════════════════════════════════════════════

@dp.errors()
async def global_error_handler(event: ErrorEvent):
    logger.exception("Необработанная ошибка: %s", event.exception)

    update = event.update
    try:
        if update.message:
            await update.message.answer(
                "❌ Произошла ошибка. Попробуйте ещё раз или напишите в поддержку."
            )
        elif update.callback_query:
            await update.callback_query.answer("❌ Ошибка. Попробуйте ещё раз.", show_alert=True)
    except TelegramBadRequest:
        pass
    except Exception as e:
        logger.error("Не удалось сообщить об ошибке пользователю: %s", e)
    return True


async def check_channels_on_startup():
    """Проверяет, что бот — админ во всех активных каналах, и предупреждает админа."""
    from utils.subscription import verify_bot_admin_rights
    try:
        problems = await verify_bot_admin_rights(bot)
    except Exception as e:
        logger.error("Не удалось проверить права бота в каналах: %s", e)
        return

    if not problems:
        logger.info("✅ Права бота во всех каналах в порядке.")
        return

    logger.warning("⚠️ Проблемы с правами бота в %d канал(ах):", len(problems))
    lines = ["<b>⚠️ Внимание! Проверка подписки не работает</b>\n"]
    for p in problems:
        ch = p["channel"]
        name = ch.get("title") or ch.get("username") or ch.get("chat_id")
        logger.warning("  • %s: %s", name, p["reason"])
        lines.append(f"• <b>{name}</b> — {p['reason']}")
    lines.append(
        "\n<b>Решение:</b> добавьте бота в канал и выдайте права "
        "<b>администратора</b> (достаточно «Добавлять участников» / «Блокировать участников»)."
    )
    try:
        await bot.send_message(ADMIN_ID, "\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Не удалось отправить предупреждение админу: %s", e)


async def start_keepalive_server():
    """
    Простой HTTP-сервер для Replit:
    - отвечает 200 OK на любой запрос (health-check для UptimeRobot),
    - не даёт Repl «заснуть» при периодических пингах.
    Порт берётся из PORT (Replit задаёт его автоматически) или 8080.
    """
    import os
    from aiohttp import web

    port = _to_int_port(os.getenv("PORT"), 8080)

    async def health(request):
        return web.Response(text="OK — bot is running")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Keep-alive сервер запущен на порту %s", port)


def _to_int_port(value, default=8080):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


async def main():
    """Инициализация БД и запуск поллинга."""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("Бот запущен!")

    # Запускаем keep-alive веб-сервер (для Replit/UptimeRobot)
    try:
        await start_keepalive_server()
    except Exception as e:
        logger.warning("Не удалось запустить keep-alive сервер: %s", e)

    asyncio.create_task(check_channels_on_startup())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except SystemExit:
        pass