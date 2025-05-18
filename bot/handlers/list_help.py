from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ChatType

from bot import get_main_menu
from bot.handlers.remove_test import update_new_msg

HELP_TEXT_PRIVATE = ("<b>Основные функции:</b>\n"
                     "🪟 <b>Окна в расписании</b> - поиск свободного времени\n"
                     "👥 <b>Группы</b> - управление своим списком групп\n"
                     "📅 <b>Даты</b> - управление своим списком дат\n"
                     "\n"
                     "<b>Как добавить группу?</b>\n"
                     "1. Перейти в нужный раздел\n"
                     "2. Ввести соответствующее наименование:\n"
                     "- Вывод групп института\n"
                     "Напишите: <code>НазваниеИнститута (Сокращенное)</code>\n"
                     "Например*: <code>ИМИС</code>\n"
                     "\n"
                     "- Вывод групп факультета\n"
                     "Напишите: <code>НазваниеФакультета (Сокращенное)</code>\n"
                     "Например*: <code>ФАВТ</code> \n"
                     "\n"
                     "- Вывод групп специальности:\n"
                     "Напишите: <code>НазваниеСпециальности (Сокращенное)</code>\n"
                     "Например*: <code>ИВТ</code>\n"
                     "\n"
                     "- Добавление отдельной группы:\n"
                     "Напишите: <code>НазваниеГруппы</code>\n"
                     "Например*: <code>ИВТб-1305-05-00</code>\n"
                     "\n"
                     "<b>Как удалить группу?</b>\n"
                     "1. Перейти в нужный раздел\n"
                     "2. Нажать на нужную группу для удаления\n"
                     "\n"
                     "<b>Как добавить преподавателя?</b>\n"
                     "1. Перейти в раздел 'Преподаватели'\n"
                     "2. Ввести соответствующее наименование:\n"
                     "- Вывод преподавателей института\n"
                     "Напишите: <code>НазваниеИнститута (Сокращенное)</code>\n"
                     "Например*: <code>ИМИС</code>\n"
                     "\n"
                     "- Вывод преподавателей факультета\n"
                     "Напишите: <code>НазваниеФакультета (Сокращенное)</code>\n"
                     "Например*: <code>ФАВТ</code> \n"
                     "\n"
                     "- Вывод преподавателей кафедры:\n"
                     "Напишите: <code>НазваниеКафедры (Сокращенное)</code>\n"
                     "Например*: <code>БМ</code>\n"
                     "\n"
                     "- Добавление отдельного преподавателей:\n"
                     "Напишите: <code>Фамилия И.О.</code>\n"
                     "Например*: <code>Голиков Р.В.</code>\n"
                     "\n"
                     "<b>Как удалить преподавателя?</b>\n"
                     "1. Перейти в нужный раздел\n"
                     "2. Нажать на нужную группу для удаления\n"
                     "\n"
                     "<b>Как добавить дату?</b>\n"
                     "1. Перейти в нужный раздел\n"
                     "2. Ввести нужную дату:\n"
                     "- Для добавления группы\n"
                     "Напишите: <code>Дата*</code>\n"
                     "Например: <code>21.04</code>\n"
                     "\n"
                     "<i>* - Формат даты: DD, DD.\u200BMM или DD.MM.YYYY</i>\n"
                     "\n"
                     "<b>Как удалить дату?</b>\n"
                     "1. Перейти в нужный раздел\n"
                     "2. Нажать на нужную дату для удаления\n"
                     "\n"
                     "<a href='teletype.in/@pepegeshka/sFjYdnH8AVG'>Ссылка на подробный гайд (Кликабельно)</a>")


HELP_TEXT_PUBLIC = ("ℹ️ Как привязать беседу группы к боту?\n"
                    "– Введите `!код` [пароль]\n"
                    "\n"
                    "ℹ️ Как узнать назначенные встречи группе?\n"
                    "– Введите `!встречи`")


async def send_help_public(msg: Message):
    await msg.answer(HELP_TEXT_PUBLIC, parse_mode="Markdown")


async def send_help(msg: Message, state: FSMContext):
    """Обработка /help"""
    u_id = msg.from_user.id
    sent = None
    try:
        await msg.answer(HELP_TEXT_PRIVATE, parse_mode="HTML")
        sent = await msg.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                reply_markup=get_main_menu(u_id),
                                parse_mode="HTML")
    finally:
        await update_new_msg(msg.chat.id, sent, state)


def register_help_handlers(dp: Dispatcher):
    # Вывод помощи через команду (! Переделать)
    dp.register_message_handler(send_help_public,
                                commands=["help"],
                                chat_type=[ChatType.SUPERGROUP, ChatType.GROUP],
                                content_types=types.ContentTypes.TEXT,
                                state="*")
    dp.register_message_handler(send_help,
                                commands=["help"],
                                chat_type=ChatType.PRIVATE,
                                content_types=types.ContentTypes.TEXT,
                                state='*')
