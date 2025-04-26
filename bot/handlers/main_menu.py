from aiogram import types, Dispatcher

from bot.keyboards import get_main_menu
from parser import groups_web_parse
from sql import build_sql, remove_schedule

LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'

HELP_TEXT = """    
<b>Основные функции:</b>
🪟 <b>Окна в расписании</b> - поиск свободного времени
👥 <b>Изменить группы</b> - управление списком группами
📅 <b>Изменить группы</b> - управление списком дат
<b>Ссылки быстрого доступа:</b>
📅 Расписание - официальный бот ВятГУ с расписанием
📝 Отметка - система посещений
📌 ЛК - личный кабинет ВятГУ

<b>Как добавить группу?</b>
1. Перейти в нужный раздел
2. Ввести соответствующую команду:
- Добавление групп института
Напишите: <code>+НазваниеИнститута (Сокращенное)</code>
Например*: <code>+АТОД</code>

- Добавление групп факультета
Напишите: <code>+НазваниеФакультета (Сокращенное)</code>
Например*: <code>+БС</code> 

- Добавление групп специальности:
Напишите: <code>+НазваниеСпециальности (Сокращенное)</code>
Например*: <code>+КОТ</code>

- Добавление отдельной группы:
Напишите: <code>+НазваниеГруппы</code>
Например*: <code>+КОТб-1963-03-13</code>

<i>* - Пример взят из воздуха и не несет цели кого-либо оскорбить</i>

<b>Как удалить группу?</b>
Аналогично с добавлением, только вместо "+" следует писать "-"

<b>Как добавить дату?</b>
1. Перейти в нужный раздел
2. Ввести соответствующую команду:
- Для добавления группы
Напишите: <code>+Дата**</code>
Например: <code>+21.04</code>

<i>** - Формат даты: DD, DD.\u200BMM или DD.MM.YYYY</i>

<b>Как удалить дату?</b>
Аналогично с добавлением, только вместо "+" следует писать "-"
"""

LINK_SHEDULE = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'


async def send_help(message: types.Message):
    """ Обработка ввода команды /help """
    await message.answer(HELP_TEXT, reply_markup=get_main_menu(message.from_user.id), parse_mode='HTML')


async def update_db(message: types.Message):
    await message.answer('⏳ Запуск парсинга...')
    try:
        remove_schedule()
        groups_web_parse(LINK)
        await message.answer(f'✅ Парсинг завершен')
    except Exception as e:
        await message.answer(f'⚠️ Ошибка при парсинге\n{e}')


def register_main_handlers(dp: Dispatcher):
    dp.register_message_handler(send_help, commands=["help"], state='*')
    dp.register_message_handler(send_help, text='ℹ️ Помощь', state='*')
    dp.register_message_handler(update_db, text='🔄 Обновить расписание', state='*')
