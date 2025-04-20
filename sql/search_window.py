import sqlite3
from sql.get_info import get_groups

# Константа с расписанием пар
PAIR_TIMES = [
    "08:20-09:50",
    "10:00-11:30",
    "11:45-13:15",
    "14:00-15:30",
    "15:45-17:15",
    "17:20-18:50",
    "18:55-20:25"
]


def get_free_time(conn: sqlite3.Connection, group_names: list[str], date: str) -> dict[str, list[str]]:
    """
    Находит свободные пары у групп на указанную дату.

    Args:
        conn: соединение с SQLite
        group_names: список названий групп
        date: дата в формате 'YYYY-MM-DD'
    Returns:
        словарь {GroupName: [свободные интервалы]}
    """
    cursor = conn.cursor()
    free_slots = {}

    for group in group_names:
        # Получаем ID группы
        cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group,))
        result = cursor.fetchone()
        if not result:
            # Если группа не найдена — пропускаем (или можно записать None)
            continue
        group_id = result[0]

        # Получаем список занятых интервалов для группы на эту дату
        cursor.execute("""
            SELECT Time FROM Schedule
            WHERE GroupID = ? AND Date = ?
        """, (group_id, date))
        occupied_times = {row[0] for row in cursor.fetchall()}

        # Вычисляем свободные интервалы
        free_times = [t for t in PAIR_TIMES if t not in occupied_times]
        free_slots[group] = free_times

    return free_slots


def get_set_free_time(free_slots: dict) -> set:
    # Инициализируем пересечение с первым множеством
    group_names = list(free_slots.keys())
    common_slots = set(free_slots[group_names[0]])
    # Если указана только одна группа
    if len(group_names) == 1:
        print('++')
        return common_slots
    # Поочередно пересекаем с остальными
    for group in group_names[1:]:
        common_slots &= set(free_slots[group])
    return common_slots


def main():
    conn = sqlite3.connect("../window_bot.db")
    groups = get_groups(conn, 'ПОД')
    date = '2025-04-22'
    free_slots = get_free_time(conn, groups, date)
    set_free_slots = get_set_free_time(free_slots)
    print(f"Общие свободные пары у всех групп: {', '.join(sorted(set_free_slots))}")


if __name__ == '__main__':
    main()
