from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot import get_main_menu
from utils import logger

WELCOME_TEXT = ("Добро пожаловать в бота для поиска свободных окон в расписании групп!\n"
                "\n"
                "<b>🧭 Быстрый старт</b>\n"
                "\n"
                "Для поиска свободных окон нужно добавить <b>минимум одну группу И одну дату</b>.\n"
                "\n"
                "<b>👥 Добавление группы</b> — перейдите в <u>«Управление группами»</u> и введите:\n"
                "• <b>Название института (Сокращенное).</b> <i>Например:</i> <code>ИМИС</code>\n"
                "• <b>Название факультета (Сокращенное).</b> <i>Например:</i> <code>ФАВТ</code>\n"
                "• <b>Название направления (Сокращенное).</b> <i>Например:</i> <code>ИВТ</code>\n"
                "• <b>Группа:</b> <i>Например:</i> <code>ИВТб-1305-05-00</code>\n"
                "\n"
                "<b>📅 Добавление даты</b> — перейдите в <u>«Управление датами»</u> и введите:\n"
                "• <i>Например:</i> <code>21</code>, <code>21.04</code> или <code>21.04.2025</code>\n"
                "<i>Формат: DD, DD.\u200BMM или DD.MM.YYYY</i>\n"
                "\n"
                "Дополнительная информация — в разделе ℹ️ <b>Помощь</b>."
                )


async def remove_keyboard(bot, chat_id, message_id):
    """Удаляет сообщение с кнопками"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f'Ошибка при удалении сообщение с кнопками {e}')


async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.finish()
    sent = await call.message.edit_text("🏠 Главное меню\n\nВыберите нужный раздел",
                                        reply_markup=get_main_menu(call.from_user.id))
    await state.update_data(last_msg=sent.message_id)
    await call.answer()


async def cmd_start(msg: types.Message, state: FSMContext):
    """Обработка команды /start"""
    data = await state.get_data()
    last_msg_id = data.get('last_msg')
    await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
    await msg.answer(WELCOME_TEXT,
                     reply_markup=ReplyKeyboardRemove(),
                     parse_mode='HTML')
    msg = await msg.answer('🏠 Главное меню\n\nВыберите нужный раздел',
                           reply_markup=get_main_menu(msg.from_user.id))
    await state.update_data(last_msg=msg.message_id)


def register_common_handlers(dp: Dispatcher):
    # Возврат в главное меню
    dp.register_callback_query_handler(back_to_main,
                                       lambda c: c.data == "back_to_menu",
                                       state="*")
    # Обработка команды /start
    dp.register_message_handler(cmd_start,
                                commands=["start"],
                                state="*")
