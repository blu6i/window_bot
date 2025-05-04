from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot import get_main_menu
from bot.handlers.common import remove_keyboard

HELP_TEXT = ("<b>Основные функции:</b>\n"
             "🪟 <b>Окна в расписании</b> - поиск свободного времени\n"
             "👥 <b>Управление группами</b> - управление своим списком групп\n"
             "📅 <b>Управление датами</b> - управление своим списком дат\n"
             "<b>Ссылки быстрого доступа:</b>\n"
             "📅 Официальный бот ВятГУ - ссылка на официального бота ВятГУ\n"
             "📌 Личный кабинет ВятГУ - ссылка на личный кабинет ВятГУ\n"
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
             "2. Нажать на нужную дату для удаления")


async def send_help(call: types.CallbackQuery, state: FSMContext):
    """ Обработка ввода команды /help """
    data = await state.get_data()
    last_msg_id = data.get('last_msg')
    await remove_keyboard(call.message.bot, call.message.chat.id, last_msg_id)
    await call.message.answer(HELP_TEXT,
                              parse_mode="HTML")
    last_msg = await call.message.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                         reply_markup=get_main_menu(call.from_user.id),
                                         parse_mode='HTML')
    await state.update_data(last_msg=last_msg.message_id)
    await call.answer()


def register_help_handlers(dp: Dispatcher):
    # Вывод помощи через команду (!Переделать)
    dp.register_message_handler(send_help,
                                commands=["help"],
                                state='*')
    # Вывод помощи
    dp.register_callback_query_handler(send_help,
                                       lambda c: c.data == "help",
                                       state='*')
