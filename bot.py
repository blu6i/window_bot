import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from bot import register_group_handlers, get_main_menu, register_search_handlers, register_link_handlers, register_main_handlers
from sql import init_db, create_connection

# Инициализация бота, диспетчера
load_dotenv('config/.env')
TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
WELCOME_TEXT = '''   
Добро пожаловать в бота для нахождения свободных окон в расписании

Для помощи выберите соответствующую кнопку в меню ниже или введите: <code>/help</code>
'''


# Команда /start
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message):
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu(message.from_user.id), parse_mode='HTML')


# Регистрируем все хендлеры
register_group_handlers(dp)
register_search_handlers(dp)
register_link_handlers(dp)
register_main_handlers(dp)

# Запуск
if __name__ == "__main__":
    init_db()
    create_connection()
    executor.start_polling(dp, skip_updates=True)
