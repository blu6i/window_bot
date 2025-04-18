import sqlite3
from utils import logger


# Добавление групп
def add_subjects(conn, subject_names):
    """
    Пакетное добавление предметов

    Параметры:
        conn: соединение с базой данных
        subject_names: массив названий предметов

    Возвращает:
        Кортеж: (добавлено, дубликаты)
    """
    if not subject_names:
        logger.info('Нечего добавлять')

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

# Добавление институтов

# Добавление специальностей

# Добавление предметов
