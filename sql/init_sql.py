import sqlite3

from sql.add_info import (add_institutes, add_faculties, add_educational_levels,
                          add_specializations)
from utils import logger

from sql.init_connection import get_connection_gr

#_conn = None
#LINK_DB = 'db/data-groups.db'

PATH_SUBJECTS = '../../info_for_db/subjects.txt'
PATH_INST = '../../info_for_db/institute.txt'
PATH_FAC = '../../info_for_db/faculties.txt'
PATH_SPEC = '../../info_for_db/spec.txt'


'''def create_connection():
    """Создание подключения к базе данных SQLite"""
    global _conn
    try:
        _conn = sqlite3.connect(LINK_DB)
        logger.info(f"Подключено к {LINK_DB}, версия SQLite: {sqlite3.version}")
    except sqlite3.Error as e:
        logger.error(f'Ошибка инициализации таблицы {str(e)}')


def get_connection_gr():
    global _conn
    if _conn is None:
        try:
            _conn = sqlite3.connect(LINK_DB)
            logger.info(f"Подключено к {LINK_DB}, версия SQLite: {sqlite3.version}")
        except sqlite3.Error as e:
            logger.error(f'Ошибка инициализации таблицы {str(e)}')
    return _conn'''


def create_tables():
    """Создание всех таблиц"""
    conn = get_connection_gr()
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


def build_sql():
    conn = get_connection_gr()
    cursor = conn.cursor()
    create_tables()
    cursor.execute("DELETE FROM Schedule")
    conn.commit()
    logger.info("Таблица Schedule очищена")
    add_institutes(conn, PATH_INST)
    add_faculties(conn, PATH_FAC)
    add_specializations(conn, PATH_SPEC)
    add_educational_levels(conn)
    logger.info("Таблицы успешно созданы")
