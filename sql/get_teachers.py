import sqlite3

from utils import logger
from .add_teachers import get_user_id
from .init_connection import get_connection


def get_teacher_hash(hash: str) -> str | None:
    """Получение ID преподавателя по hash"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT TeacherID FROM Teachers WHERE Hash = ?", (hash,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения хэша преподавателя: {e}")
        return None


def get_user_teachers(user: int) -> list[int]:
    """
    Получить список ФИО преподавателей пользователя
    """
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT T.TeacherID
        FROM UserTeachers UT
        JOIN Teachers T ON UT.TeacherID = T.TeacherID
        WHERE UT.UserID = ?
    """, (user_id,))

    return [row[0] for row in cursor.fetchall()]


def get_teacher_id(full_name: str) -> int | None:
    """Получить ID преподавателя по ФИО"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT TeacherID FROM Teachers WHERE FullName = ?", (full_name,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_all_teachers() -> list[str]:
    """Получить список всех преподавателей из базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    # Выполняем запрос, чтобы получить все группы
    query = "SELECT FullName FROM Teachers"
    cursor.execute(query)

    # Получаем результаты
    teachers = [row[0] for row in cursor.fetchall()]

    return teachers


def get_teacher_name(teacher_id: int) -> str | None:
    """Получить название группы по её ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT FullName FROM Teachers WHERE TeacherID = ?", (teacher_id,))
    row = cursor.fetchone()

    if row:
        return row[0]
    else:
        return None


def get_teachers_sub(name: str) -> list[dict]:
    """
    Возвращает список преподавателей, относящихся к указанному институту,
    факультету или кафедре.

    Args:
        name (str): название института / факультета / кафедры

    Returns:
        list[dict]: список преподавателей в формате {'name': ..., 'id': ...}
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT T.FullName, T.TeacherID
    FROM Teachers T
    JOIN Departament D ON T.DepartamentID = D.DepartamentID
    JOIN Faculties F ON D.FacultyID = F.FacultyID
    JOIN Institutes I ON F.InstituteID = I.InstituteID
    WHERE I.FullName = ? OR I.ShortName = ?
       OR F.FacultyName = ? OR F.ShortName = ?
       OR D.DepartamentName = ? OR D.ShortName = ?
       OR I.FullNameLow = ? OR I.ShortNameLow = ?
       OR F.FacultyNameLow = ? OR F.ShortNameLow = ?
       OR D.DepartamentNameLow = ? OR D.ShortNameLow = ?
    GROUP BY T.TeacherID
    """

    name_low = name.lower()

    cursor.execute(query, (
        name, name,  # Точное совпадение: институт/факультет/кафедра
        name, name,
        name, name,

        name_low, name_low,  # Регистронезависимое совпадение
        name_low, name_low,
        name_low, name_low
    ))

    rows = cursor.fetchall()
    return [{"name": row[0], "id": row[1]} for row in rows]


def is_check_sub(search_str: str) -> bool:
    """
    Проверяет, существует ли факультет/институт/кафедра в БД.
    Проверяет как точное совпадение, так и регистронезависимое (через *Low-поля).

    Args:
        search_str: строка для проверки (название или аббревиатура)

    Returns:
        True, если такая сущность существует, иначе False
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Приводим к нижнему регистру для регистронезависимого поиска
    search_low = search_str.lower()

    # 1. Проверка по кафедрам
    cursor.execute("""
        SELECT 1 FROM Departament 
        WHERE DepartamentName = ? OR ShortName = ?
           OR DepartamentNameLow = ? OR ShortNameLow = ?
    """, (search_str, search_str, search_low, search_low))
    if cursor.fetchone():
        return True

    # 2. Проверка по факультетам
    cursor.execute("""
        SELECT 1 FROM Faculties 
        WHERE FacultyName = ? OR ShortName = ?
           OR FacultyNameLow = ? OR ShortNameLow = ?
    """, (search_str, search_str, search_low, search_low))
    if cursor.fetchone():
        return True

    # 3. Проверка по институтам
    cursor.execute("""
        SELECT 1 FROM Institutes 
        WHERE FullName = ? OR ShortName = ?
           OR FullNameLow = ? OR ShortNameLow = ?
    """, (search_str, search_str, search_low, search_low))
    if cursor.fetchone():
        return True

    return False


import sqlite3


def is_teacher_authorized(u_id: int) -> bool:
    """
    Проверяет, авторизован ли преподаватель.

    Args:
        u_id: Telegram ID пользователя (CurrentID)
    Return:
        True, если авторизован, иначе False
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT UserID FROM Users WHERE CurrentID = ?", (u_id,))
        user_record = cursor.fetchone()
        if not user_record:
            return False
        user_id = user_record[0]
        cursor.execute("SELECT 1 FROM Teachers WHERE UserID = ?", (user_id,))
        teacher_record = cursor.fetchone()
        return teacher_record is not None
    except Exception as e:
        logger.warning(f'Ошибка при поиске преподавателя {e}')
