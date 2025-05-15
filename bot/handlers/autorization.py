from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

import sql
from bot import get_main_menu
from utils import logger


async def authorization_teacher(msg: types.Message):
    try:
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            return  # Нет пароля после !код
        hash_code = parts[1].strip()
        u_id = msg.from_user.id
        if sql.is_teacher_authorized(u_id):
            await msg.answer(f'Вы уже авторизованы')
            return
        if sql.is_teacher_hash_authorized(hash_code):
            logger.warning(f'{u_id} Попытка использовать авторизованный ключ')
            return
        # Ищем пользователя в Users
        user_id = sql.get_user_id(u_id)
        if not user_id:
            return
            # Проверяем Hash в Teachers
        teacher_id = sql.get_teacher_hash(hash_code)
        if not teacher_id:
            return  # Хэш не найден
        # Обновляем поле UserID
        sql.update_teacher_userid(user_id, teacher_id)
        await msg.answer("Вы успешно авторизованы! Обновите меню командой /start")
    except Exception as e:
        logger.warning(f'Ошибка авторизации преподавателя: {e}')


async def unauthorization_teacher(msg: types.Message, state: FSMContext):
    try:
        u_id = msg.from_user.id
        if sql.is_teacher_authorized(u_id):
            await msg.answer('Вы вышли погулять')
            teacher_id = sql.get_teacher_id_tg(u_id)
            sql.unupdate_teacher_userid(teacher_id)
            sent = await msg.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                    reply_markup=get_main_menu(u_id))
            await state.update_data(last_msg=sent.message_id)
    except Exception as e:
        logger.warning(f'Ошибка анавторизации преподавателя: {e}')


async def authorization_group(message: types.Message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return  # Нет пароля после !код
        hash_code = parts[1].strip()
        chat_id = message.chat.id
        if sql.is_group_authorized(chat_id):
            await message.answer(f'Вы уже авторизованы')
            return
        if sql.is_group_hash_authorized(hash_code):
            logger.warning(f'{chat_id} Попытка использовать авторизованный ключ')
            return
        group_id = sql.get_group_hash(hash_code)
        if group_id:
            sql.add_chat_group(group_id, chat_id)
            await message.reply("✅ Чат успешно привязан к группе.")
        else:
            logger.warning(f'{chat_id} попытка авторизации')
    except Exception as e:
        logger.warning(f'Ошибка авторизации группы: {e}')


async def unauthorization_group(message: types.Message):
    try:
        group_id = message.chat.id
        if sql.is_group_authorized(group_id):
            await message.answer('Вы вышли погулять')
            sql.unadd_chat_group(group_id)
    except Exception as e:
        logger.warning(f'Ошибка анавторизации группы: {e}')


def register_authorization_handlers(dp: Dispatcher):
    dp.register_message_handler(
        authorization_teacher,
        lambda m: m.text.startswith('!код'),
        chat_type=types.ChatType.PRIVATE,
        state='*'
    )
    dp.register_message_handler(
        unauthorization_teacher,
        lambda m: m.text.startswith('!анкод'),
        chat_type=types.ChatType.PRIVATE,
        state='*'
    )

    dp.register_message_handler(
        authorization_group,
        lambda m: m.text.startswith("!код"),
        chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
        state="*"
    )
    dp.register_message_handler(
        unauthorization_group,
        lambda m: m.text.startswith("!анкод"),
        chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
        state="*"
    )
