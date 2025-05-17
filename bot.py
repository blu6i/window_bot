from aiogram import Dispatcher, executor, types

import bot
from sql import get_connection, build_sql
from utils import logger

bot_ = bot.init_bot.get_bot()
dp = bot.init_bot.get_dp()


# === Команды ===
async def set_private_commands():
    await bot_.set_my_commands(
        commands=[
            types.BotCommand("start", "Запустить бота"),
            types.BotCommand("help", "Помощь")
        ],
        scope={"type": "all_private_chats"}
    )


async def set_groups_commands():
    await bot_.set_my_commands(
        commands=[
            types.BotCommand("help", "Помощь")
        ],
        scope={"type": "all_group_chats"}
    )


# === Регистрация хендлеров ===
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
bot.register_testing_handlers(dp)
bot.register_start_handlers(dp)
bot.register_groups_chat_handlers(dp)
bot.register_help_handlers(dp)


async def on_startup(dp: Dispatcher):
    """Инициализация бота"""
    build_sql()
    await set_private_commands()
    await set_groups_commands()
    logger.info("Бот запущен")


if __name__ == "__main__":
    conn = get_connection()
    try:
        executor.start_polling(
            dispatcher=dp,
            on_startup=on_startup,
            skip_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"]
        )
    except Exception as e:
        logger.error(f'Бот завершился ошибкой: {e}')
    finally:
        conn.close()
        logger.info("Соединение закрыто")
