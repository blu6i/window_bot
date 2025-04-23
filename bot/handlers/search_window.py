import sqlite3

from aiogram import types, Dispatcher

from sql import get_user_values, get_connection, get_connection_gr

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

# Используем уже открытую БД


def get_free_time(conn: sqlite3.Connection, group_names: list[str], date: str) -> dict[str, list[str]]:
    cursor = conn.cursor()
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


def get_set_free_time(free_slots: dict) -> set:
    group_names = list(free_slots.keys())
    if not group_names:
        return set()
    common_slots = set(free_slots[group_names[0]])
    for group in group_names[1:]:
        common_slots &= set(free_slots[group])
    return common_slots


async def handle_schedule_request(message: types.Message):
    user_id = message.from_user.id
    groups = get_user_values(user_id, "group")
    dates = get_user_values(user_id, "date")
    conn = get_connection()
    conn2 = get_connection_gr()

    if not groups or not dates:
        await message.answer("⚠️ Пожалуйста, добавьте хотя бы одну группу и дату перед поиском окон.")
        return

    results = []
    for date in dates:
        free_slots = get_free_time(conn2, groups, date)
        common_slots = get_set_free_time(free_slots)

        if not common_slots:
            results.append(f"📅 {date}: свободных окон нет")
        else:
            slots = ', '.join(sorted(common_slots))
            results.append(f"📅 {date}: {slots}")

    await message.answer("\n".join(results))


def register_search_handlers(dp: Dispatcher):
    dp.register_message_handler(handle_schedule_request, text="🪟 Окна в расписании", state="*")
    dp.register_message_handler(handle_schedule_request, commands=["search_window"], state='*')
