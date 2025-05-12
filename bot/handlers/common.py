from aiogram import types, Dispatcher, bot
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatType

import sql
from bot import get_main_menu
from sql import remove_schedule, remove_schedule_teacher
from utils import logger
from parser import groups_web_parse, parse_schedule_teacher
from bot.init_bot import get_bot

WELCOME_TEXT = ("Добро пожаловать в бота для поиска свободных окон в расписании групп!\n"
                "\n"
                "<b>🧭 Быстрый старт</b>\n"
                "\n"
                "Для поиска свободных окон нужно добавить <b>минимум одну группу И одну дату</b>.\n"
                "\n"
                "<b>👥 Добавление группы</b> — перейдите в <u>«Управление группами»</u> и введите:\n"
                "• <b>Название института (Сокращенное).</b> <i>Например:</i> <code>ИМИС</code>\n"
                "• <b>Название факультета (Сокращенное).</b> <i>Например:</i> <code>ФАВТ</code>\n"
                "• <b>Название направления (Сокращенное).</b> <i>Например:</i> <code>ИВТ</code>\n"
                "• <b>Группа:</b> <i>Например:</i> <code>ИВТб-1305-05-00</code>\n"
                "\n"
                "<b>📅 Добавление даты</b> — перейдите в <u>«Управление датами»</u> и введите:\n"
                "• <i>Например:</i> <code>21</code>, <code>21.04</code> или <code>21.04.2025</code>\n"
                "<i>Формат: DD, DD.\u200BMM или DD.MM.YYYY</i>\n"
                "\n"
                "Дополнительная информация — в разделе ℹ️ <b>Помощь</b>."
                )

LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'
LINK_TEACHER = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/teacher.html'


async def update_db(call: types.CallbackQuery):
    await call.message.answer('⏳ Запуск парсинга...')
    await call.answer()
    try:
        remove_schedule_teacher()
        parse_schedule_teacher(LINK_TEACHER)
        await call.message.answer(f'✅ Парсинг расписания преподавателей завершен')
    except Exception as e:
        await call.message.answer(f'⚠️ Ошибка при парсинге\n{e}')
    try:
        remove_schedule()
        groups_web_parse(LINK)
        await call.message.answer(f'✅ Парсинг расписания групп завершен')
    except Exception as e:
        await call.message.answer(f'⚠️ Ошибка при парсинге\n{e}')


async def remove_keyboard(bot, chat_id, msg_id):
    """Удаляет сообщение с кнопками"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        logger.error(f'Ошибка при удалении сообщение с кнопками {e}')


async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.finish()
    sent = await call.message.edit_text("🏠 Главное меню\n\nВыберите нужный раздел",
                                        reply_markup=get_main_menu(call.from_user.id))
    await state.update_data(last_msg=sent.message_id)
    await call.answer()


async def cmd_start(msg: types.Message, state: FSMContext):
    """Обработка команды /start"""
    data = await state.get_data()
    last_msg_id = data.get('last_msg')
    await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
    await msg.answer(WELCOME_TEXT,
                     reply_markup=ReplyKeyboardRemove(),
                     parse_mode='HTML')
    msg = await msg.answer('🏠 Главное меню\n\nВыберите нужный раздел',
                           reply_markup=get_main_menu(msg.from_user.id))
    await state.update_data(last_msg=msg.message_id)


async def notify_mp(group_ids: list, teacher_ids: list, message: str):
    # Списки для тех, у кого нет привязанного TG ID
    unnotified_groups = []
    unnotified_teachers = []
    _bot = get_bot()
    # Оповещение по группам (если у группы есть чат)
    for group_id in group_ids:
        # Получаем ChatID группы из базы данных
        chat_id = sql.get_group_chat_id(group_id)
        if chat_id:
            try:
                await _bot.send_message(chat_id, message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения в группу {group_id}: {e}")
        else:
            # Если нет chat_id, добавляем в список
            unnotified_groups.append(group_id)

    # Оповещение преподавателей (личные сообщения)
    for teacher_id in teacher_ids:
        # Получаем UserID преподавателя
        user_id = sql.get_teacher_chat_id(teacher_id)
        if user_id:
            try:
                await _bot.send_message(user_id, message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения преподавателю {teacher_id}: {e}")
        else:
            # Если нет user_id, добавляем в список
            unnotified_teachers.append(teacher_id)

    # Возвращаем списки, в которые не удалось отправить уведомление
    return unnotified_groups, unnotified_teachers


def register_common_handlers(dp: Dispatcher):
    # Возврат в главное меню
    dp.register_callback_query_handler(back_to_main,
                                       lambda c: c.data == "back_to_menu" and c.message.chat.type == ChatType.PRIVATE,
                                       state="*")
    # Обработка команды /start
    dp.register_message_handler(cmd_start,
                                commands=["start"],
                                chat_type=ChatType.PRIVATE,
                                state="*")
    # Запуск парсера
    dp.register_callback_query_handler(update_db,
                                       lambda c: c.data == "refresh_schedule" and c.message.chat.type == ChatType.PRIVATE,
                                       state='*')
