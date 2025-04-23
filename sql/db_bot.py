import sqlite3

LINK_DB = 'db/data-bot.db'
conn = None


def init_db():
    global conn
    if conn is None:
        conn = sqlite3.connect(LINK_DB, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        init_tables()


def init_tables():
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER,
            type TEXT,  -- 'group' or 'date'
            value TEXT
        )
    ''')
    conn.commit()


def get_connection():
    if conn is None:
        init_db()
    return conn


def get_user_values(user_id, type_):
    """Выборка данных"""
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_data WHERE user_id=? AND type=?", (user_id, type_))
    return [row[0] for row in cursor.fetchall()]


def add_value(user_id, type_, value):
    """Добавление значения"""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_data (user_id, type, value) VALUES (?, ?, ?)", (user_id, type_, value))
    conn.commit()


def remove_value(user_id, type_, value):
    """Удаление значения"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_data WHERE user_id=? AND type=? AND value=?", (user_id, type_, value))
    conn.commit()
