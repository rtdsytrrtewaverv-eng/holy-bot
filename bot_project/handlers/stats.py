# ==================== handlers/stats.py ====================
"""
Хендлер статистики.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import (
    is_admin, total_users, new_users_since, total_downloads, count_files,
)
from callbacks import NavCallback
from keyboards.common_kb import back_and_menu
from utils.ui import breadcrumb, toast

stats_router = Router(name="stats")


async def show_stats(callback: CallbackQuery):
    """Отображает статистику."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    u_total = await total_users()
    u_day = await new_users_since(1)
    u_week = await new_users_since(7)
    d_total = await total_downloads()
    f_total = await count_files()

    text = (
        f"{breadcrumb('🏠', '📊 Статистика')}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Пользователи</b>\n"
        f"   • Всего: <b>{u_total}</b>\n"
        f"   • За 24ч: <b>{u_day}</b>\n"
        f"   • За 7 дней: <b>{u_week}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📁 <b>Файлы:</b> {f_total}\n"
        f"📥 <b>Скачиваний всего:</b> {d_total}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )
    builder = back_and_menu("admin")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()