import os

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

import bot
from sql import get_connection, build_sql
from utils import logger

# Инициализация бота, диспетчера
load_dotenv('config/.env')
TOKEN = os.getenv('BOT_TOKEN')
_bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(_bot, storage=storage)


# Регистрируем все хендлеры
bot.register_add_groups_handlers(dp)
bot.register_add_teachers_handlers(dp)
bot.register_windows_list_handlers(dp)
bot.register_edit_meet_handlers(dp)
bot.register_authorization_handlers(dp)
bot.register_groups_handlers(dp)
bot.register_teachers_handlers(dp)
bot.register_date_handlers(dp)
bot.register_search_handlers(dp)
bot.register_link_handlers(dp)
bot.register_common_handlers(dp)
bot.register_help_handlers(dp)

# Запуск
if __name__ == "__main__":
    conn = get_connection()
    build_sql()
    try:
        executor.start_polling(dp, skip_updates=True)
    finally:
        conn.close()
        logger.info('Соединение закрыто')
