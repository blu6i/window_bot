import sqlite3

from utils import logger

LINK_DB = 'тфтdb/data-groups.db'
_conn = None


def create_connection():
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
    return _conn
