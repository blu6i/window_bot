import os
import sqlite3

import pandas as pd

from utils import logger


# Добавление предметов
def add_subjects(conn, file_path):
    """
    Пакетное добавление предметов

    Параметры:
        conn: соединение с базой данных
        subject_names: массив названий предметов

    Возвращает:
        Кортеж: (добавлено, дубликаты)
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        subject_names = [line.strip() for line in file if line.strip()]

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
            return 0, subject_names

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
def add_faculties(conn, file_path):
    """
    Читает факультеты из файла и добавляет их в БД, связывая с существующими институтами.
    Формат файла (каждая строка):
    факультет;аббревиатура;название_института
    """
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
def add_institutes(conn, file_path):
    """
    Читает институты из файла и добавляет их в базу данных в том же порядке.
    Формат файла: каждая строка содержит полное название и аббревиатуру через разделитель ';'

    Параметры:
        conn: соединение с SQLite базой данных
        file_path: путь к текстовому файлу
    """
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
def add_specializations(conn, file_path):
    """
    Добавляет специальности из файла в базу данных
    Формат файла: name;short_name;faculty_name
    """
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
        faculty_map = {name: id for id, name in cursor.fetchall()}

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
def add_educational_levels(conn):
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
def add_groups(conn, folder_path):
    cursor = conn.cursor()

    # Проходим по всем файлам в папке
    for filename in os.listdir(folder_path):
        if filename.endswith('.xlsx'):
            excel_file_path = os.path.join(folder_path, filename)

            # Читаем только вторую строку файла (индекс 1)
            df = pd.read_excel(excel_file_path, header=None, skiprows=1, nrows=1)

            # Извлекаем данные из второй строки
            faculty = df.iloc[0, 0]  # Столбец "faculty"
            group = df.iloc[0, 1]  # Столбец "group"
            specialization = df.iloc[0, 2]  # Столбец "specilizations"
            education_level = df.iloc[0, 3]  # Столбец "education_level"
            institute = int(df.iloc[0, 4])  # Столбец "institute"
            course = int(df.iloc[0, 5])  # Столбец "course"

            # Находим FacultyID по имени факультета и InstituteID
            cursor.execute("""
                SELECT FacultyID 
                FROM Faculties 
                WHERE ShortName = ? AND InstituteID = ?
            """, (faculty, institute))
            faculty_id = cursor.fetchone()
            if not faculty_id:
                print(f"Faculty '{faculty}' with institute '{institute}' not found.")
                continue
            faculty_id = faculty_id[0]

            # Находим SpecializationID по ShortName специализации и FacultyID
            cursor.execute("""
                SELECT SpecializationID 
                FROM Specializations 
                WHERE ShortName = ? AND FacultyID = ?
            """, (specialization, faculty_id))
            specialization_id = cursor.fetchone()
            if not specialization_id:
                print(f"Specialization '{specialization}' for faculty '{faculty}' not found.")
                continue
            specialization_id = specialization_id[0]

            # Находим LevelID по имени уровня образования
            cursor.execute("""
                SELECT LevelID 
                FROM EducationalLevel 
                WHERE ShortName = ?
            """, (education_level,))
            level_id = cursor.fetchone()
            if not level_id:
                print(f"Educational level '{education_level}' not found.")
                continue
            level_id = level_id[0]

            # Проверяем, существует ли группа с таким названием
            cursor.execute("""
                SELECT GroupID 
                FROM Groups 
                WHERE GroupName = ?
            """, (group,))
            existing_group = cursor.fetchone()
            if existing_group:
                print(f"Group '{group}' already exists.")
                continue

            # Вставляем новую группу в таблицу Groups
            cursor.execute("""
                INSERT INTO Groups (GroupName, SpecializationID, CourseNumber, LevelID) 
                VALUES (?, ?, ?, ?)
            """, (group, specialization_id, course, level_id))

            # Сохраняем изменения в базе данных
            conn.commit()
            print(f"Group '{group}' from file '{filename}' added successfully.")

# Добавление расписания
import os
import pandas as pd
import sqlite3
from utils import logger


def add_schedule(conn, folder_path):
    """
    Добавляет расписание из всех Excel файлов в указанной папке в базу данных
    Формат Excel: group | date | day | time | subject
    """
    try:
        # Получаем список Excel файлов в папке
        excel_files = [f for f in os.listdir(folder_path)
                       if f.endswith(('.xlsx', '.xls'))]

        if not excel_files:
            logger.warning(f"В папке {folder_path} не найдено Excel файлов")
            return 0

        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Подготовка кэша для быстрого доступа
        group_cache = {}
        subject_cache = {}

        # Заполняем кэш существующими данными
        cursor.execute("SELECT GroupID, GroupName FROM Groups")
        group_cache = {name: id for id, name in cursor.fetchall()}

        cursor.execute("SELECT SubjectID, SubjectName FROM Subjects")
        subject_cache = {name: id for id, name in cursor.fetchall()}

        total_added = 0

        for file_name in excel_files:
            file_path = os.path.join(folder_path, file_name)
            try:
                # Чтение Excel файла
                df = pd.read_excel(file_path)
                required_columns = ['group', 'date', 'day', 'time', 'subject']

                # Проверка наличия всех необходимых колонок
                if not all(col in df.columns for col in required_columns):
                    missing = set(required_columns) - set(df.columns)
                    logger.warning(f"В файле {file_name} отсутствуют колонки: {missing}")
                    continue

                # Обработка данных
                schedule_data = df[required_columns].dropna().drop_duplicates()
                added_in_file = 0

                for _, row in schedule_data.iterrows():
                    group_name = str(row['group']).strip()
                    subject_name = str(row['subject']).strip()
                    date = str(row['date']).strip()
                    day = str(row['day']).strip()
                    time = str(row['time']).strip()

                    # Получаем GroupID
                    if group_name not in group_cache:
                        logger.warning(f"Группа {group_name} не найдена (файл: {file_name})")
                        continue
                    group_id = group_cache[group_name]

                    # Получаем SubjectID (добавляем если не существует)
                    if subject_name not in subject_cache:
                        try:
                            cursor.execute(
                                "INSERT INTO Subjects (SubjectName) VALUES (?)",
                                (subject_name,)
                            )
                            subject_id = cursor.lastrowid
                            subject_cache[subject_name] = subject_id
                        except sqlite3.IntegrityError:
                            # На случай параллельного добавления
                            cursor.execute(
                                "SELECT SubjectID FROM Subjects WHERE SubjectName = ?",
                                (subject_name,)
                            )
                            subject_id = cursor.fetchone()[0]
                            subject_cache[subject_name] = subject_id

                    subject_id = subject_cache[subject_name]

                    # Добавляем запись в расписание
                    try:
                        cursor.execute(
                            """INSERT INTO Schedule 
                            (GroupID, Date, Day, Time, SubjectID) 
                            VALUES (?, ?, ?, ?, ?)""",
                            (group_id, date, day, time, subject_id)
                        )
                        added_in_file += 1
                    except sqlite3.IntegrityError:
                        # Пропускаем дубликаты расписания
                        continue

                total_added += added_in_file
                logger.info(f"Файл {file_name}: добавлено {added_in_file} записей")

            except Exception as e:
                logger.error(f"Ошибка обработки файла {file_name}: {str(e)}")
                continue

        conn.commit()
        logger.info(f"Всего добавлено {total_added} записей расписания из {len(excel_files)} файлов")
        return total_added

    except Exception as e:
        conn.rollback()
        logger.error(f"Критическая ошибка: {str(e)}")
        return 0