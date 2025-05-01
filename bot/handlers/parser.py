from aiogram import types, Dispatcher
from sql import remove_schedule
from parser import groups_web_parse

LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'


async def update_db(message: types.Message):
    await message.answer('⏳ Запуск парсинга...')
    try:
        remove_schedule()
        groups_web_parse(LINK)
        await message.answer(f'✅ Парсинг завершен')
    except Exception as e:
        await message.answer(f'⚠️ Ошибка при парсинге\n{e}')


def register_parser_handlers(dp: Dispatcher):
    # Запуск парсера
    dp.register_callback_query_handler(update_db,
                                       lambda c: c.data == "refresh_schedule",
                                       state='*')
