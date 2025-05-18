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

    cursor.execute("SELECT TeacherID FROM Teachers WHERE TeacherFullNameLow = ?", (full_name.lower(),))
    row = cursor.fetchone()
    return row[0] if row else None


def get_all_teachers() -> list[str]:
    """Получить список всех преподавателей из базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    # Выполняем запрос, чтобы получить все группы
    query = "SELECT TeacherFullNameLow FROM Teachers"
    cursor.execute(query)

    # Получаем результаты
    teachers = [row[0] for row in cursor.fetchall()]

    return teachers


def get_teacher_name(teacher_id: int) -> str | None:
    """Получить преподавателя по её ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT FullName FROM Teachers WHERE TeacherID = ?", (teacher_id,))
    row = cursor.fetchone()

    if row:
        return row[0]
    else:
        return None


def get_teachers_sub(name: str):
    """
    Выполняет поиск преподавателей по иерархии:
    1. По институту
    2. По факультету
    3. По кафедре
    4. По имени преподавателя
    5. Ничего не найдено → None
    """
    conn = get_connection()
    cursor = conn.cursor()

    pattern = f"{name.lower()}%"

    # 1. Поиск по институту
    query_institute = """
        SELECT DISTINCT T.FullName, I.FullName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        JOIN Faculties F ON D.FacultyID = F.FacultyID
        JOIN Institutes I ON F.InstituteID = I.InstituteID
        WHERE I.FullNameLow LIKE ? OR I.ShortNameLow LIKE ?
    """
    cursor.execute(query_institute, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        institute_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 0,
            "related": institute_name
        }

    # 2. Поиск по факультету
    query_faculty = """
        SELECT DISTINCT T.FullName, F.FacultyName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        JOIN Faculties F ON D.FacultyID = F.FacultyID
        WHERE F.FacultyNameLow LIKE ? OR F.ShortNameLow LIKE ?
    """
    cursor.execute(query_faculty, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        faculty_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 1,
            "related": faculty_name
        }

    # 3. Поиск по кафедре
    query_department = """
        SELECT DISTINCT T.FullName, D.DepartamentName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        WHERE D.DepartamentNameLow LIKE ? OR D.ShortNameLow LIKE ?
    """
    cursor.execute(query_department, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        department_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 2,
            "related": department_name
        }

    # 4. Поиск по преподавателю
    query_teacher = """
        SELECT DISTINCT FullName
        FROM Teachers
        WHERE TeacherFullNameLow LIKE ?
    """
    cursor.execute(query_teacher, (pattern,))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        return {
            "teachers": teachers,
            "code": 3,
            "related": None
        }

    # Ничего не найдено
    return None


