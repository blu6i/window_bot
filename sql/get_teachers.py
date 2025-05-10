import sqlite3

from utils import logger
from .add_teachers import get_user_id
from .init_connection import get_connection


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


def get_user_teachers(user: int) -> list[str]:
    """
    Получить список ФИО преподавателей пользователя
    """
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT T.FullName
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
