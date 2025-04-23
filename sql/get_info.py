import sqlite3
import re
from datetime import datetime
from sql.init_sql import get_connection_gr

PATTERN_GROUP = r"^[а-яА-ЯёЁ]+-\d{4}-\d{2}-\d{2}$"

conn = get_connection_gr()

def is_schedule_on_date(date_str: str) -> bool:
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


def is_check_entity(search_str: str) -> bool:
    """
    Проверяет, существует ли группа/факультет/институт/направление в бд
    !!! Старая версия. В новой теперь проверяем возвращает ли поиск что-то, если возвращает, то это есть
    в базе данных, а следовательно существует
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


def get_groups(name: str) -> list[str]:
    """
    Возвращает список названий групп, которые относятся к переданному названию
    факультета, института или специальности.

    Args:
        conn: соединение с SQLite
        name: строка (название факультета / института / специальности)
    Returns:
        список названий групп
    """
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


def main():
    for i in range(3):
        conn = sqlite3.connect("../window_bot.db")
        search = input()
        # result = is_check_entity(conn, search)
        # result = is_schedule_on_date(conn, search)
        result = get_groups(conn, search)
        print(result)


if __name__ == '__main__':
    main()
