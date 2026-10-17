# ==================== states.py ====================
"""
FSM состояния для диалогов добавления/редактирования.
"""

from aiogram.fsm.state import State, StatesGroup


class AddFileStates(StatesGroup):
    slug = State()
    title = State()
    description = State()
    howto_url = State()
    file = State()
    image = State()


class EditFileStates(StatesGroup):
    waiting_value = State()
    waiting_file = State()
    waiting_image = State()


class BatchFileStates(StatesGroup):
    """Массовое добавление файлов: собираем файлы, потом задаём общие поля."""
    collecting = State()
    title = State()
    description = State()
    howto_url = State()
    image = State()


class AddChannelStates(StatesGroup):
    title = State()
    chat_id_or_username = State()
    invite_link = State()
    is_required = State()


class EditChannelStates(StatesGroup):
    waiting_value = State()


class EditTextStates(StatesGroup):
    waiting_value = State()


class BroadcastStates(StatesGroup):
    message_content = State()
    button_text = State()
    button_url = State()


class AddAdminStates(StatesGroup):
    user_id = State()


class EditMediaStates(StatesGroup):
    waiting_photo = State()


class UserSearchStates(StatesGroup):
    query = State()