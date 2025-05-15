from typing import Union

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType

from bot import get_main_menu

HELP_TEXT = ("<b>Основные функции:</b>\n"
             "🪟 <b>Окна в расписании</b> - поиск свободного времени\n"
             "👥 <b>Управление группами</b> - управление своим списком групп\n"
             "📅 <b>Управление датами</b> - управление своим списком дат\n"
             "<b>Ссылки быстрого доступа:</b>\n"
             "📅 Бот ВятГУ - ссылка на официального бота ВятГУ\n"
             "📌 ЛК ВятГУ - ссылка на личный кабинет ВятГУ\n"
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

# Не актуально

async def send_help(event: Union[CallbackQuery, Message], state: FSMContext):
    """Обработка /help или кнопки ℹ️ Помощь"""
    u_id = event.from_user.id

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(HELP_TEXT, parse_mode="HTML")
        menu_msg = await event.message.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                              reply_markup=get_main_menu(u_id),
                                              parse_mode="HTML")
    else:
        await event.answer(HELP_TEXT, parse_mode="HTML")  # Показываем помощь
        menu_msg = await event.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                      reply_markup=get_main_menu(u_id),
                                      parse_mode="HTML")

    await state.update_data(last_msg=menu_msg.message_id)


def register_help_handlers(dp: Dispatcher):
    # Вывод помощи через команду (! Переделать)
    dp.register_message_handler(send_help,
                                commands=["help"],
                                chat_type=ChatType.PRIVATE,
                                state='*')
    # Вывод помощи
    dp.register_callback_query_handler(send_help,
                                       lambda c: c.data == "help" and c.message.chat.type == ChatType.PRIVATE,
                                       state='*')
