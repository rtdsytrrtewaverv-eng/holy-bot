# ==================== config.py ====================
"""
Конфигурация бота. Все настройки загружаются из .env файла.
"""

import os
from dotenv import load_dotenv

# На Replit переменные берутся из Secrets (это переменные окружения).
# load_dotenv() нужен только для локального .env и не мешает Secrets.
load_dotenv()


def _to_int(value, default=0):
    """Безопасно превращает значение в int (пустая строка / мусор → default)."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
ADMIN_ID = _to_int(os.getenv("ADMIN_ID"), 0)
CHANNEL_ID = _to_int(os.getenv("CHANNEL_ID"), 0)

# Путь к БД можно переопределить переменной окружения (например, на
# постоянный диск Replit), иначе файл рядом со скриптом.
DB_PATH = os.getenv("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")

DEFAULT_HOWTO_URL = "https://t.me/holy_IPA/44"
DEFAULT_TEXTS = {
    "start_text": (
        "<b>👋 Привет, {username}!</b>\n\n"
        "Я бот канала <a href='https://t.me/holy_IPA'>Holy IPA</a>.\n"
        "Здесь ты можешь получить эксклюзивные файлы.\n\n"
        "📌 <i>Используй кнопки меню для навигации.</i>"
    ),
    "subscribe_text": (
        "<b>🔒 Доступ ограничен</b>\n\n"
        "Чтобы получить файл, подпишись на наш канал:\n"
        "<a href='https://t.me/holy_IPA'>@holy_IPA</a>\n\n"
        "После подписки нажми <b>«✅ Я подписался»</b>"
    ),
    "subscription_confirmed": (
        "<b>✅ Подписка подтверждена!</b>\n\n"
        "🎁 Ваш файл: <b>{title}</b>\n"
        "📝 {description}"
    ),
    "file_not_found": "<b>❌ Файл не найден.</b>\n\nВозможно, он был удалён или ссылка устарела.",
    "help_text": (
        "<b>ℹ️ Помощь</b>\n\n"
        "1. Перейди по ссылке из канала @holy_IPA\n"
        "2. Подпишись на канал\n"
        "3. Получи файл!\n\n"
        "По вопросам: /support"
    ),
    "support_username": "@holy_IPA_admin",
    "support_text": "<b>📞 Поддержка:</b> {username}",
    "howto_button_text": "📖 Как установить?",
    "tech_works": "<b>🚧 Бот временно на техобслуживании.</b>\n\nПопробуй позже.",
    "maintenance": "0",
}