import sqlite3
from datetime import datetime

import pandas as pd

from sql.init_connection import get_connection
from sql.get_info import get_user_id
from utils import logger


# Добавление факультета
def add_faculties(file_path: str):
    """
    Читает факультеты из файла и добавляет их в БД, связывая с существующими институтами.
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

        # Получаем ID всех институтов один раз
        cursor.execute("SELECT InstituteID, FullName FROM Institutes")
        institute_map = {name: id_ for id_, name in cursor.fetchall()}

        # Добавляем факультеты
        count = 0
        missing_institutes = set()

        for faculty_name, faculty_short, institute_name in faculties_data:
            if institute_name not in institute_map:
                missing_institutes.add(institute_name)
                continue

            try:
                cursor.execute(
                    "INSERT INTO Faculties (FacultyName, ShortName, InstituteID) VALUES (?, ?, ?)",
                    (faculty_name, faculty_short, institute_map[institute_name]))
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

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except UnicodeDecodeError:
        logger.error("Ошибка декодирования файла.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление институтов
def add_institutes(file_path: str):
    """
    Читает институты из файла и добавляет их в базу данных в том же порядке.
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
            if ';' in line:
                full_name, short_name = line.split(';', 1)
                institutes_data.append((full_name.strip(), short_name.strip()))

        # Добавление в базу данных
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        count = 0
        for full_name, short_name in institutes_data:
            try:
                cursor.execute(
                    "INSERT INTO Institutes (FullName, ShortName) VALUES (?, ?)",
                    (full_name, short_name)
                )
                logger.debug(f"Добавлен институт: {full_name} ({short_name})")
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Пропуск дубликата: {full_name} ({short_name})")
                continue

        conn.commit()
        logger.info(f"Успешно добавлено {count} институтов из файла")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при обработке файла: {str(e)}")


# Добавление специальностей
def add_specializations(file_path: str):
    """
    Добавляет дисциплину из файла в базу данных
    Формат файла: Название дисциплины;аббревиатура;название факультета
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

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Получаем ID всех факультетов один раз
        cursor.execute("SELECT FacultyID, FacultyName FROM Faculties")
        faculty_map = {name: id_ for id_, name in cursor.fetchall()}

        # Добавляем специальности
        count = 0
        missing_faculties = set()

        for spec_name, short_name, faculty_name in specializations_data:
            if faculty_name not in faculty_map:
                missing_faculties.add(faculty_name)
                continue

            try:
                cursor.execute(
                    """INSERT INTO Specializations 
                    (SpecializationName, ShortName, FacultyID) 
                    VALUES (?, ?, ?)""",
                    (spec_name, short_name, faculty_map[faculty_name]))
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Специальность уже существует: {spec_name}")
            except Exception as e:
                logger.error(f"Ошибка добавления специальности {spec_name}: {str(e)}")
                raise

        conn.commit()

        if missing_faculties:
            logger.warning(f"Следующие факультеты не найдены: {', '.join(missing_faculties)}")

        logger.info(f"Успешно добавлено {count} специальностей")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except UnicodeDecodeError:
        logger.error("Ошибка декодирования файла. Убедитесь, что файл в кодировке UTF-8")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление групп
def add_groups(df: pd.DataFrame):
    """
    Добавляет группу из второй строки DataFrame (аналогично чтению второй строки из Excel)
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
        faculty_short = df.iloc[0, 0]  # ShortName факультета
        group_name = df.iloc[0, 1]  # Название группы
        specialization_short = df.iloc[0, 2]  # ShortName специальности
        institute_id = int(df.iloc[0, 4])  # ID института
    except Exception as e:
        logger.warning(f"Ошибка при чтении строки: {e}")
        return

    try:
        # Получаем FacultyID
        cursor.execute("""
            SELECT FacultyID 
            FROM Faculties 
            WHERE ShortName = ? AND InstituteID = ?
        """, (faculty_short, institute_id))
        faculty_id = cursor.fetchone()
        if not faculty_id:
            logger.warning(f"Факультет '{faculty_short}' с институтом ID '{institute_id}' не найден")
            return
        faculty_id = faculty_id[0]

        # Получаем SpecializationID
        cursor.execute("""
            SELECT SpecializationID 
            FROM Specializations 
            WHERE ShortName = ? AND FacultyID = ?
        """, (specialization_short, faculty_id))
        specialization_id = cursor.fetchone()
        if not specialization_id:
            logger.warning(f"Специальность '{specialization_short}' не найдена")
            return
        specialization_id = specialization_id[0]

        # Проверяем, существует ли группа
        cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group_name,))
        if cursor.fetchone():
            logger.warning(f"Группа '{group_name}' уже существует")
            return

        # Вставляем группу
        cursor.execute("""
            INSERT INTO Groups (GroupName, SpecializationID) 
            VALUES (?, ?)
        """, (group_name, specialization_id))

        conn.commit()
        logger.info(f"Группа '{group_name}' успешно добавлена")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении группы: {e}")


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
