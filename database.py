# ==================== database.py ====================
"""
База данных SQLite (aiosqlite). Все CRUD-операции.
"""

import aiosqlite
import os
import logging
from datetime import datetime, timedelta
from config import DB_PATH, DEFAULT_TEXTS, DEFAULT_HOWTO_URL, ADMIN_ID, CHANNEL_ID

logger = logging.getLogger(__name__)


async def get_db() -> aiosqlite.Connection:
    """Подключение к БД с включёнными внешними ключами."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db():
    """Создаёт таблицы и заполняет значениями по умолчанию."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TEXT DEFAULT (datetime('now')),
                is_banned   INTEGER DEFAULT 0,
                is_admin    INTEGER DEFAULT 0,
                files_downloaded INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT UNIQUE NOT NULL,
                file_type   TEXT NOT NULL,
                file_id     TEXT NOT NULL,
                title       TEXT DEFAULT '',
                description TEXT DEFAULT '',
                howto_url   TEXT DEFAULT '',
                downloads   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS channels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT DEFAULT '',
                chat_id     TEXT NOT NULL,
                username    TEXT DEFAULT '',
                invite_link TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1,
                is_required INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS texts (
                key   TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS medias (
                key     TEXT PRIMARY KEY,
                file_id TEXT DEFAULT '',
                type    TEXT DEFAULT 'photo'
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    INTEGER,
                message_type TEXT DEFAULT 'text',
                message_content TEXT DEFAULT '',
                sent        INTEGER DEFAULT 0,
                failed      INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS file_items (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id      INTEGER NOT NULL,
                item_type    TEXT NOT NULL,
                item_file_id TEXT NOT NULL,
                title        TEXT DEFAULT '',
                sort_order   INTEGER DEFAULT 0,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            );
        """)
        await db.commit()

        await db.execute(
            "INSERT OR IGNORE INTO users(user_id, is_admin) VALUES (?, 1)",
            (ADMIN_ID,)
        )

        defaults = {
            "subscribe_required": "1",
            "maintenance_mode": "0",
        }
        for k, v in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v)
            )

        text_defaults = {
            "start_text": DEFAULT_TEXTS["start_text"],
            "subscribe_text": DEFAULT_TEXTS["subscribe_text"],
            "subscription_confirmed": DEFAULT_TEXTS["subscription_confirmed"],
            "file_not_found": DEFAULT_TEXTS["file_not_found"],
            "help_text": DEFAULT_TEXTS["help_text"],
            "support_username": DEFAULT_TEXTS["support_username"],
            "support_text": DEFAULT_TEXTS["support_text"],
            "howto_button_text": DEFAULT_TEXTS["howto_button_text"],
            "tech_works": DEFAULT_TEXTS["tech_works"],
            "library_title": "Библиотека приложений",
            "library_text": (
                "<b>Библиотека приложений</b>\n\n"
                "Выберите приложение из списка ниже.\n"
                "<i>Доступ только для подписчиков канала.</i>"
            ),
            "library_button_text": "Библиотека",
        }
        for k, v in text_defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO texts(key, value) VALUES (?, ?)", (k, v)
            )

        await db.execute(
            "INSERT OR IGNORE INTO medias(key, file_id, type) VALUES (?, '', 'photo')",
            ("start_photo",)
        )
        await db.execute(
            "INSERT OR IGNORE INTO medias(key, file_id, type) VALUES (?, '', 'photo')",
            ("subscribe_photo",)
        )

        # Автодобавление канала из .env при первом запуске
        if CHANNEL_ID:
            cur = await db.execute("SELECT COUNT(*) as cnt FROM channels")
            row = await cur.fetchone()
            if row and row["cnt"] == 0:
                await db.execute(
                    "INSERT INTO channels(title, chat_id, username, invite_link, is_active, is_required) "
                    "VALUES (?, ?, ?, ?, 1, 1)",
                    ("@holy_IPA", str(CHANNEL_ID), "@holy_IPA", "https://t.me/holy_IPA")
                )

        await db.commit()

        # Миграция: приводим slug к формату, допустимому в deep-link
        # (Telegram не поддерживает точки и спецсимволы в ?start=)
        import re as _re
        cur = await db.execute("SELECT id, slug FROM files")
        for row in await cur.fetchall():
            old = row["slug"]
            new = _re.sub(r"[^a-z0-9_\-]+", "_", old.strip().lower())
            new = _re.sub(r"_+", "_", new).strip("_")
            if new and new != old:
                try:
                    await db.execute("UPDATE files SET slug = ? WHERE id = ?", (new, row["id"]))
                    logger.info("Миграция slug: %r -> %r", old, new)
                except Exception:
                    pass
        await db.commit()

        # Миграции: добавляем новые колонки, если их нет
        await _add_column_if_missing(db, "files", "image_file_id", "TEXT DEFAULT ''")
        await _add_column_if_missing(db, "files", "emoji", "TEXT DEFAULT ''")
        await _add_column_if_missing(db, "files", "in_library", "INTEGER DEFAULT 1")
        await _add_column_if_missing(db, "files", "sort_order", "INTEGER DEFAULT 0")

        # Настройки оформления по умолчанию
        style_defaults = {
            "button_style_main": "primary",       # цвет кнопок меню/библиотеки
            "button_style_file": "primary",        # цвет кнопок на экране файла
            "button_style_howto": "success",       # цвет кнопки «Как установить?»
            "button_style_library": "primary",     # цвет кнопок библиотеки
            "button_style_back": "primary",        # цвет кнопки «Главное меню»
            "library_enabled": "1",
        }
        for k, v in style_defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v)
            )
        await db.commit()
    finally:
        await db.close()


async def _add_column_if_missing(db, table: str, column: str, ddl: str):
    """Добавляет колонку в таблицу, если её ещё нет (безопасная миграция)."""
    try:
        cur = await db.execute(f"PRAGMA table_info({table})")
        cols = [r["name"] for r in await cur.fetchall()]
        if column not in cols:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            await db.commit()
            logger.info("Миграция: добавлена колонка %s.%s", table, column)
    except Exception as e:
        logger.warning("Не удалось добавить колонку %s.%s: %s", table, column, e)


# ═══════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════

async def get_user(user_id: int):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def add_or_update_user(user_id: int, username: str = None, first_name: str = None):
    db = await get_db()
    try:
        existing = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if await existing.fetchone():
            await db.execute(
                "UPDATE users SET username = COALESCE(?, username), first_name = COALESCE(?, first_name) WHERE user_id = ?",
                (username, first_name, user_id)
            )
        else:
            await db.execute(
                "INSERT INTO users(user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
        await db.commit()
    finally:
        await db.close()


async def get_all_users(only_active: bool = False, only_subscribed: bool = False):
    db = await get_db()
    try:
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        if only_active:
            query += " AND is_banned = 0"
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def set_banned(user_id: int, banned: bool):
    db = await get_db()
    try:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
        await db.commit()
    finally:
        await db.close()


async def set_admin(user_id: int, is_admin: bool):
    db = await get_db()
    try:
        await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (int(is_admin), user_id))
        await db.commit()
    finally:
        await db.close()


async def is_admin(user_id: int) -> bool:
    db = await get_db()
    try:
        cur = await db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row["is_admin"])
    finally:
        await db.close()


async def increment_downloads(user_id: int):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET files_downloaded = files_downloaded + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    finally:
        await db.close()


async def total_users() -> int:
    db = await get_db()
    try:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM users")
        row = await cur.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


async def new_users_since(days: int) -> int:
    db = await get_db()
    try:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cur = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE joined_at >= ?", (since,))
        row = await cur.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# ФАЙЛЫ
# ═══════════════════════════════════════════════════════════

async def add_file(slug: str, file_type: str, file_id: str, title: str = "",
                   description: str = "", howto_url: str = "") -> int:
    db = await get_db()
    try:
        cur = await db.execute(
            "INSERT INTO files(slug, file_type, file_id, title, description, howto_url) VALUES (?, ?, ?, ?, ?, ?)",
            (slug, file_type, file_id, title, description, howto_url)
        )
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()


async def slug_exists(slug: str) -> bool:
    """Проверяет, занят ли slug."""
    db = await get_db()
    try:
        cur = await db.execute("SELECT 1 FROM files WHERE slug = ?", (slug,))
        return await cur.fetchone() is not None
    finally:
        await db.close()


async def generate_unique_slug(base: str) -> str:
    """
    Возвращает свободный slug на основе base: если base занят, добавляет -2, -3, ...
    """
    import re as _re
    base = (base or "").strip().lower()
    base = _re.sub(r"[^a-z0-9_\-]+", "_", base)
    base = _re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "file"
    if not await slug_exists(base):
        return base
    i = 2
    while await slug_exists(f"{base}-{i}"):
        i += 1
    return f"{base}-{i}"


async def get_file_by_slug(slug: str):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM files WHERE slug = ?", (slug,))
        row = await cur.fetchone()
        if row:
            return dict(row)

        # Устойчивый поиск: сравниваем нормализованные slug (без регистра/спецсимволов)
        import re as _re

        def _norm(s: str) -> str:
            s = _re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())
            return s

        target = _norm(slug)
        if not target:
            return None
        cur = await db.execute("SELECT * FROM files")
        rows = await cur.fetchall()

        # 1) Точное совпадение нормализованных slug
        for r in rows:
            if _norm(r["slug"]) == target:
                return dict(r)

        # 2) Совпадение по префиксу (Telegram мог обрезать slug на недопустимом
        #    символе, например точке). Если подходит ровно один файл — берём его.
        prefix_matches = [r for r in rows if _norm(r["slug"]).startswith(target)]
        if len(prefix_matches) == 1:
            return dict(prefix_matches[0])

        return None
    finally:
        await db.close()


async def get_file_by_id(file_id: int):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_all_files(limit: int = 10, offset: int = 0):
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def count_files() -> int:
    db = await get_db()
    try:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM files")
        row = await cur.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


async def get_library_files():
    """Файлы, отображаемые в библиотеке приложений (in_library = 1)."""
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT * FROM files WHERE in_library = 1 "
            "ORDER BY sort_order ASC, id DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def update_file_field(file_id: int, field: str, value):
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE files SET {field} = ? WHERE id = ?", (value, file_id)
        )
        await db.commit()
    finally:
        await db.close()


async def update_file(file_id: int, **kwargs):
    """Обновление полей файла."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [file_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE files SET {set_clause} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()


async def delete_file(file_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM file_items WHERE file_id = ?", (file_id,))
        await db.execute("DELETE FROM files WHERE id = ?", (file_id,))
        await db.commit()
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# СОСТАВНЫЕ ФАЙЛЫ (несколько файлов в одной записи/кнопке)
# ═══════════════════════════════════════════════════════════

async def add_file_item(entry_id: int, item_type: str, item_file_id: str, title: str = "") -> int:
    db = await get_db()
    try:
        cur = await db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM file_items WHERE file_id = ?", (entry_id,))
        row = await cur.fetchone()
        order = row["n"] if row else 1
        cur = await db.execute(
            "INSERT INTO file_items(file_id, item_type, item_file_id, title, sort_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry_id, item_type, item_file_id, title, order)
        )
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()


async def get_file_items(entry_id: int):
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT * FROM file_items WHERE file_id = ? ORDER BY sort_order ASC, id ASC",
            (entry_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def count_file_items(entry_id: int) -> int:
    db = await get_db()
    try:
        cur = await db.execute("SELECT COUNT(*) AS n FROM file_items WHERE file_id = ?", (entry_id,))
        row = await cur.fetchone()
        return row["n"] if row else 0
    finally:
        await db.close()


async def delete_file_item(item_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM file_items WHERE id = ?", (item_id,))
        await db.commit()
    finally:
        await db.close()


async def get_file_item(item_id: int):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM file_items WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def increment_file_downloads(slug: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE files SET downloads = downloads + 1 WHERE slug = ?", (slug,)
        )
        await db.commit()
    finally:
        await db.close()


async def total_downloads() -> int:
    db = await get_db()
    try:
        cur = await db.execute("SELECT COALESCE(SUM(downloads), 0) as cnt FROM files")
        row = await cur.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# КАНАЛЫ
# ═══════════════════════════════════════════════════════════

async def add_channel(title: str, chat_id: str, username: str = "",
                      invite_link: str = "", is_required: int = 1):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO channels(title, chat_id, username, invite_link, is_required) VALUES (?, ?, ?, ?, ?)",
            (title, chat_id, username, invite_link, is_required)
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_channels():
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM channels ORDER BY id ASC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_active_channels():
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM channels WHERE is_active = 1")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_channel(channel_id: int):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_channel(channel_id: int, **kwargs):
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [channel_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE channels SET {set_clause} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()


async def delete_channel(channel_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# ТЕКСТЫ
# ═══════════════════════════════════════════════════════════

async def get_text(key: str) -> str:
    db = await get_db()
    try:
        cur = await db.execute("SELECT value FROM texts WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else DEFAULT_TEXTS.get(key, "")
    finally:
        await db.close()


async def set_text(key: str, value: str):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO texts(key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_texts():
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM texts ORDER BY key ASC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# МЕДИА
# ═══════════════════════════════════════════════════════════

async def get_media(key: str):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM medias WHERE key = ?", (key,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def set_media(key: str, file_id: str, file_type: str = "photo"):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO medias(key, file_id, type) VALUES (?, ?, ?)",
            (key, file_id, file_type)
        )
        await db.commit()
    finally:
        await db.close()


async def delete_media(key: str):
    db = await get_db()
    try:
        await db.execute("UPDATE medias SET file_id = '' WHERE key = ?", (key,))
        await db.commit()
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════

async def get_setting(key: str) -> str:
    db = await get_db()
    try:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else "0"
    finally:
        await db.close()


async def set_setting(key: str, value: str):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()
    finally:
        await db.close()


async def is_maintenance() -> bool:
    return await get_setting("maintenance_mode") == "1"


async def is_subscribe_required() -> bool:
    return await get_setting("subscribe_required") == "1"


# ═══════════════════════════════════════════════════════════
# ОФОРМЛЕНИЕ (стили кнопок)
# ═══════════════════════════════════════════════════════════

VALID_STYLES = ("primary", "success", "danger", "")


def _validate_style(value) -> str:
    """Приводит значение к допустимому стилю кнопки (или пустой строке)."""
    v = str(value or "").strip().lower()
    if v == "none":
        v = ""
    return v if v in VALID_STYLES else ""


async def get_button_style(key: str) -> str:
    """Возвращает стиль кнопки (primary/success/danger или None). None = стиль по умолчанию."""
    v = _validate_style(await get_setting(key))
    return v or None


async def set_button_style(key: str, value: str):
    await set_setting(key, _validate_style(value))


async def is_library_enabled() -> bool:
    return await get_setting("library_enabled") != "0"


# ═══════════════════════════════════════════════════════════
# РАССЫЛКИ
# ═══════════════════════════════════════════════════════════

async def create_broadcast(admin_id: int, message_type: str, message_content: str) -> int:
    db = await get_db()
    try:
        cur = await db.execute(
            "INSERT INTO broadcasts(admin_id, message_type, message_content) VALUES (?, ?, ?)",
            (admin_id, message_type, message_content)
        )
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()


async def update_broadcast(broadcast_id: int, **kwargs):
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [broadcast_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE broadcasts SET {set_clause} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════
# БЭКАП (экспорт/импорт всей БД)
# ═══════════════════════════════════════════════════════════

async def get_db_dump() -> bytes:
    """
    Безопасный снимок всей БД со всеми данными (файлы, приложения, каналы,
    тексты, настройки, пользователи). Использует SQLite online-backup,
    поэтому копия всегда консистентна, даже если бот сейчас работает.
    """
    import tempfile
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = await aiosqlite.connect(DB_PATH)
        try:
            dst = await aiosqlite.connect(tmp_path)
            try:
                await src.backup(dst)
                await dst.commit()
            finally:
                await dst.close()
        finally:
            await src.close()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _is_sqlite(data: bytes) -> bool:
    """Проверяет, что данные — файл SQLite (сигнатура 'SQLite format 3')."""
    return data[:16] == b"SQLite format 3\x00"


async def restore_db(data: bytes):
    """
    Восстанавливает БД из полученных данных.
    Сначала проверяет, что это настоящий файл SQLite, затем перезаписывает.
    """
    if not data or not _is_sqlite(data):
        raise ValueError("Файл не является базой данных SQLite (bot_data.db).")

    # Атомарная замена: пишем во временный файл и подменяем
    tmp_path = DB_PATH + ".restore.tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)

    # Проверяем, что временный файл действительно открывается как SQLite
    try:
        check = await aiosqlite.connect(tmp_path)
        try:
            await check.execute("SELECT name FROM sqlite_master LIMIT 1")
        finally:
            await check.close()
    except Exception as e:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise ValueError(f"Повреждённый файл базы данных: {e}")

    os.replace(tmp_path, DB_PATH)

    # Применяем миграции к восстановленной БД (на случай старой версии схемы)
    await init_db()


async def backup_stats() -> dict:
    """Краткая сводка того, что попадёт в бэкап."""
    db = await get_db()
    try:
        async def _count(sql):
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return row[0] if row else 0

        return {
            "files": await _count("SELECT COUNT(*) FROM files"),
            "library": await _count("SELECT COUNT(*) FROM files WHERE in_library = 1"),
            "channels": await _count("SELECT COUNT(*) FROM channels"),
            "users": await _count("SELECT COUNT(*) FROM users"),
        }
    finally:
        await db.close()