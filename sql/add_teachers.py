import hashlib
import os
import sqlite3
from datetime import datetime

import pandas as pd

from sql.init_connection import get_connection
from utils import logger

from dotenv import load_dotenv

load_dotenv('../config/.env')


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


def generate_hash(fullname: str) -> str:
    """
    Генерирует хэш на основе полного имени преподавателя и секретного ключа из .env
    """
    key = os.getenv('HASH_TOKEN')
    data_to_hash = key + fullname.strip()
    return hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()


# Добавление преподавателя
def add_teachers(df: pd.DataFrame):
    """
    Добавляет новых преподавателей в таблицу Teachers на основе DataFrame.
    Требуется наличие колонок: 'teacher' и 'departament'.

    Args:
        df (pd.DataFrame): DataFrame с колонками 'teacher' и 'departament'.
    """
    conn = get_connection()
    added_count = 0
    missing_departments = set()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Проверка обязательных колонок
        required_columns = {'teacher', 'departament'}
        if not required_columns.issubset(df.columns):
            logger.warning(f"DataFrame должен содержать колонки: {required_columns}")
            return

        # Удаляем пустые значения и дубликаты
        teacher_data = df[['teacher', 'departament']].dropna().drop_duplicates()

        # Получаем уже существующих преподавателей (по FullNameLow)
        cursor.execute("SELECT TeacherFullNameLow FROM Teachers")
        existing_teachers_low = {row[0] for row in cursor.fetchall()}

        # Кэшируем кафедры с регистронезависимым поиском через DepartamentNameLow
        cursor.execute("SELECT DepartamentID, DepartamentNameLow FROM Departament")
        departament_map = {name_low: id_ for id_, name_low in cursor.fetchall()}

        for _, row in teacher_data.iterrows():
            fullname = str(row['teacher']).strip()
            dep_name = str(row['departament']).strip()

            if not fullname or not dep_name:
                continue

            fullname_low = fullname.lower()
            dep_name_low = dep_name.lower()

            # Проверяем, существует ли такой преподаватель
            if fullname_low in existing_teachers_low:
                # logger.info(f"Преподаватель '{fullname}' уже существует")
                continue

            # Проверяем, существует ли кафедра
            departament_id = departament_map.get(dep_name_low)
            if departament_id is None:
                missing_departments.add(dep_name)
                continue

            teacher_hash = generate_hash(fullname)

            try:
                cursor.execute("""
                    INSERT INTO Teachers (
                        FullName, DepartamentID, Hash, TeacherFullNameLow
                    ) VALUES (?, ?, ?, ?)
                """, (
                    fullname,
                    departament_id,
                    teacher_hash,
                    fullname_low
                ))
                added_count += 1
                existing_teachers_low.add(fullname_low)
            except sqlite3.IntegrityError as e:
                logger.warning(f"Ошибка целостности при добавлении '{fullname}': {str(e)}")
            except Exception as e:
                logger.error(f"Ошибка добавления преподавателя '{fullname}': {str(e)}")
                raise

        conn.commit()

        if missing_departments:
            logger.warning(f"Кафедры не найдены: {', '.join(missing_departments)}")

        logger.info(f"Добавлено {added_count} новых преподавателей")

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении преподавателей: {e}")
        raise


# Добавление расписания преподавателей
def add_schedule_teacher(df: pd.DataFrame):
    """
    Добавляет расписание преподавателей на основе DataFrame.
    Старые записи НЕ удаляются — предполагается, что это делается отдельно.

    Args:
        df: DataFrame с данными
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Кэш преподавателей
        cursor.execute("SELECT TeacherID, FullName FROM Teachers")
        teacher_cache = {name.strip(): id_ for id_, name in cursor.fetchall()}

        required_columns = ['teacher', 'date', 'time', 'subject']

        schedule_data = df[required_columns].dropna().drop_duplicates()
        added_count = 0
        today = datetime.today().date()

        for _, row in schedule_data.iterrows():
            try:
                # Проверка на актуальность даты
                date_str = str(row['date']).strip()
                row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if row_date < today:
                    continue  # Пропускаем устаревшие записи
            except Exception as e:
                logger.warning(f"Ошибка при обработке даты: {e}")
                continue

            subject = str(row['subject']).strip()
            if not subject:
                continue  # Пропускаем строку без названия предмета

            teacher_name = str(row['teacher']).strip()
            time = str(row['time']).strip()

            teacher_id = teacher_cache.get(teacher_name)
            if not teacher_id:
                logger.warning(f"Преподаватель '{teacher_name}' не найден")
                continue

            cursor.execute("""
                INSERT INTO ScheduleTeacher (TeacherID, Date, Time)
                VALUES (?, ?, ?)
            """, (teacher_id, date_str, time))
            added_count += 1

        conn.commit()
        logger.info(f"Добавлено {added_count} записей в расписание преподавателей")

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении расписания преподавателей: {str(e)}")


def add_user_teacher(user: int, teacher_name: str) -> bool:
    """
    Добавить преподавателя пользователю по ФИО.
    Если пользователя нет в базе — добавляется.
    """
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT TeacherID FROM Teachers WHERE FullName = ?", (teacher_name,))
    row = cursor.fetchone()
    if not row:
        return False

    teacher_id = row[0]

    cursor.execute(
        "INSERT OR IGNORE INTO UserTeachers (UserID, TeacherID) VALUES (?, ?)",
        (user_id, teacher_id)
    )
    conn.commit()
    return True
