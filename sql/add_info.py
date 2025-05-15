import hashlib
import os
import sqlite3
from datetime import datetime

import pandas as pd

from sql.get_info import get_user_id
from sql.init_connection import get_connection
from utils import logger
from dotenv import load_dotenv

load_dotenv('../config/.env')

def generate_hash(fullname: str) -> str:
    """
    Генерирует хэш на основе полного имени преподавателя и секретного ключа из .env
    """
    key = os.getenv('HASH_TOKEN')
    data_to_hash = key + fullname.strip()
    return hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()


# Добавление факультета
def add_faculties(file_path: str):
    """
    Читает факультеты из файла и добавляет их в БД,
    связывая с институтами через регистронезависимый поиск.

    Формат файла (каждая строка): факультет;аббревиатура;название_института

    Args:
        file_path: путь до файла с факультетами
    """
    conn = get_connection()
    try:
        # Чтение и подготовка данных
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip()]

        # Парсинг данных
        faculties_data = []
        for line in lines:
            if line.count(';') != 2:
                logger.warning(f"Пропущена некорректная строка: {line}")
                continue

            faculty_name, faculty_short, institute_name = map(str.strip, line.split(';'))
            faculties_data.append((faculty_name, faculty_short, institute_name))

        if not faculties_data:
            logger.warning("Файл не содержит данных для добавления")
            return

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Получаем все институты в нижнем регистре для регистронезависимого поиска
        cursor.execute("SELECT InstituteID, FullNameLow FROM Institutes")
        institute_map = {name_low: id_ for id_, name_low in cursor.fetchall()}

        # Добавляем факультеты
        count = 0
        missing_institutes = set()

        for faculty_name, faculty_short, institute_name in faculties_data:
            institute_name_low = institute_name.lower()

            if institute_name_low not in institute_map:
                missing_institutes.add(institute_name)
                continue

            institute_id = institute_map[institute_name_low]

            try:
                cursor.execute("""
                    INSERT INTO Faculties (
                        FacultyName, ShortName, InstituteID, FacultyNameLow, ShortNameLow
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    faculty_name,
                    faculty_short,
                    institute_id,
                    faculty_name.lower(),
                    faculty_short.lower()
                ))
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Факультет уже существует: {faculty_name}")
            except Exception as e:
                logger.error(f"Ошибка добавления факультета {faculty_name}: {str(e)}")
                raise

        conn.commit()

        if missing_institutes:
            logger.warning(f"Следующие институты не найдены: {', '.join(missing_institutes)}")

        logger.info(f"Успешно добавлено {count} факультетов")

    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление институтов
def add_institutes(file_path: str):
    """
    Читает институты из файла и добавляет их в базу данных.
    Формат файла: Институт;аббревиатура

    Args:
        file_path: путь к файлу с институтами
    """
    conn = get_connection()
    try:
        # Чтение данных из файла
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip()]

        # Парсинг строк
        institutes_data = []
        for line in lines:
            if ';' not in line:
                logger.warning(f"Пропущена некорректная строка: {line}")
                continue

            full_name, short_name = line.split(';', 1)
            institutes_data.append((full_name.strip(), short_name.strip()))

        if not institutes_data:
            logger.warning("Файл не содержит корректных данных")
            return

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        count = 0
        for full_name, short_name in institutes_data:
            try:
                cursor.execute("""
                    INSERT INTO Institutes (
                        FullName,
                        ShortName,
                        FullNameLow,
                        ShortNameLow
                    ) VALUES (?, ?, ?, ?)
                """, (
                    full_name,
                    short_name,
                    full_name.lower(),
                    short_name.lower()
                ))
                logger.debug(f"Добавлен институт: {full_name} ({short_name})")
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Пропуск дубликата: {full_name} ({short_name})")
            except Exception as e:
                logger.error(f"Ошибка добавления института '{full_name}': {str(e)}")
                raise

        conn.commit()
        logger.info(f"Успешно добавлено {count} институтов из файла")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при обработке файла: {str(e)}")
        raise


# Добавление специальностей
def add_specializations(file_path: str):
    """
    Добавляет специальности из файла в базу данных.
    Формат файла: Название_специальности;аббревиатура;название_факультета

    Args:
        file_path: путь до файла с дисциплинами
    """
    conn = get_connection()
    try:
        # Чтение данных из файла
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip()]

        # Парсинг данных
        specializations_data = []
        for line in lines:
            if line.count(';') != 2:
                logger.warning(f"Пропущена некорректная строка: {line}")
                continue

            spec_name, short_name, faculty_name = map(str.strip, line.split(';'))
            specializations_data.append((spec_name, short_name, faculty_name))

        if not specializations_data:
            logger.warning("Файл не содержит корректных данных")
            return

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Получаем все факультеты в нижнем регистре для регистронезависимого поиска
        cursor.execute("SELECT FacultyID, FacultyNameLow FROM Faculties")
        faculty_map = {name_low: id_ for id_, name_low in cursor.fetchall()}

        count = 0
        missing_faculties = set()

        for spec_name, short_name, faculty_name in specializations_data:
            faculty_name_low = faculty_name.lower()

            if faculty_name_low not in faculty_map:
                missing_faculties.add(faculty_name)
                continue

            faculty_id = faculty_map[faculty_name_low]

            # Проверка на существование специальности (регистрозависимо)
            cursor.execute("""
                SELECT 1 FROM Specializations
                WHERE SpecializationName = ? AND ShortName = ? AND FacultyID = ?
            """, (spec_name, short_name, faculty_id))

            if cursor.fetchone():
                logger.info(f"Пропущена уже существующая специальность: {spec_name} ({short_name})")
                continue

            try:
                cursor.execute("""
                    INSERT INTO Specializations (
                        SpecializationName, ShortName, FacultyID,
                        SpecializationNameLow, ShortNameLow
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    spec_name,
                    short_name,
                    faculty_id,
                    spec_name.lower(),
                    short_name.lower()
                ))
                count += 1
            except Exception as e:
                logger.error(f"Ошибка добавления специальности {spec_name}: {str(e)}")
                raise

        conn.commit()

        if missing_faculties:
            logger.warning(f"Следующие факультеты не найдены: {', '.join(missing_faculties)}")

        logger.info(f"Успешно добавлено {count} специальностей")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление кафедры
