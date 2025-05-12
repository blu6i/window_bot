from typing import Union

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType

from bot.keyboards import get_main_menu
from sql import get_connection, get_user_groups, get_user_dates, get_group_name
from utils import logger

# Предопределённые временные интервалы
PAIR_TIMES = [
    "08:20-09:50",
    "10:00-11:30",
    "11:45-13:15",
    "14:00-15:30",
    "15:45-17:15",
    "17:20-18:50",
    "18:55-20:25"
]


def get_free_time(cursor, group_id: list[int], date: str) -> dict[str, list[str]]:
    """Получить свободные пары по группам на указанную дату"""
    free_slots = {}
    # Обход всех групп
    for id_ in group_id:
        cursor.execute("""
            SELECT Time FROM Schedule
            WHERE GroupID = ? AND Date = ?
        """, (id_, date))
        occupied_times = {row[0] for row in cursor.fetchall()}
        # Формирование массива с временем, которого нет в БД
        free_times = [t for t in PAIR_TIMES if t not in occupied_times]
        group_name = get_group_name(id_)
        free_slots[group_name] = free_times

    return free_slots


def get_set_free_time(free_slots: dict[str, list[str]]) -> set[str]:
    """Пересечение свободных временных окон для всех групп"""
    if not free_slots:
        return set()

    group_names = list(free_slots.keys())
    common_slots = set(free_slots[group_names[0]])

    for group in group_names[1:]:
        common_slots &= set(free_slots[group])

    return common_slots


async def search_window_handler(event: Union[CallbackQuery, Message], state: FSMContext):
    """Обработка поиска свободных окон (по кнопке или команде)"""
    u_id = event.from_user.id

    u_groups = get_user_groups(u_id)
    u_dates = get_user_dates(u_id)
    text_menu = "🏠 Главное меню\n\nВыберите нужный раздел"
    if not u_groups or not u_dates:
        text = "⚠️ Пожалуйста, добавьте хотя бы одну группу и дату перед поиском окон."

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.message.answer(text_menu,
                                       reply_markup=get_main_menu(u_id))
        else:
            await event.answer(text)
            await event.answer(text_menu,
                               reply_markup=get_main_menu(u_id))
        return

    # Формируем текст окон
    conn = get_connection()
    cursor = conn.cursor()
    results = []

    for date in u_dates:
        free_slots = get_free_time(cursor, u_groups, date)
        common_slots = get_set_free_time(free_slots)

        if not common_slots:
            results.append(f"📅 {date}: свободных окон нет")
        else:
            slots = '\n'.join(sorted(common_slots))
            results.append(f"📅 {date}:\n{slots}\n")

    text_windows = "\n".join(results)

    if isinstance(event, CallbackQuery):
        await event.answer()
        try:
            # Сообщение с окнами
            await event.message.edit_text(text_windows)
            # Главное меню
            menu_msg = await event.message.answer(text_menu, reply_markup=get_main_menu(u_id))
            await state.update_data(last_msg=menu_msg.message_id)
        except Exception as e:
            logger.error(f"Ошибка при выводе окон: {e}")
    else:
        # Сообщение с окнами
        await event.answer(text_windows)

        # Главное меню
        menu_msg = await event.answer(text_menu, reply_markup=get_main_menu(u_id))
        await state.update_data(last_msg=menu_msg.message_id)


def register_search_handlers(dp: Dispatcher):
    # Вывод окон
    dp.register_callback_query_handler(
        search_window_handler,
        lambda c: c.data == "menu_windows" and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_message_handler(
        search_window_handler,
        chat_type=ChatType.PRIVATE,
        commands=["windows"],
        state="*"
    )
