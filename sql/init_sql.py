import sqlite3
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
    """Создание всех таблиц"""
    try:
        cursor = conn.cursor()
        # Уровень образоания
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS EducationalLevel (
            LevelID INTEGER PRIMARY KEY AUTOINCREMENT,
            LevelName TEXT NOT NULL UNIQUE
        )""")
        # Факультеты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculties (
            FacultyID INTEGER PRIMARY KEY AUTOINCREMENT,
            FacultyName TEXT NOT NULL UNIQUE,
            InstituteID INTEGER NOT NULL,
            FOREIGN KEY (InstituteID) REFERENCES Institutes(InstituteID)
        )""")
        # Направления
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Specializations (
            SpecializationID INTEGER PRIMARY KEY AUTOINCREMENT,
            SpecializationName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE,
            FacultyID INTEGER NOT NULL,
            LevelID INTEGER NOT NULL,
            FOREIGN KEY (FacultyID) REFERENCES Faculties(FacultyID),
            FOREIGN KEY (LevelID) REFERENCES EducationalLevel(LevelID)
        )""")
        # Группа
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Groups (
            GroupID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupName TEXT NOT NULL UNIQUE,
            SpecializationID INTEGER NOT NULL,
            CourseNumber INTEGER NOT NULL CHECK (CourseNumber BETWEEN 1 AND 6),
            FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID)
        )""")
        # Предмет
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Subjects (
            SubjectID INTEGER PRIMARY KEY AUTOINCREMENT,
            SubjectName TEXT NOT NULL UNIQUE
        )""")
        # Расписание
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Schedule (
            ScheduleID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Time TEXT NOT NULL,
            SubjectID INTEGER NOT NULL,
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID),
            FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID)
        )""")
        # Институт
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Institutes (
            InstituteID INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE
        )""")

        logger.info(f'Таблицы инициализированы')
    except sqlite3.Error as e:
        logger.error(f'Ошибка инициализации таблицы {str(e)}')
