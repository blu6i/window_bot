import sqlite3

from sql.init_connection import get_connection
from utils import logger


def remove_user_group(user_id: int, group_id: int):
    """Удаление привязки группы к пользователю"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_groups WHERE user_id = ? AND group_id = ?",
        (user_id, group_id)
    )
    conn.commit()


def remove_all_user_groups(user_id: int):
    """Удаление всех групп пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_groups WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()


def remove_user_date(user_id: int, date: str):
    """Удаление конкретной даты у пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_dates WHERE user_id = ? AND date = ?",
        (user_id, date)
    )
    conn.commit()


def remove_all_user_dates(user_id: int):
    """Удаление всех дат у пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_dates WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()


def remove_schedule():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Schedule")
    conn.commit()
    logger.info("Таблица Schedule очищена")
