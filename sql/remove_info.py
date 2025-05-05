import sqlite3

from sql import get_user_id
from sql.init_connection import get_connection
from utils import logger


def remove_user_group(user_id: int, group_id: int):
    """Удаление привязки группы к пользователю"""
    conn = get_connection()
    cursor = conn.cursor()

    u_id = get_user_id(user_id)

    cursor.execute(
        "DELETE FROM UserGroups WHERE UserID = ? AND GroupID = ?",
        (u_id, group_id)
    )
    conn.commit()


def remove_all_user_groups(user: int):
    """Удаление всех групп пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    u_id = get_user_id(user)
    cursor.execute(
        "DELETE FROM UserGroups WHERE UserID = ?",
        (u_id,)
    )
    conn.commit()


def remove_user_date(user: int, date: str):
    """Удаление конкретной даты у пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    u_id = get_user_id(user)
    cursor.execute(
        "DELETE FROM UserDates WHERE UserID = ? AND Date = ?",
        (u_id, date)
    )
    conn.commit()


def remove_all_user_dates(user: int):
    """Удаление всех дат у пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    u_id = get_user_id(user)
    cursor.execute(
        "DELETE FROM UserDates WHERE UserID = ?",
        (u_id,)
    )
    conn.commit()


def remove_schedule():
    """Удаление всего расписания"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Schedule")
    conn.commit()
    logger.info("Таблица Schedule очищена")
