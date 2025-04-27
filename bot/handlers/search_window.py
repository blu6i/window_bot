from aiogram import types, Dispatcher

from bot.keyboards import get_main_menu
from sql import get_connection, get_user_groups, get_user_dates, get_group_name

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

    for id_ in group_id:
        cursor.execute("""
            SELECT Time FROM Schedule
            WHERE GroupID = ? AND Date = ?
        """, (id_, date))
        occupied_times = {row[0] for row in cursor.fetchall()}

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


async def handle_schedule_request(message: types.Message):
    """Обработка запроса на поиск свободных окон"""
    user_id = message.from_user.id

    conn = get_connection()
    cursor = conn.cursor()

    groups = get_user_groups(user_id)
    dates = get_user_dates(user_id)

    if not groups or not dates:
        await message.answer("⚠️ Пожалуйста, добавьте хотя бы одну группу и дату перед поиском окон.")
        return

    results = []
    for date in dates:
        free_slots = get_free_time(cursor, groups, date)
        common_slots = get_set_free_time(free_slots)

        if not common_slots:
            results.append(f"📅 {date}: свободных окон нет")
        else:
            slots = '\n'.join(sorted(common_slots))
            results.append(f"📅 {date}: {slots}")

    await message.answer("\n".join(results), reply_markup=get_main_menu(user_id))


def register_search_handlers(dp: Dispatcher):
    dp.register_message_handler(handle_schedule_request, text="🪟 Окна в расписании", state="*")
    dp.register_message_handler(handle_schedule_request, commands=["search_window"], state="*")
