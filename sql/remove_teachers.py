from sql.get_teachers import get_teacher_id
from utils import logger
from .add_teachers import get_user_id
from .init_connection import get_connection


def remove_user_teacher(user: int, teacher_name: str):
    """Удалить привязку преподавателя к пользователю"""
    user_id = get_user_id(user)
    teacher_id = get_teacher_id(teacher_name)
    if teacher_id is None:
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM UserTeachers WHERE UserID = ? AND TeacherID = ?",
        (user_id, teacher_id)
    )
    conn.commit()


def remove_all_user_teachers(user: int):
    """Удалить всех преподавателей пользователя"""
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM UserTeachers WHERE UserID = ?", (user_id,))
    conn.commit()


def remove_meet(meeting_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM BusyWindows WHERE BusyWindowID = ?", (meeting_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.warning(f'Не удалось удалить встречу: {e}')


def remove_meeting_group(date: str, time: str, initiator_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM BusyWindows
            WHERE Date = ? AND Time = ? AND InitiatorTeacherID = ?
        """, (date, time, initiator_id))

        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.warning(f'Ошибка при удалении занятого окна: {e}')
