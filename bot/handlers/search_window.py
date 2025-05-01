from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_main_menu, get_inline_key_list
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


async def callback_search_window(call: types.CallbackQuery, state: FSMContext):
    """Обработка запроса на поиск свободных окон"""
    u_id = call.from_user.id
    data = await state.get_data()
    last_msg_id = data.get("last_msg")
    if last_msg_id is None:
        logger.warning('У пользователя обнулился кэш с последним сообщением')
        await call.answer()
        return
    conn = get_connection()
    cursor = conn.cursor()

    u_groups = get_user_groups(u_id)
    u_dates = get_user_dates(u_id)
    if not u_groups or not u_dates:
        await call.bot.edit_message_text("⚠️ Пожалуйста, добавьте хотя бы одну группу и дату перед поиском окон.",
                                         chat_id=call.message.chat.id,
                                         message_id=last_msg_id,
                                         reply_markup=get_inline_key_list(u_id, "date")
                                         )
        await call.answer()
        return

    results = []
    for date in u_dates:
        free_slots = get_free_time(cursor, u_groups, date)
        common_slots = get_set_free_time(free_slots)

        if not common_slots:
            results.append(f"📅 {date}: свободных окон нет")
        else:
            slots = '\n'.join(sorted(common_slots))
            results.append(f"📅 {date}: \n{slots}\n")
    try:
        await call.bot.edit_message_text("\n".join(results),
                                         chat_id=call.message.chat.id,
                                         message_id=last_msg_id,
                                         reply_markup=get_main_menu(u_id))
    except Exception as e:
        logger.error(f'Ошибка при выводе окон {e}')
    await call.answer()


def register_search_handlers(dp: Dispatcher):
    # Вывод окон
    dp.register_callback_query_handler(callback_search_window,
                                       lambda c: c.data == 'menu_windows',
                                       state="*")
    # Вывод окон через команду (!Переделать)
    dp.register_message_handler(callback_search_window, commands=["search_window"], state="*")