def add_departments(file_path: str):
    """
    Добавляет кафедры из файла в базу данных.
    Формат файла: Название_кафедры;аббревиатура;аббревиатура_факультета

    Args:
        file_path: путь до файла с кафедрами
    """
    conn = get_connection()
    try:
        # Чтение данных из файла
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip()]

        # Парсинг строк
        departments_data = []
        for line in lines:
            if line.count(';') != 2:
                logger.warning(f"Пропущена некорректная строка: {line}")
                continue

            dep_name, short_name, faculty_short = map(str.strip, line.split(';'))
            departments_data.append((dep_name, short_name, faculty_short))

        if not departments_data:
            logger.warning("Файл не содержит корректных данных")
            return

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Кэшируем факультеты по ShortNameLow (для регистронезависимого поиска)
        cursor.execute("SELECT FacultyID, ShortNameLow FROM Faculties")
        faculty_map = {short_low: id_ for id_, short_low in cursor.fetchall()}

        count = 0
        missing_faculties = set()

        for dep_name, short_name, faculty_short in departments_data:
            faculty_short_low = faculty_short.lower()

            if faculty_short_low not in faculty_map:
                missing_faculties.add(faculty_short)
                continue

            faculty_id = faculty_map[faculty_short_low]

            # Проверка на существование кафедры
            cursor.execute("""
                SELECT 1 FROM Departament
                WHERE DepartamentName = ? AND ShortName = ? AND FacultyID = ?
            """, (dep_name, short_name, faculty_id))

            if cursor.fetchone():
                logger.info(f"Пропущена уже существующая кафедра: {dep_name} ({short_name})")
                continue

            try:
                cursor.execute("""
                    INSERT INTO Departament (
                        DepartamentName, ShortName, FacultyID,
                        DepartamentNameLow, ShortNameLow
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    dep_name,
                    short_name,
                    faculty_id,
                    dep_name.lower(),
                    short_name.lower()
                ))
                count += 1
            except Exception as e:
                logger.error(f"Ошибка добавления кафедры {dep_name}: {str(e)}")
                raise

        conn.commit()

        if missing_faculties:
            logger.warning(f"Факультеты не найдены (по аббревиатуре): {', '.join(missing_faculties)}")

        logger.info(f"Успешно добавлено {count} кафедр")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление групп
def add_groups(df: pd.DataFrame):
    """
    Добавляет группу из второй строки DataFrame.
    Формат строки: факультет, название группы, специальность, уровень образования, институт, курс

    Args:
        df: DataFrame, содержащий хотя бы 2 строки
    """
    conn = get_connection()
    cursor = conn.cursor()

    if df.shape[0] < 1:
        logger.warning("DataFrame пустой — нечего добавлять")
        return

    try:
        faculty_short = str(df.iloc[0, 0]).strip()  # ShortName факультета
        group_name = str(df.iloc[0, 1]).strip()  # Название группы
        specialization_short = str(df.iloc[0, 2]).strip()  # ShortName специальности
        institute_id = int(df.iloc[0, 4])  # ID института
    except Exception as e:
        logger.warning(f"Ошибка при чтении строки: {e}")
        return

    try:
        # Получаем FacultyID через регистронезависимый поиск
        cursor.execute("""
            SELECT FacultyID 
            FROM Faculties 
            WHERE ShortNameLow = ? AND InstituteID = ?
        """, (faculty_short.lower(), institute_id))
        faculty_result = cursor.fetchone()
        if not faculty_result:
            logger.warning(f"Факультет '{faculty_short}' с институтом ID '{institute_id}' не найден")
            return
        faculty_id = faculty_result[0]

        # Получаем SpecializationID через регистронезависимый поиск
        cursor.execute("""
            SELECT SpecializationID 
            FROM Specializations 
            WHERE ShortNameLow = ? AND FacultyID = ?
        """, (specialization_short.lower(), faculty_id))
        specialization_result = cursor.fetchone()
        if not specialization_result:
            logger.warning(f"Специальность '{specialization_short}' не найдена")
            return
        specialization_id = specialization_result[0]

        # Проверяем существование группы регистронезависимо
        cursor.execute("""
            SELECT GroupID FROM Groups 
            WHERE GroupNameLow = ?
        """, (group_name.lower(),))
        if cursor.fetchone():
            logger.warning(f"Группа '{group_name}' уже существует")
            return
        group_hash = generate_hash(group_name)
        # Вставляем группу с нормализованным названием
        cursor.execute("""
            INSERT INTO Groups (
                GroupName, SpecializationID, GroupNameLow, Hash
            ) VALUES (?, ?, ?, ?)
        """, (
            group_name,
            specialization_id,
            group_name.lower(),
            group_hash
        ))

        conn.commit()
        logger.info(f"Группа '{group_name}' успешно добавлена")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении группы: {e}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление расписания
def add_schedule(df: pd.DataFrame):
    """
    Добавляет расписание на основе DataFrame.
    Старые записи НЕ удаляются — предполагается, что это делается отдельно.

    Args:
        df: DataFrame с данными
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Кэш групп
        cursor.execute("SELECT GroupID, GroupName FROM Groups")
        group_cache = {name.strip(): id_ for id_, name in cursor.fetchall()}

        required_columns = ['group', 'date', 'time', 'subject']

        schedule_data = df[required_columns].dropna().drop_duplicates()
        added_count = 0
        today = datetime.today().date()

        for _, row in schedule_data.iterrows():
            try:
                # Проверка на актуальность дат
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

            group_name = str(row['group']).strip()
            time = str(row['time']).strip()

            group_id = group_cache.get(group_name)
            if not group_id:
                logger.warning(f"Группа '{group_name}' не найдена")
                continue

            cursor.execute("""
                    INSERT INTO Schedule (GroupID, Date, Time)
                    VALUES (?, ?, ?)
                """, (group_id, date_str, time))
            added_count += 1

        conn.commit()
        logger.info(f"Добавлено {added_count} записей в расписание")

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении расписания: {str(e)}")


# Добавление группы пользователю
def add_user_group(user: int, group_name: str) -> bool:
    """
        Добавить пользователю выбранную группу.
        Если пользователя нет в базе, то сначала добавляем его.
    """
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group_name,))
    row = cursor.fetchone()
    if not row:
        return False

    group_id = row[0]

    cursor.execute(
        "INSERT OR IGNORE INTO UserGroups (UserID, GroupID) VALUES (?, ?)",
        (user_id, group_id)
    )
    conn.commit()
    return True


# Добавление даты пользователю
def add_user_date(user: int, date: str):
    """
    Добавить пользователю выбранную дату.
    Если пользователя нет в базе, то сначала добавляем его.
    """
    user_id = get_user_id(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO UserDates (UserID, Date) VALUES (?, ?)",
        (user_id, date)
    )
    conn.commit()


def add_busy_window(current_date, times, group_id, teacher_id, cabinet_id, comment, initiator_teacher_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for time in times:
            cursor.execute("""
                INSERT INTO BusyWindows 
                    (Date, Time, GroupID, TeacherID, CabinetID, Comment, InitiatorTeacherID)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                current_date,
                time,
                group_id,
                teacher_id if teacher_id is not None else None,
                cabinet_id,
                comment,
                initiator_teacher_id
            ))
        conn.commit()
    except Exception as e:
        logger.warning(f'Проблема при добавлении окна: {e}')



def add_chat_group(group_id: int, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Groups SET ChatID = ? WHERE GroupID = ?", (chat_id, group_id))
    conn.commit()


def unadd_chat_group(group_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Groups SET ChatID = ? WHERE ChatID = ?", (None, group_id))
    conn.commit()
