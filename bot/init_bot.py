import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from utils import logger

_bot = None
_dp = None


def get_bot():
    global _bot
    if _bot is None:
        try:
            load_dotenv('../config/.env')
            TOKEN = os.getenv('BOT_TOKEN')
            _bot = Bot(token=TOKEN)
            logger.info(f'Бот инициализирован')
        except Exception as e:
            logger.warning(f'Ошибка при инициализации бота: {e}')
    return _bot

def get_dp():
    global _dp
    if _dp is None:
        try:
            storage = MemoryStorage()
            _dp = Dispatcher(get_bot(), storage=storage)
            logger.info(f'Бот инициализирован')
        except Exception as e:
            logger.warning(f'Ошибка при инициализации бота: {e}')
    return _dp
