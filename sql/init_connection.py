import sqlite3

from utils import logger

LINK_DB = 'db/data-groups.db'
_conn = None


def get_connection():
    global _conn
    if _conn is None:
        try:
            _conn = sqlite3.connect(LINK_DB)
            create_tables()
            logger.info(f"Подключено к {LINK_DB}, версия SQLite: {sqlite3.version}")
        except sqlite3.Error as e:
            logger.error(f'Ошибка инициализации таблицы {str(e)}')
    return _conn


def create_tables():
    """Создание всех таблиц с обновленной структурой и LowName полями"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Институты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Institutes (
            InstituteID INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE,
            FullNameLow TEXT NOT NULL,
            ShortNameLow TEXT NOT NULL
        )""")

        # 2. Факультеты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculties (
            FacultyID INTEGER PRIMARY KEY AUTOINCREMENT,
            FacultyName TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL UNIQUE,
            InstituteID INTEGER NOT NULL,
            FacultyNameLow TEXT NOT NULL,
            ShortNameLow TEXT NOT NULL,
            FOREIGN KEY (InstituteID) REFERENCES Institutes(InstituteID)
        )""")

        # 3. Специализации
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Specializations (
            SpecializationID INTEGER PRIMARY KEY AUTOINCREMENT,
            SpecializationName TEXT NOT NULL,
            ShortName TEXT NOT NULL,
            FacultyID INTEGER NOT NULL,
            SpecializationNameLow TEXT NOT NULL,
            ShortNameLow TEXT NOT NULL,
            FOREIGN KEY (FacultyID) REFERENCES Faculties(FacultyID)
        )""")

        # 4. Кафедры
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Departament (
            DepartamentID INTEGER PRIMARY KEY AUTOINCREMENT,
            DepartamentName TEXT NOT NULL,
            ShortName TEXT NOT NULL,
            FacultyID INTEGER NOT NULL,
            DepartamentNameLow TEXT NOT NULL,
            ShortNameLow TEXT NOT NULL,
            FOREIGN KEY (FacultyID) REFERENCES Faculties(FacultyID)
        )""")

        # 5. Группы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Groups (
            GroupID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupName TEXT NOT NULL UNIQUE,
            SpecializationID INTEGER NOT NULL,
            GroupNameLow TEXT NOT NULL,
            Hash TEXT,
            ChatID INTEGER,
            FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID)
        )""")

        # 6. Расписание
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Schedule (
            ScheduleID INTEGER PRIMARY KEY AUTOINCREMENT,
            GroupID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Time TEXT NOT NULL,
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID)
        )""")

        # 7. Пользователи
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            CurrentID INTEGER NOT NULL UNIQUE
        )""")

        # 8. Группы пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserGroups (
            UserID INTEGER NOT NULL,
            GroupID INTEGER NOT NULL,
            PRIMARY KEY (UserID, GroupID),
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (GroupID) REFERENCES Groups(GroupID)
        )""")

        # 9. Даты пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserDates (
            UserID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            PRIMARY KEY (UserID, Date),
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )""")

        # 10. Преподаватели пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserTeachers (
            UserID INTEGER NOT NULL,
            TeacherID INTEGER NOT NULL,
            PRIMARY KEY (UserID, TeacherID),
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID)
        )""")

        # 11. Преподаватели
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Teachers (
            TeacherID INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL UNIQUE,
            DepartamentID INTEGER NOT NULL,
            TeacherFullNameLow TEXT NOT NULL,
            Hash TEXT,
            UserID INTEGER,
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (DepartamentID) REFERENCES Departament(DepartamentID)
        )""")

        # 12. Расписание преподавателей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ScheduleTeacher (
            ScheduleTeacherID INTEGER PRIMARY KEY AUTOINCREMENT,
            TeacherID INTEGER NOT NULL,
            Date TEXT NOT NULL,
            Time TEXT NOT NULL,
            FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID)
        )""")

        # 13. Кабинеты
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Cabinets (
                CabinetID INTEGER PRIMARY KEY AUTOINCREMENT,
                Corpus TEXT NOT NULL,
                Number TEXT NOT NULL,
                Date TEXT NOT NULL,
                Time TEXT NOT NULL
            )""")

        # 14. Занятые окна
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS BusyWindows (
                BusyWindowID INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT NOT NULL,
                Time TEXT NOT NULL,
                Comment TEXT,
                GroupID INTEGER,
                TeacherID INTEGER,
                CabinetID INTEGER,
                InitiatorTeacherID INTEGER,
                IsCompleted INTEGER DEFAULT 0,
                FOREIGN KEY (GroupID) REFERENCES Groups(GroupID),
                FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
                FOREIGN KEY (InitiatorTeacherID) REFERENCES Teachers(TeacherID),
                FOREIGN KEY (CabinetID) REFERENCES Cabinets(CabinetID)
            )""")

        conn.commit()
        logger.info('Таблицы созданы с обновленной структурой')

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f'Ошибка создания таблиц: {str(e)}')
        raise
