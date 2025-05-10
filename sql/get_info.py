import sqlite3

import re
from datetime import datetime

from sql.init_connection import get_connection
from utils import logger

PATTERN_GROUP = r"^[а-яА-ЯёЁ]+-\d{4}-\d{2}-\d{2}$"


# Получение ид пользователя
def get_user_id(user: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT UserID FROM Users WHERE CurrentID = ?", (user,))
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute("INSERT INTO Users (CurrentID) VALUES (?)", (user,))
    conn.commit()
    return cursor.lastrowid


# Проверка, что элемент есть в БД
def is_check_entity(search_str: str) -> bool:
    """
    Проверяет, существует ли группа/факультет/институт/направление в бд

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


# Получение имен групп из таблицы с расписанием
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


# Получение ид групп из таблицы с расписанием
def get_groups_id(name: str) -> list[int]:
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
    SELECT G.GroupID
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


def get_all_groups() -> list[str]:
    """Получить список всех групп из базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    # Выполняем запрос, чтобы получить все группы
    query = "SELECT GroupName FROM Groups"
    cursor.execute(query)

    # Получаем результаты
    all_groups = [row[0] for row in cursor.fetchall()]

    return all_groups


# Получение списка групп пользователя
def get_user_groups(user: int) -> list[int]:
    """Получить список ID групп пользователя"""
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT GroupID
            FROM UserGroups
            WHERE UserID = ?
        """, (user_id,))

    return [row[0] for row in cursor.fetchall()]


# Получение списка дат пользователя
def get_user_dates(user: int) -> list[str]:
    """Получить список дат пользователя"""
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT Date FROM UserDates WHERE UserID = ?",
        (user_id,)
    )
    return [row[0] for row in cursor.fetchall()]


def get_group_name(group_id: int) -> str | None:
    """Получить название группы по её ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT GroupName FROM Groups WHERE GroupID = ?", (group_id,))
    row = cursor.fetchone()

    if row:
        return row[0]
    else:
        return None


def get_group_id(group_name: str) -> int | None:
    """Получить ид группы по её названию"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group_name,))
    row = cursor.fetchone()

    if row:
        return row[0]
    else:
        return None


# Проверка наличия даты в расписании
def is_date_in_schedule(date_str: str) -> bool:
    """Проверка наличия даты в расписании"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Schedule WHERE Date = ? LIMIT 1", (date_str,))
    result = cursor.fetchone()
    return result is not None


def get_group_hash(group_id: int) -> str:
    """Получение хэша группы по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Hash FROM Groups WHERE GroupID = ?", (group_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения хэша группы: {e}")
        return None
    finally:
        cursor.close()


def get_teacher_hash(teacher_id: int) -> str:
    """Получение хэша преподавателя по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Hash FROM Teachers WHERE TeacherID = ?", (teacher_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения хэша преподавателя: {e}")
        return None
    finally:
        cursor.close()


def check_cabinet_exists(cabinet_id: int) -> bool:
    """Проверка существования кабинета"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM Cabinets WHERE CabinetID = ?", (cabinet_id,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Ошибка проверки кабинета: {e}")
        return False
    finally:
        cursor.close()


def check_corpus_exists(corpus: str) -> bool:
    """Проверка существования корпуса"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM Cabinets WHERE Corpus = ? LIMIT 1", (corpus,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Ошибка проверки корпуса: {e}")
        return False
    finally:
        cursor.close()


def main():
    for i in range(3):
        search = input()
        # result = is_check_entity(conn, search)
        # result = is_schedule_on_date(conn, search)
        result = get_groups(search)
        print(result)


if __name__ == '__main__':
    main()
