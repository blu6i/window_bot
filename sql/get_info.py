import sqlite3

import re
from datetime import datetime

from sql.init_connection import get_connection

PATTERN_GROUP = r"^[а-яА-ЯёЁ]+-\d{4}-\d{2}-\d{2}$"


# Проверка, что дата есть в БД
def is_schedule_on_date(date_str: str) -> bool:
    """
    Проверяет, существует ли расписание хотя бы для одной группы на указанную дату.
    Принимает дату в формате 'DD.MM.YYYY' и преобразует её к 'YYYY-MM-DD'.
    Args:
        date_str: дата в формате 'DD.MM.YYYY'
    Returns:
        True если расписание есть, иначе False
    """
    conn = get_connection()
    try:
        # Преобразуем в формат YYYY-MM-DD
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        # Если дата некорректна
        return False
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Schedule WHERE Date = ? LIMIT 1", (parsed_date,))
    return cursor.fetchone() is not None


# Проверка, что элемент есть в БД
def is_check_entity(search_str: str) -> bool:
    """
    Проверяет, существует ли группа/факультет/институт/направление в бд
    !!! Старая версия. В новой теперь проверяем возвращает ли поиск что-то, если возвращает, то это есть
    в базе данных, а следовательно существует
    Args:
        search_str: строка с данными
    Returns:
        True если данные есть, иначе False
    """
    conn = get_connection()
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


# Получение групп из таблицы с расписанием
def get_groups(name: str) -> list[str]:
    """
    Возвращает список названий групп, которые относятся к переданному названию
    факультета, института или специальности.

    Args:
        name: строка (название факультета / института / специальности)
    Returns:
        список названий групп
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT G.GroupName
    FROM Groups G
    JOIN Specializations S ON G.SpecializationID = S.SpecializationID
    JOIN Faculties F ON S.FacultyID = F.FacultyID
    JOIN Institutes I ON F.InstituteID = I.InstituteID
    WHERE S.SpecializationName = ?
       OR S.ShortName = ?
       OR F.FacultyName = ?
       OR F.ShortName = ?
       OR I.FullName = ?
       OR I.ShortName = ?
       OR G.GroupName = ?
    """

    cursor.execute(query, (name, name, name, name, name, name, name))
    rows = cursor.fetchall()

    return [row[0] for row in rows]


# Получение списка групп пользователя
def get_user_groups(user_id: int) -> list[str]:
    """Получить список названий групп пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT g.GroupName
        FROM user_groups ug
        JOIN Groups g ON ug.group_id = g.GroupID
        WHERE ug.user_id = ?
    """, (user_id,))
    return [row[0] for row in cursor.fetchall()]


# Получение списка дат пользователя
def get_user_dates(user_id: int) -> list[str]:
    """Получить список дат пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT date FROM user_dates WHERE user_id = ?",
        (user_id,)
    )
    return [row[0] for row in cursor.fetchall()]


# Проверка наличия даты в расписании
def is_date_in_schedule(date_str: str) -> bool:
    """Проверка наличия даты в расписании"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Schedule WHERE Date = ? LIMIT 1", (date_str,))
    result = cursor.fetchone()
    return result is not None


def main():
    for i in range(3):
        search = input()
        # result = is_check_entity(conn, search)
        # result = is_schedule_on_date(conn, search)
        result = get_groups(search)
        print(result)


if __name__ == '__main__':
    main()
