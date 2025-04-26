import sqlite3

import pandas as pd

from sql.init_connection import get_connection
from utils import logger


# Добавление предметов
def add_subjects(file_path: str):
    """
    Пакетное добавление предметов
    Формат файла: название предмета
    Args:
        file_path: путь до файла
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        subject_names = [line.strip() for line in file if line.strip()]
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Получаем существующие предметы
        cursor.execute("SELECT SubjectName FROM Subjects")
        existing = {row[0] for row in cursor.fetchall()}

        # Фильтруем новые предметы
        new_subjects = [
            (name.strip(),) for name in subject_names
            if name.strip() not in existing
        ]

        if not new_subjects:
            dup_count = len(subject_names)
            logger.info(f"Все {dup_count} предметов уже существуют")
            return
        # Пакетная вставка
        cursor.executemany(
            "INSERT INTO Subjects (SubjectName) VALUES (?)",
            new_subjects
        )

        conn.commit()

        added = len(new_subjects)
        duplicates = [name for name in subject_names if name.strip() in existing]

        logger.info(f"Добавлено {added} предметов, {len(duplicates)} дубликатов")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка пакетного добавления: {str(e)}")


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
        added_count = 0
        missing_institutes = set()

        for faculty_name, faculty_short, institute_name in faculties_data:
            if institute_name not in institute_map:
                missing_institutes.add(institute_name)
                continue

            try:
                cursor.execute(
                    "INSERT INTO Faculties (FacultyName, ShortName, InstituteID) VALUES (?, ?, ?)",
                    (faculty_name, faculty_short, institute_map[institute_name]))
                added_count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Факультет уже существует: {faculty_name}")
            except Exception as e:
                logger.error(f"Ошибка добавления факультета {faculty_name}: {str(e)}")
                raise

        conn.commit()

        if missing_institutes:
            logger.warning(f"Следующие институты не найдены: {', '.join(missing_institutes)}")

        logger.info(f"Успешно добавлено {added_count} факультетов")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except UnicodeDecodeError:
        logger.error("Ошибка декодирования файла. Убедитесь, что файл в кодировке UTF-8")
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

        if not institutes_data:
            logger.warning("Файл не содержит данных для добавления")
            return

        # Добавление в базу данных
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        for full_name, short_name in institutes_data:
            try:
                cursor.execute(
                    "INSERT INTO Institutes (FullName, ShortName) VALUES (?, ?)",
                    (full_name, short_name)
                )
                logger.debug(f"Добавлен институт: {full_name} ({short_name})")
            except sqlite3.IntegrityError:
                logger.warning(f"Пропуск дубликата: {full_name} ({short_name})")
                continue

        conn.commit()
        logger.info(f"Успешно добавлено {len(institutes_data)} институтов из файла")

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

        if not specializations_data:
            logger.warning("Файл не содержит данных для добавления")
            return
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Получаем ID всех факультетов один раз
        cursor.execute("SELECT FacultyID, FacultyName FROM Faculties")
        faculty_map = {name: id_ for id_, name in cursor.fetchall()}

        # Добавляем специальности
        added_count = 0
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
                added_count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Специальность уже существует: {spec_name}")
            except Exception as e:
                logger.error(f"Ошибка добавления специальности {spec_name}: {str(e)}")
                raise

        conn.commit()

        if missing_faculties:
            logger.warning(f"Следующие факультеты не найдены: {', '.join(missing_faculties)}")

        logger.info(f"Успешно добавлено {added_count} специальностей")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
    except UnicodeDecodeError:
        logger.error("Ошибка декодирования файла. Убедитесь, что файл в кодировке UTF-8")
    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


# Добавление уровня образования
def add_educational_levels():
    """
    Добавляет стандартные уровни образования в таблицу EducationalLevel.
    Уровни: Бакалавриат (Б), Специалитет (С), Магистратура (М), Аспирантура (А)

    """
    standard_levels = [
        ("Бакалавриат", "б"),
        ("Специалитет", "с"),
        ("Магистратура", "м"),
        ("Аспирантура", "а")
    ]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Проверяем существующие уровни, чтобы избежать дубликатов
        cursor.execute("SELECT LevelName, ShortName FROM EducationalLevel")
        existing_levels = {(row[0], row[1]) for row in cursor.fetchall()}

        added_count = 0

        for level_name, short_name in standard_levels:
            if (level_name, short_name) not in existing_levels:
                try:
                    cursor.execute(
                        "INSERT INTO EducationalLevel (LevelName, ShortName) VALUES (?, ?)",
                        (level_name, short_name)
                    )
                    added_count += 1
                    logger.debug(f"Добавлен уровень образования: {level_name} ({short_name})")
                except sqlite3.IntegrityError:
                    # На случай параллельного добавления
                    continue

        conn.commit()
        logger.info(f"Добавлено {added_count} новых уровней образования из {len(standard_levels)} возможных")

        return added_count

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении уровней образования: {str(e)}")
        return 0


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

    if df.shape[0] < 2:
        logger.warning(f"DataFrame содержит меньше двух строк — нечего читать")
        return

    try:
        # Извлекаем данные из второй строки
        faculty = df.iloc[0, 0]  # Столбец "faculty"
        group = df.iloc[0, 1]  # Столбец "group"
        specialization = df.iloc[0, 2]  # Столбец "specilizations"
        education_level = df.iloc[0, 3]  # Столбец "education_level"
        institute = int(df.iloc[0, 4])  # Столбец "institute"
        course = int(df.iloc[0, 5])  # Столбец "course"
    except Exception as e:
        logger.warning(f"Ошибка при чтении строки: {e}")
        return

    # Получаем FacultyID
    cursor.execute("""
        SELECT FacultyID 
        FROM Faculties 
        WHERE ShortName = ? AND InstituteID = ?
    """, (faculty, institute))
    faculty_id = cursor.fetchone()
    if not faculty_id:
        logger.warning(f"Факультет '{faculty}' с институтом '{institute}' не найден")
        return
    faculty_id = faculty_id[0]

    # Получаем SpecializationID
    cursor.execute("""
        SELECT SpecializationID 
        FROM Specializations 
        WHERE ShortName = ? AND FacultyID = ?
    """, (specialization, faculty_id))
    specialization_id = cursor.fetchone()
    if not specialization_id:
        logger.warning(f"Специальность '{specialization}' не найдена")
        return
    specialization_id = specialization_id[0]

    # Получаем LevelID
    cursor.execute("""
        SELECT LevelID 
        FROM EducationalLevel 
        WHERE ShortName = ?
    """, (education_level,))
    level_id = cursor.fetchone()
    if not level_id:
        logger.warning(f"Уровень образования '{education_level}' не найден")
        return
    level_id = level_id[0]

    # Проверяем, существует ли группа
    cursor.execute("""
        SELECT GroupID 
        FROM Groups 
        WHERE GroupName = ?
    """, (group,))
    existing_group = cursor.fetchone()
    if existing_group:
        logger.warning(f"Группа '{group}' уже добавлена")
        return

    # Вставляем новую группу
    cursor.execute("""
        INSERT INTO Groups (GroupName, SpecializationID, CourseNumber, LevelID) 
        VALUES (?, ?, ?, ?)
    """, (group, specialization_id, course, level_id))

    conn.commit()
    logger.info(f"Группа '{group}' успешно добавлена")


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
        group_cache = {name: id_ for id_, name in cursor.fetchall()}

        # Кэш предметов
        cursor.execute("SELECT SubjectID, SubjectName FROM Subjects")
        subject_cache = {name: id_ for id_, name in cursor.fetchall()}

        required_columns = ['group', 'date', 'day', 'time', 'subject']
        if not all(col in df.columns for col in required_columns):
            missing = set(required_columns) - set(df.columns)
            logger.warning(f"Отсутствуют колонки: {missing}")
            return

        schedule_data = df[required_columns].dropna().drop_duplicates()
        added_count = 0

        for _, row in schedule_data.iterrows():
            group_name = str(row['group']).strip()
            subject_name = str(row['subject']).strip()
            if not subject_name:
                continue
            date = str(row['date']).strip()
            day = str(row['day']).strip()
            time = str(row['time']).strip()

            group_id = group_cache.get(group_name)
            if not group_id:
                logger.warning(f"Группа '{group_name}' не найдена")
                continue

            subject_id = subject_cache.get(subject_name)
            if not subject_id:
                try:
                    cursor.execute(
                        "INSERT INTO Subjects (SubjectName) VALUES (?)",
                        (subject_name,)
                    )
                    subject_id = cursor.lastrowid
                    subject_cache[subject_name] = subject_id
                except sqlite3.IntegrityError:
                    cursor.execute(
                        "SELECT SubjectID FROM Subjects WHERE SubjectName = ?",
                        (subject_name,)
                    )
                    subject_id = cursor.fetchone()[0]
                    subject_cache[subject_name] = subject_id

            cursor.execute("""
                INSERT INTO Schedule (GroupID, Date, Day, Time, SubjectID)
                VALUES (?, ?, ?, ?, ?)
            """, (group_id, date, day, time, subject_id))
            added_count += 1

        conn.commit()
        logger.info(f"Добавлено {added_count} записей в расписание")

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении расписания: {str(e)}")


# Добавление выбранной группы
def add_user_group(user_id: int, group_name: str):
    """Добавить пользователю группу по названию"""
    conn = get_connection()
    cursor = conn.cursor()

    # Найти ID группы по названию
    cursor.execute("SELECT GroupID FROM Groups WHERE GroupName = ?", (group_name,))
    row = cursor.fetchone()

    group_id = row[0]

    # Вставить в таблицу user_groups
    cursor.execute(
        "INSERT OR IGNORE INTO user_groups (user_id, group_id) VALUES (?, ?)",
        (user_id, group_id)
    )

    conn.commit()


# Добавление выбранной даты
def add_user_date(user_id: int, date: str):
    """Добавить пользователю дату"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO user_dates (user_id, date) VALUES (?, ?)",
        (user_id, date)
    )

    conn.commit()
