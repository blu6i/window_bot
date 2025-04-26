from aiogram import types, Dispatcher

from sql import get_connection, get_user_groups, get_user_dates

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


def get_free_time(cursor, group_names: list[str], date: str) -> dict[str, list[str]]:
    """Получить свободные пары по группам на указанную дату"""
    free_slots = {}

    for group in group_names:
        cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group,))
        result = cursor.fetchone()
        if not result:
            continue
        group_id = result[0]

        cursor.execute("""
            SELECT Time FROM Schedule
            WHERE GroupID = ? AND Date = ?
        """, (group_id, date))
        occupied_times = {row[0] for row in cursor.fetchall()}

        free_times = [t for t in PAIR_TIMES if t not in occupied_times]
        free_slots[group] = free_times

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
        conn.close()
        return

    results = []
    for date in dates:
        free_slots = get_free_time(cursor, groups, date)
        common_slots = get_set_free_time(free_slots)

        if not common_slots:
            results.append(f"📅 {date}: свободных окон нет")
        else:
            slots = ', '.join(sorted(common_slots))
            results.append(f"📅 {date}: {slots}")

    await message.answer("\n".join(results))
    conn.close()


def register_search_handlers(dp: Dispatcher):
    dp.register_message_handler(handle_schedule_request, text="🪟 Окна в расписании", state="*")
    dp.register_message_handler(handle_schedule_request, commands=["search_window"], state="*")
