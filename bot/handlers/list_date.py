from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list
from bot.states import MenuStates
from sql import add_user_date, get_user_dates, remove_user_date, remove_all_user_dates, is_date_in_schedule

from bot.handlers.utils import remove_keyboard, date_format_db


async def show_dates(message: types.Message, state: FSMContext):
    """Вывод дат пользователя"""
    user_id = message.from_user.id
    dates = get_user_dates(user_id)

    # Удаление предыдущего сообщения с кнопками
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        await remove_keyboard(message.bot, message.chat.id, last_msg_id)
        await state.update_data(last_groups_msg=None)
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        await remove_keyboard(message.bot, message.chat.id, last_msg_id)
        await state.update_data(last_dates_msg=None)

    # Проверка на наличия дат
    if not dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:"
                                    "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                    reply_markup=get_inline_key_list(user_id, "date"))

    await state.update_data(last_dates_msg=sent.message_id)
    await state.set_state(MenuStates.DATE_EDIT.state)


async def add_date(message: types.Message, state: FSMContext):
    """Добавление даты с проверкой наличия даты в расписании"""
    text = message.text[1:].strip()
    if not text:
        return
    # Преобразование в формат для БД
    try:
        date_str = date_format_db(text)
    except ValueError:
        await message.answer("⚠️ Некорректный формат даты или такой даты не существует в календаре. "
                             "\n\nФормат даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY", parse_mode=None)
        return

    # Проверка: есть ли вообще такая дата в БД расписания
    if not is_date_in_schedule(date_str):
        await message.answer(f"⚠️ На {date_str} нет расписания.")
        return

    user_id = message.from_user.id
    current_dates = get_user_dates(user_id)

    if date_str in current_dates:
        await message.answer(f"⚠️ Дата {date_str} уже добавлена.")
        return

    add_user_date(user_id, date_str)
    await message.answer(f"✅ Дата {date_str} добавлена.")

    await refresh_dates_message(message, state, user_id)


async def remove_date(message: types.Message, state: FSMContext):
    """Удаление даты"""
    text = message.text[1:].strip()
    if not text:
        return
    # Преобразование даты в формат БД
    try:
        date_str = date_format_db(text)
    except ValueError:
        await message.answer("⚠️ Некорректный формат даты или такой даты не существует в календаре. "
                             "\n\nФормат даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY", parse_mode=None)
        return

    user_id = message.from_user.id

    # Проверка на наличие даты у юзера
    current_dates = get_user_dates(user_id)
    if date_str not in current_dates:
        await message.answer(f"⚠️ Дата {date_str} не найдена в списке.")
        return

    remove_user_date(user_id, date_str)
    await message.answer(f"❌ Дата {date_str} удалена.")

    await refresh_dates_message(message, state, user_id)


async def date_callback(call: types.CallbackQuery, state: FSMContext):
    """Инлайн-кнопки для дат"""
    user_id = call.from_user.id
    data = call.data
    # Удаление
    if data.startswith("-"):
        date_str = data[1:]
        current_dates = get_user_dates(user_id)

        if date_str in current_dates:
            remove_user_date(user_id, date_str)
            await call.answer(f"❌ Дата {date_str} удалена.")
        else:
            await call.answer(f"⚠️ Дата {date_str} не найдена.", show_alert=True)
    # Очистка
    elif data == "clear_all_date":
        remove_all_user_dates(user_id)
        await call.answer("🧹 Все даты удалены.")

    # Вывод
    dates = get_user_dates(user_id)
    if not dates:
        await call.message.edit_text("📅 У вас пока нет добавленных дат.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(user_id, "date"))


async def refresh_dates_message(message, state, user_id):
    """Обновить сообщение со списком дат"""
    dates = get_user_dates(user_id)
    if not dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:"
                                    "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                    reply_markup=get_inline_key_list(user_id, "date"))

    await state.update_data(last_dates_msg=sent.message_id)


def register_date_handlers(dp: Dispatcher):
    dp.register_message_handler(show_dates,
                                text="📅 Изменить даты",
                                state="*")
    dp.register_message_handler(show_dates,
                                text="📅 Добавить даты",
                                state="*")
    dp.register_message_handler(show_dates,
                                commands=["list_dates"],
                                state='*')
    dp.register_message_handler(add_date,
                                lambda m: m.text.startswith('+'),
                                state=MenuStates.DATE_EDIT)
    dp.register_message_handler(remove_date,
                                lambda m: m.text.startswith('-'),
                                state=MenuStates.DATE_EDIT)
    dp.register_callback_query_handler(date_callback,
                                       lambda c: True,
                                       state=MenuStates.DATE_EDIT)