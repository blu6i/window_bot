import sqlite3

from utils import logger

LINK_DB = 'db/data-groups.db'
_conn = None


def create_connection():
    """Создание подключения к базе данных SQLite"""
    global _conn
    try:
        _conn = sqlite3.connect(LINK_DB)
        create_tables()
        logger.info(f"Подключено к {LINK_DB}, версия SQLite: {sqlite3.version}")
    except sqlite3.Error as e:
        logger.error(f'Ошибка инициализации таблицы {str(e)}')


def get_connection():
    global _conn
    if _conn is None:
        try:
            _conn = sqlite3.connect(LINK_DB)
            logger.info(f"Подключено к {LINK_DB}, версия SQLite: {sqlite3.version}")
        except sqlite3.Error as e:
            logger.error(f'Ошибка инициализации таблицы {str(e)}')
    return _conn


def create_tables():
    """Создание всех таблиц без уровней образования, курсов и предметов"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Институты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Institutes (
            InstituteID INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE
        )""")

        # 2. Факультеты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculties (
            FacultyID INTEGER PRIMARY KEY AUTOINCREMENT,
            FacultyName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE,
            InstituteID INTEGER NOT NULL,
            FOREIGN KEY (InstituteID) REFERENCES Institutes(InstituteID)
        )""")

        # 3. Специализации
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Specializations (
            SpecializationID INTEGER PRIMARY KEY AUTOINCREMENT,
            SpecializationName TEXT NOT NULL,
            ShortName TEXT NOT NULL,
            FacultyID INTEGER NOT NULL,
            FOREIGN KEY (FacultyID) REFERENCES Faculties(FacultyID)
        )""")

        # 4. Группы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Groups (
            GroupID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupName TEXT NOT NULL UNIQUE,
            SpecializationID INTEGER NOT NULL,
            FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID)
        )""")

        # 5. Расписание (без SubjectID и связи с Subjects)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Schedule (
            ScheduleID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Time TEXT NOT NULL,
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID)
        )""")

        # 6. Пользователи
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY
        )""")

        # 7. Группы пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_groups (
            UserID INTEGER NOT NULL,
            GroupID INTEGER NOT NULL,
            PRIMARY KEY (UserID, GroupID),
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID)
        )""")

        # 8. Даты пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_dates (
            UserID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            PRIMARY KEY (UserID, Date),
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )""")

        conn.commit()
        logger.info('Таблицы созданы с обновленной структурой')

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f'Ошибка создания таблиц: {str(e)}')
        raise

