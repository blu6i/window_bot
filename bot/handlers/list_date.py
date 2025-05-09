from datetime import datetime
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import get_inline_key_list
from bot.states import MenuStates
from sql import add_user_date, get_user_dates, remove_user_date, remove_all_user_dates, is_date_in_schedule
from utils import logger


async def show_dates(event: Union[CallbackQuery, Message], state: FSMContext):
    """Вывод дат пользователя"""
    u_id = event.from_user.id
    u_dates = get_user_dates(u_id)

    if not u_dates:
        text = "📅 У вас пока нет добавленных дат."
    else:
        text = "📅 Ваши даты:\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY"

    keyboard = get_inline_key_list(u_id, "date")

    if isinstance(event, CallbackQuery):
        sent = await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        sent = await event.answer(text, reply_markup=keyboard)

    await state.update_data(last_msg=sent.message_id)
    await state.set_state(MenuStates.DATE_EDIT.state)


'''async def show_dates(call: types.CallbackQuery, state: FSMContext):
    """Вывод дат пользователя"""
    u_id = call.from_user.id
    u_dates = get_user_dates(u_id)
    # Проверка на наличия дат
    if not u_dates:
        sent = await call.message.edit_text("📅 У вас пока нет добавленных дат.",
                                            reply_markup=get_inline_key_list(u_id, "date"))
    else:
        sent = await call.message.edit_text("📅 Ваши даты:"
                                            "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                            reply_markup=get_inline_key_list(u_id, "date"))

    await state.update_data(last_msg=sent.message_id)
    await state.set_state(MenuStates.DATE_EDIT.state)
    await call.answer()'''


async def add_date(msg: types.Message, state: FSMContext):
    """Добавление даты с проверкой наличия даты в расписании"""
    u_id = msg.from_user.id
    text = msg.text.strip()
    data = await state.get_data()
    last_msg_id = data.get('last_msg')
    # Преобразование в формат для БД
    try:
        date = date_format_db(text)
    except ValueError:
        await msg.bot.edit_message_text("⚠️ Некорректный формат даты или такой даты не существует в календаре. "
                                        "\n\nФормат даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                        chat_id=msg.chat.id,
                                        message_id=last_msg_id,
                                        reply_markup=get_inline_key_list(u_id, "date")
                                        )
        return

    # Проверка: есть ли вообще такая дата в БД расписания
    if not is_date_in_schedule(date):
        await msg.bot.edit_message_text(f"⚠️ На {date} нет расписания.",
                                        chat_id=msg.chat.id,
                                        message_id=last_msg_id,
                                        reply_markup=get_inline_key_list(u_id, "date")
                                        )
        return

    u_id = msg.from_user.id
    u_dates = get_user_dates(u_id)

    if date in u_dates:
        await msg.bot.edit_message_text(f"⚠️ Дата {date} уже добавлена.",
                                        chat_id=msg.chat.id,
                                        message_id=last_msg_id,
                                        reply_markup=get_inline_key_list(u_id, "date")
                                        )
        return

    add_user_date(u_id, date)
    await msg.bot.edit_message_text(f"✅ Дата {date} добавлена.",
                                    chat_id=msg.chat.id,
                                    message_id=last_msg_id,
                                    reply_markup=get_inline_key_list(u_id, "date")
                                    )
    await state.update_data(last_msg=last_msg_id)


async def del_date(call: types.CallbackQuery, state: FSMContext):
    """Инлайн-кнопки для дат"""
    u_id = call.from_user.id
    data = call.data
    text = "📅 У вас пока нет добавленных дат."
    # Удаление
    if data.startswith("-"):
        date_str = data[1:]
        remove_user_date(u_id, date_str)
        text = f"❌ Дата {date_str} удалена."

    # Очистка
    elif data == "clear_all_date":
        remove_all_user_dates(u_id)
        text = "🧹 Все даты удалены."

    # Вывод
    u_dates = get_user_dates(u_id)
    if not u_dates:
        await call.message.edit_text(f"{text}\n\nФормат для добавления дат: DD, DD.\u200BMM или DD.MM.YYYY",
                                     reply_markup=get_inline_key_list(u_id, "date"))
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(u_id, "date"))
    await call.answer()


async def refresh_dates_message(msg, state, user_id):
    """Обновить сообщение со списком дат"""
    u_dates = get_user_dates(user_id)
    if not u_dates:
        sent = await msg.answer("📅 У вас пока нет добавленных дат.",
                                reply_markup=get_inline_key_list(user_id, "date"))
    else:
        sent = await msg.answer("📅 Ваши даты:"
                                "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                reply_markup=get_inline_key_list(user_id, "date"))

    await state.update_data(last_dates_msg=sent.message_id)


def date_format_db(text: str) -> str:
    """Преобразование строки вида DD, DD.MM, DD.MM.YYYY в YYYY-MM-DD с учетом перехода на следующий месяц"""
    today = datetime.now()
    try:
        parts = list(map(int, text.split(".")))
    except ValueError as e:
        logger.error(f'Ошибка при преобразовании в формат БД: {e}')
        raise

    if len(parts) == 1:
        # Если только день указан
        day = parts[0]
        month = today.month
        year = today.year
        try:
            temp_date = datetime(year, month, day)
            if temp_date.date() < today.date():
                # День уже прошел в этом месяце -> следующий месяц
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
        except ValueError:
            # День не существует в этом месяце (например 31 февраля), пробуем следующий месяц
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
    elif len(parts) == 2:
        # День и месяц
        day, month = parts
        year = today.year
    else:
        # День, месяц и год
        day, month, year = parts

    date_obj = datetime(year, month, day)
    return date_obj.strftime("%Y-%m-%d")


def register_date_handlers(dp: Dispatcher):
    # Меню с датами
    dp.register_callback_query_handler(show_dates,
                                       lambda c: c.data == 'menu_dates',
                                       state="*")
    dp.register_message_handler(show_dates,
                                commands=['dates'],
                                state="*")
    # Добавление даты
    dp.register_message_handler(add_date,
                                lambda m: not m.text.startswith('/'),
                                state=MenuStates.DATE_EDIT)
    # Удаление даты
    dp.register_callback_query_handler(del_date,
                                       lambda c: c.data.startswith("-") or c.data == 'clear_all_date',
                                       state=MenuStates.DATE_EDIT)
