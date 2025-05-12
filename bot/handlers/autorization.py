from aiogram import types, Dispatcher
from aiogram.types import ChatType

import sql


async def authorization_teacher(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return  # Нет пароля после !код
    password = parts[1].strip()
    u_id = message.from_user.id
    if sql.is_teacher_authorized(u_id):
        await message.answer(f'Вы уже авторизованы')
        return
    # Ищем пользователя в Users
    user_id = sql.get_user_id(u_id)
    if not user_id:
        return 
    # Проверяем Hash в Teachers
    teacher_id = sql.get_teacher_hash(password)
    if not teacher_id:
        return  # Хэш не найден
    # Обновляем поле UserID
    sql.update_teacher_userid(user_id, teacher_id)
    await message.answer("Вы успешно авторизованы! Обновите меню командой /start")


def register_authorization_handlers(dp: Dispatcher):
    dp.register_message_handler(authorization_teacher,
                                lambda c: c.text.startswith('!код') and c.message.chat.type == ChatType.PRIVATE,
                                state='*')
