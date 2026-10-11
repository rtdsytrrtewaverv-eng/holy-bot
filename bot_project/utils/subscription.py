# ==================== utils/subscription.py ====================
"""
Проверка подписки пользователя на каналы.
"""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from database import get_active_channels

logger = logging.getLogger(__name__)


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, list]:
    """
    Проверяет подписку на все активные обязательные каналы.
    Возвращает (все_подписаны, список_неподписанных_каналов).

    ВАЖНО: если канал недоступен для проверки (бот не админ,
    chat not found и т.п.) — считаем пользователя подписанным (fail-open),
    чтобы не блокировать выдачу файлов из-за ошибки конфигурации.
    """
    channels = await get_active_channels()
    channels = [ch for ch in channels if ch.get("is_required")]
    not_subscribed = []

    for ch in channels:
        chat_id = ch["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            status = member.status
            if status in ("member", "administrator", "creator"):
                continue
            if status == "restricted":
                if getattr(member, "is_member", False):
                    continue
            not_subscribed.append(ch)
        except TelegramBadRequest as e:
            # "member list is inaccessible" — бот не админ канала
            logger.warning(
                "Не удалось проверить подписку на %s: %s. "
                "Убедитесь, что бот добавлен в канал как администратор!",
                chat_id, e
            )
            continue  # fail-open: не блокируем выдачу
        except TelegramForbiddenError as e:
            logger.warning("Бот заблокирован/кикнут из %s: %s", chat_id, e)
            continue
        except Exception as e:
            logger.error("Ошибка проверки подписки на %s: %s", chat_id, e)
            continue

    return len(not_subscribed) == 0, not_subscribed


async def check_single_subscription(bot: Bot, channel_id: str, user_id: int) -> bool:
    """Проверка подписки на конкретный канал. Возвращает True при ошибке (fail-open)."""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        status = member.status
        if status in ("member", "administrator", "creator"):
            return True
        if status == "restricted" and getattr(member, "is_member", False):
            return True
        return False
    except TelegramBadRequest as e:
        logger.warning("Проверка канала %s недоступна: %s (бот не админ?)", channel_id, e)
        return True  # fail-open
    except Exception as e:
        logger.error("Ошибка проверки канала %s: %s", channel_id, e)
        return True


async def verify_bot_admin_rights(bot: Bot) -> list:
    """
    Проверяет, является ли бот администратором во всех активных каналах.
    Возвращает список проблемных каналов (dict).
    """
    problems = []
    channels = await get_active_channels()
    me = await bot.get_me()
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=me.id)
            if member.status not in ("administrator", "creator"):
                problems.append({"channel": ch, "reason": f"бот имеет статус «{member.status}», нужен администратор"})
        except TelegramBadRequest as e:
            problems.append({"channel": ch, "reason": str(e)})
        except Exception as e:
            problems.append({"channel": ch, "reason": str(e)})
    return problems