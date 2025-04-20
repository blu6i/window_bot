import sqlite3
import re
from datetime import datetime

PATTERN_GROUP = r"^[а-яА-ЯёЁ]+-\d{4}-\d{2}-\d{2}$"


def is_schedule_on_date(conn, date_str: str) -> bool:
    """
    Проверяет, существует ли расписание хотя бы для одной группы на указанную дату.
    Принимает дату в формате 'DD.MM.YYYY' и преобразует её к 'YYYY-MM-DD'.
    Args:
        conn: соединение с базой данных SQLite
        date_str: дата в формате 'DD.MM.YYYY'
    Returns:
        True если расписание есть, иначе False
    """
    try:
        # Преобразуем в формат YYYY-MM-DD
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        # Если дата некорректна
        return False
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Schedule WHERE Date = ? LIMIT 1", (parsed_date,))
    return cursor.fetchone() is not None


def is_check_entity(conn, search_str: str) -> bool:
    """
    Проверяет, существует ли группа/факультет/институт/направление в бд
    Args:
        conn: соединение с базой данных SQLite
        search_str: строка с данными
    Returns:
        True если данные есть, иначе False
    """
    cursor = conn.cursor()
    # Проверка формата группы
    if re.match(PATTERN_GROUP, search_str):
        cursor.execute("SELECT 1 FROM Groups WHERE GroupName = ?", (search_str,))
        return cursor.fetchone() is not None

    # Проверка по факультетам
    cursor.execute("""
        SELECT 1 FROM Faculties 
        WHERE FacultyName = ? OR ShortName = ?
    """, (search_str, search_str))
    if cursor.fetchone():
        return True

    # Проверка по институтам
    cursor.execute("""
        SELECT 1 FROM Institutes 
        WHERE FullName = ? OR ShortName = ?
    """, (search_str, search_str))
    if cursor.fetchone():
        return True

    # Проверка по специальностям
    cursor.execute("""
        SELECT 1 FROM Specializations 
        WHERE SpecializationName = ? OR ShortName = ?
    """, (search_str, search_str))
    if cursor.fetchone():
        return True

    return False


def main():
    for i in range(3):
        conn = sqlite3.connect("../window_bot.db")
        search = input()
        # result = is_check_entity(conn, search)
        result = is_schedule_on_date(conn, search)
        print(result)  # True или False


if __name__ == '__main__':
    main()
