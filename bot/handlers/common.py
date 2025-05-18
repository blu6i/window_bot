from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ChatType, CallbackQuery, Message

import sql
from bot import get_main_menu
from bot.handlers.remove_test import update_new_msg
from bot.init_bot import get_bot
from parser import groups_web_parse, parse_schedule_teacher
from utils import logger

LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'
LINK_TEACHER = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/teacher.html'

PAIR_TIMES = [
    "08:20-09:50",
    "10:00-11:30",
    "11:45-13:15",
    "14:00-15:30",
    "15:45-17:15",
    "17:20-18:50",
    "18:55-20:25"
]


async def update_db(call: types.CallbackQuery):
    await call.message.answer('⏳ Запуск парсинга...')
    await call.answer()
    try:
        sql.remove_schedule_teacher()
        parse_schedule_teacher(LINK_TEACHER)
        await call.message.answer(f'✅ Парсинг расписания преподавателей завершен')
    except Exception as e:
        await call.message.answer(f'⚠️ Ошибка при парсинге преподавателей\n{e}')
    try:
        sql.remove_schedule()
        groups_web_parse(LINK)
        await call.message.answer(f'✅ Парсинг расписания групп завершен')
    except Exception as e:
        await call.message.answer(f'⚠️ Ошибка при парсинге групп\n{e}')


async def back_to_main(call: types.CallbackQuery, state: FSMContext, text: str = ""):
    """Вернуться в главное меню"""
    try:
        await state.finish()
        await out_main_menu(call, state, text)
    except Exception as e:
        logger.warning(f'Проблема при возврате в главное меню: {e}')
    finally:
        await call.answer()


async def out_main_menu(event: Union[types.Message, types.CallbackQuery],
                        state: FSMContext,
                        sub_text: str = '',
                        is_new_msg: bool = False):
    sent = None
    chat_id = None
    try:
        u_id = event.from_user.id
        if sql.is_teacher_authorized(u_id):
            teacher_name = f'{sql.get_teacher_name(sql.get_teacher_id_tg(u_id))}\n'
            text = ('🏠 *Главное меню*\n'
                    '\n'
                    'Вы авторизовались как:\n'
                    f'{teacher_name}'
                    f'Введите `!анкод` для выхода\n'
                    f'\n'
                    f'Выберите нужный раздел\n'
                    f'{sub_text}')
        else:
            text = ('🏠 *Главное меню*\n'
                    '\n'
                    'Выберите нужный раздел\n'
                    f'{sub_text}')

        if isinstance(event, types.CallbackQuery):
            chat_id = event.message.chat.id
            if is_new_msg:
                sent = await event.message.answer(f'{text}',
                                                  reply_markup=get_main_menu(u_id),
                                                  parse_mode='Markdown')
            else:
                try:
                    sent = await event.message.edit_text(f'{text}',
                                                         reply_markup=get_main_menu(u_id),
                                                         parse_mode='Markdown')
                except:
                    sent = await event.message.answer(f'{text}',
                                                      reply_markup=get_main_menu(u_id),
                                                      parse_mode='Markdown')
                finally:
                    await event.answer()
        else:
            chat_id = event.chat.id
            if is_new_msg:
                sent = await event.answer(f'{text}',
                                          reply_markup=get_main_menu(u_id),
                                          parse_mode='Markdown')
            else:
                try:
                    sent = await event.edit_text(f'{text}',
                                                 reply_markup=get_main_menu(u_id),
                                                 parse_mode='Markdown')
                except:
                    sent = await event.answer(f'{text}',
                                              reply_markup=get_main_menu(u_id),
                                              parse_mode='Markdown')
        return sent
    finally:
        await update_new_msg(chat_id, sent, state)


async def notify_mp(group_ids: list, teacher_ids: list, message: str):
    """Оповещение об встрече"""
    try:
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
                    logger.warning(f"Ошибка при отправке сообщения в группу {group_id}: {e}")
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
                    logger.warning(f"Ошибка при отправке сообщения преподавателю {teacher_id}: {e}")
            else:
                # Если нет user_id, добавляем в список
                unnotified_teachers.append(teacher_id)

        # Возвращаем списки, в которые не удалось отправить уведомление
        return unnotified_groups, unnotified_teachers
    except Exception as e:
        logger.warning(f'Проблема при оповещении об встрече: {e}')


def generate_free_windows_multi(group_ids: list, teacher_ids: list, dates: list) -> dict:
    """Выборка свободных окон"""
    try:
        occupied = sql.get_occupied_times_multi(group_ids, teacher_ids, dates)
        free_windows = {}
        for date, busy_times in occupied.items():
            free = [pair for pair in PAIR_TIMES if pair not in busy_times]
            free_windows[date] = free
        return free_windows
    except Exception as e:
        logger.warning(f'Проблема при выборке свободных окон: {e}')


async def send_result_text(event: Union[CallbackQuery, Message], text: str, reply_markup=None):
    """Вывод сообщений под разный стиль"""
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except:
            await event.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        await event.answer()
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=reply_markup, parse_mode="HTML")


def register_common_handlers(dp: Dispatcher):
    # Возврат в главное меню
    dp.register_callback_query_handler(
        back_to_main,
        lambda c: c.data == "back_to_menu" and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    # Запуск парсера
    dp.register_callback_query_handler(
        update_db,
        lambda c: c.data == "refresh_schedule" and c.message.chat.type == ChatType.PRIVATE,
        state='*'
    )