def get_teachers_sub_id(name: str):
    """
    Выполняет поиск преподавателей по иерархии:
    1. По институту
    2. По факультету
    3. По кафедре
    4. По имени преподавателя
    5. Ничего не найдено → None
    """
    conn = get_connection()
    cursor = conn.cursor()

    pattern = f"{name.lower()}%"

    # 1. Поиск по институту
    query_institute = """
        SELECT DISTINCT T.TeacherID, I.FullName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        JOIN Faculties F ON D.FacultyID = F.FacultyID
        JOIN Institutes I ON F.InstituteID = I.InstituteID
        WHERE I.FullNameLow LIKE ? OR I.ShortNameLow LIKE ?
    """
    cursor.execute(query_institute, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        institute_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 0,
            "related": institute_name
        }

    # 2. Поиск по факультету
    query_faculty = """
        SELECT DISTINCT T.TeacherID, F.FacultyName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        JOIN Faculties F ON D.FacultyID = F.FacultyID
        WHERE F.FacultyNameLow LIKE ? OR F.ShortNameLow LIKE ?
    """
    cursor.execute(query_faculty, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        faculty_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 1,
            "related": faculty_name
        }

    # 3. Поиск по кафедре
    query_department = """
        SELECT DISTINCT T.TeacherID, D.DepartamentName
        FROM Teachers T
        JOIN Departament D ON T.DepartamentID = D.DepartamentID
        WHERE D.DepartamentNameLow LIKE ? OR D.ShortNameLow LIKE ?
    """
    cursor.execute(query_department, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        department_name = rows[0][1]
        return {
            "teachers": teachers,
            "code": 2,
            "related": department_name
        }

    # 4. Поиск по преподавателю
    query_teacher = """
        SELECT DISTINCT TeacherID
        FROM Teachers
        WHERE TeacherFullNameLow LIKE ?
    """
    cursor.execute(query_teacher, (pattern,))
    rows = cursor.fetchall()
    if rows:
        teachers = [row[0] for row in rows]
        return {
            "teachers": teachers,
            "code": 3,
            "related": None
        }

    # Ничего не найдено
    return None


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
    pattern = f"{search_str.lower()}%"
    # 0. Проверка по преподавателям
    cursor.execute("""
        SELECT 1 FROM Teachers WHERE TeacherFullNameLow LIKE ?
    """, (pattern, ))
    if cursor.fetchone():
        return True
    # 1. Проверка по кафедрам
    cursor.execute("""
        SELECT 1 FROM Departament WHERE DepartamentNameLow LIKE ? OR ShortNameLow LIKE ?
    """, (pattern, pattern))
    if cursor.fetchone():
        return True
    # 2. Проверка по факультетам
    cursor.execute("""
        SELECT 1 FROM Faculties 
        WHERE FacultyNameLow LIKE ? OR ShortNameLow LIKE ?
    """, (pattern, pattern))
    if cursor.fetchone():
        return True

    # 3. Проверка по институтам
    cursor.execute("""
        SELECT 1 FROM Institutes 
        WHERE FullNameLow LIKE ? OR ShortNameLow LIKE ?
    """, (pattern, pattern))
    if cursor.fetchone():
        return True

    return False


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


def is_teacher_hash_authorized(hash_code: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT UserID
        FROM Teachers
        WHERE Hash = ?
    """, (hash_code,))
    row = cursor.fetchone()
    return row is not None and row[0] is not None


def get_meet_teacher(teacher_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Шаг 1: получаем все Date + Time, где учавствует пользователь
        cursor.execute("""
            SELECT DISTINCT Date, Time FROM BusyWindows 
            WHERE TeacherID = ? OR InitiatorTeacherID = ?
        """, (teacher_id, teacher_id))
        date_time_list = cursor.fetchall()

        if not date_time_list:
            return []

        # Шаг 2: по найденным Date + Time — получаем полную информацию о встречах
        query = """
            SELECT 
                Date,
                Time,
                GROUP_CONCAT(DISTINCT CAST(GroupID AS TEXT)) AS Groups,
                GROUP_CONCAT(DISTINCT CAST(TeacherID AS TEXT)) AS Teachers,
                CabinetID,
                Comment,
                BusyWindowID,
                InitiatorTeacherID,
                IsCompleted
            FROM BusyWindows
            WHERE (Date, Time) IN ({})
            GROUP BY Date, Time
            ORDER BY Date DESC, Time
        """.format(','.join(['(?, ?)'] * len(date_time_list)))

        # Подготавливаем параметры для запроса
        params = []
        for row in date_time_list:
            params.extend(row)

        # Добавляем teacher_id ещё раз для проверки инициатора
        cursor.execute(query, params)
        return cursor.fetchall()

    except Exception as e:
        logger.warning(f'Ошибка при парсе занятых окон: {e}')


def is_initiator(meeting_id: int, teacher_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 1 FROM BusyWindows
            WHERE BusyWindowID = ? AND InitiatorTeacherID = ?
        """, (meeting_id, teacher_id))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.warning(f'Не удалось проверить на инициатора: {e}')


def get_teacher_id_tg(tg_id: int) -> int | None:
    """
    Получает TeacherID по Telegram ID (CurrentID в таблице Users).
    Возвращает None, если пользователь не найден или не является преподавателем.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT t.TeacherID
            FROM Teachers t
            JOIN Users u ON t.UserID = u.UserID
            WHERE u.CurrentID = ?
        """, (tg_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.warning(f'Ошибка при получении ид преподавателя: {e}')


def get_teacher_chat_id(teacher_id: int) -> int | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Users.CurrentID
        FROM Teachers
        JOIN Users ON Teachers.UserID = Users.UserID
        WHERE Teachers.TeacherID = ?
    """, (teacher_id,))
    result = cursor.fetchone()
    return result[0] if result else None

