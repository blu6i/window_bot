import sqlite3

from sql.add_info import (add_institutes, add_faculties, add_educational_levels, add_schedule,
                          add_specializations, add_groups)
from utils import logger


def create_connection(db_file):
    """Создание подключения к базе данных SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logger.info(f"Подключено к {db_file}, версия SQLite: {sqlite3.version}")
        return conn
    except sqlite3.Error as e:
        logger.error(f'Ошибка инициализации таблицы {str(e)}')
    return conn


def create_tables(conn):
    """Создание всех таблиц с обновленной структурой"""
    try:
        cursor = conn.cursor()

        # 1. Уровни образования
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS EducationalLevel (
            LevelID INTEGER PRIMARY KEY AUTOINCREMENT,
            LevelName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE
        )""")

        # 2. Институты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Institutes (
            InstituteID INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE
        )""")

        # 3. Факультеты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculties (
            FacultyID INTEGER PRIMARY KEY AUTOINCREMENT,
            FacultyName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE,
            InstituteID INTEGER NOT NULL,
            FOREIGN KEY (InstituteID) REFERENCES Institutes(InstituteID)
        )""")

        # 4. Специализации
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Specializations (
            SpecializationID INTEGER PRIMARY KEY AUTOINCREMENT,
            SpecializationName TEXT NOT NULL,
            ShortName TEXT NOT NULL,
            FacultyID INTEGER NOT NULL,
            FOREIGN KEY (FacultyID) REFERENCES Faculties(FacultyID)
        )""")

        # 5. Группы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Groups (
            GroupID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupName TEXT NOT NULL UNIQUE,
            SpecializationID INTEGER NOT NULL,
            CourseNumber INTEGER NOT NULL CHECK (CourseNumber BETWEEN 1 AND 6),
            LevelID INTEGER NOT NULL,
            FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID),
            FOREIGN KEY (LevelID) REFERENCES EducationalLevel(LevelID)
        )""")

        # 6. Предметы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Subjects (
            SubjectID INTEGER PRIMARY KEY AUTOINCREMENT,
            SubjectName TEXT NOT NULL UNIQUE
        )""")

        # 7. Расписание
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Schedule (
            ScheduleID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Day TEXT NOT NULL,
            Time TEXT NOT NULL,
            SubjectID INTEGER NOT NULL,
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID),
            FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID)
        )""")

        conn.commit()
        logger.info('Таблицы созданы с обновленной структурой')

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f'Ошибка создания таблиц: {str(e)}')
        raise


def build_sql(conn, path_institutes: str, path_faculties: str, path_spec: str, path_excel: str):
    create_tables(conn)
    add_institutes(conn, path_institutes)
    add_faculties(conn, path_faculties)
    add_specializations(conn, path_spec)
    add_educational_levels(conn)
    add_groups(conn, path_excel)
    add_schedule(conn, path_excel)
    logger.info("Таблицы успешно созданы")
