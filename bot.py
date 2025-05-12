from aiogram import executor

import bot
from sql import get_connection, build_sql
from utils import logger

dp = bot.init_bot.get_dp()

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

bot.register_groups_chat_handlers(dp)

# Запуск
if __name__ == "__main__":
    conn = get_connection()
    build_sql()
    try:
        executor.start_polling(dp, skip_updates=True)
    finally:
        conn.close()
        logger.info('Соединение закрыто')
