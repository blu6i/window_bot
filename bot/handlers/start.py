from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatType

from bot.handlers.common import out_main_menu
from bot.handlers.testing_bot import send_test_auth_message


WELCOME_TEXT = ("Добро пожаловать в бота для поиска свободных окон в расписании групп!\n"
                "\n"
                "<b>🧭 Быстрый старт</b>\n"
                "\n"
                "Для поиска свободных окон нужно добавить <b>минимум одну группу И одну дату</b>.\n"
                "\n"
                "<b>👥 Добавление группы</b> — перейдите в <u>«Группы»</u> и введите: "
                "шифр группы или название подразделения университета\n"
                "ℹ️ <i>Например:</i> <code>ИВТб-1305-05-00</code> или <code>ИМИС</code>\n"
                "\n"
                "<b>📅 Добавление даты</b> — перейдите в <u>«Даты»</u> и введите дату.\n"
                "<i>Формат: DD, DD.\u200BMM или DD.MM.YYYY</i>\n"
                "ℹ️ <i>Например:</i> <code>16</code> или <code>16.05</code>\n"
                "\n"
                "<b>👨‍🏫 Добавление преподавателя</b> — перейдите в <u>«Преподаватели»</u> и введите: "
                "ФИО (Формат: Фамилия И.О.) преподавателя или название подразделения университета\n"
                "ℹ️ <i>Например:</i> <code>Долженкова М.Л.</code> или <code>ИМИС</code>\n"
                "\n"
                "Дополнительная информация — в разделе ℹ️ <b>Помощь</b>."
                )


async def cmd_start(msg: types.Message, state: FSMContext):
    """Обработка команды /start"""
    await msg.answer(WELCOME_TEXT,
                     reply_markup=ReplyKeyboardRemove(),
                     parse_mode='HTML')
    #await send_test_auth_message(msg)
    await out_main_menu(msg, state)


def register_start_handlers(dp: Dispatcher):
    # Обработка команды /start
    dp.register_message_handler(
        cmd_start,
        commands=["start"],
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state="*"
    )