from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list
from bot.states import MenuStates
from sql import add_user_date, add_user_group, get_user_groups, get_user_dates, get_groups, is_check_entity, \
    remove_user_group, remove_user_date, remove_all_user_dates, remove_all_user_groups, is_date_in_schedule


async def show_groups(message: types.Message, state: FSMContext):
    """Вывод групп пользователя"""
    user_id = message.from_user.id
    groups = get_user_groups(user_id)

    # Удаляем старое сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        await safe_remove_keyboard(message.bot, message.chat.id, last_msg_id)

    if not groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:", reply_markup=get_inline_key_list(groups, "group"))

    await state.update_data(last_groups_msg=sent.message_id)
    await state.set_state(MenuStates.GROUP_EDIT.state)


async def add_group(message: types.Message, state: FSMContext):
    """Добавление новой группы"""
    group = message.text[1:].strip()
    if not group:
        return

    user_id = message.from_user.id
    current_groups = get_user_groups(user_id)

    if group in current_groups:
        await message.answer(f"⚠️ Группа «{group}» уже добавлена.")
        return

    if not is_check_entity(group):
        await message.answer(f"⚠️ Неверно указана информация или её нет в базе.")
        return

    groups = get_groups(group)
    list_group = []
    for g in groups:
        add_user_group(user_id, g)
        list_group.append(g)

    res = '\n'.join(list_group)
    await message.answer(f"✅ Список пополнен:\n{res}")

    await refresh_groups_message(message, state, user_id)


async def remove_group(message: types.Message, state: FSMContext):
    """Удаление группы"""
    group = message.text[1:].strip()
    if not group:
        return

    user_id = message.from_user.id
    current_groups = get_user_groups(user_id)

    if group not in current_groups:
        await message.answer(f"⚠️ Группа «{group}» не найдена в списке.")
        return

    remove_user_group(user_id, group)
    await message.answer(f"❌ Группа «{group}» удалена.")

    await refresh_groups_message(message, state, user_id)


async def group_callback(call: types.CallbackQuery, state: FSMContext):
    """Инлайн-кнопки для групп"""
    user_id = call.from_user.id
    data = call.data

    groups = get_user_groups(user_id)
    state_data = await state.get_data()
    page = state_data.get("page_group", 0)

    if data.startswith("-"):
        group = data[1:]
        if group in groups:
            remove_user_group(user_id, group)
            await call.answer(f"❌ Группа «{group}» удалена.")
        else:
            await call.answer(f"⚠️ Группа «{group}» не найдена.", show_alert=True)

    elif data == "clear_all_group":
        remove_all_user_groups(user_id)
        await call.answer("🧹 Все группы удалены.")
        page = 0  # сбрасываем на первую страницу

    elif data.startswith("next_page_group_"):
        page = int(data.split("_")[-1])

    elif data.startswith("prev_page_group_"):
        page = int(data.split("_")[-1])

    groups = get_user_groups(user_id)
    if not groups:
        await call.message.edit_text("👥 У вас пока нет добавленных групп.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(groups, "group", page))

    await state.update_data(page_group=page)



async def show_dates(message: types.Message, state: FSMContext):
    """Вывод дат пользователя"""
    user_id = message.from_user.id
    dates = get_user_dates(user_id)

    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        await safe_remove_keyboard(message.bot, message.chat.id, last_msg_id)

    if not dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:"
                                    "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                    reply_markup=get_inline_key_list(dates, "date"))

    await state.update_data(last_dates_msg=sent.message_id)
    await state.set_state(MenuStates.DATE_EDIT.state)


async def add_date(message: types.Message, state: FSMContext):
    """Добавление даты с проверкой наличия даты в расписании"""
    text = message.text[1:].strip()
    if not text:
        return

    try:
        date_str = format_to_db(text)
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

    try:
        date_str = format_to_db(text)
    except ValueError:
        await message.answer("⚠️ Некорректный формат даты или такой даты не существует в календаре. "
                             "\n\nФормат даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY", parse_mode=None)
        return

    user_id = message.from_user.id
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

    if data.startswith("-"):
        date_str = data[1:]
        current_dates = get_user_dates(user_id)

        if date_str in current_dates:
            remove_user_date(user_id, date_str)
            await call.answer(f"❌ Дата {date_str} удалена.")
        else:
            await call.answer(f"⚠️ Дата {date_str} не найдена.", show_alert=True)

    elif data == "clear_all_date":
        remove_all_user_dates(user_id)
        await call.answer("🧹 Все даты удалены.")

    dates = get_user_dates(user_id)
    if not dates:
        await call.message.edit_text("📅 У вас пока нет добавленных дат.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(dates, "date"))


async def safe_remove_keyboard(bot, chat_id, message_id):
    """Безопасно удаляет клавиатуру у сообщения"""
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    except:
        pass


async def refresh_groups_message(message, state, user_id):
    """Обновить сообщение со списком групп"""
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        await safe_remove_keyboard(message.bot, message.chat.id, last_msg_id)

    groups = get_user_groups(user_id)
    if not groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:", reply_markup=get_inline_key_list(groups, "group"))

    await state.update_data(last_groups_msg=sent.message_id)


async def refresh_dates_message(message, state, user_id):
    """Обновить сообщение со списком дат"""
    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        await safe_remove_keyboard(message.bot, message.chat.id, last_msg_id)

    dates = get_user_dates(user_id)
    if not dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:"
                                    "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                    reply_markup=get_inline_key_list(dates, "date"))

    await state.update_data(last_dates_msg=sent.message_id)


def format_to_db(text: str) -> str:
    """Преобразование строки вида DD, DD.MM, DD.MM.YYYY в YYYY-MM-DD с учетом перехода на следующий месяц"""
    from datetime import datetime
    today = datetime.now()

    parts = list(map(int, text.split(".")))

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


def register_group_handlers(dp: Dispatcher):
    """Регистрация хендлеров"""
    dp.register_message_handler(show_groups, text="👥 Изменить группы", state="*")
    dp.register_message_handler(add_group, lambda m: m.text.startswith('+'), state=MenuStates.GROUP_EDIT)
    dp.register_message_handler(remove_group, lambda m: m.text.startswith('-'), state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(group_callback, lambda c: True, state=MenuStates.GROUP_EDIT)
    dp.register_message_handler(show_groups, commands=["list_groups"], state='*')

    dp.register_message_handler(show_dates, text="📅 Изменить даты", state="*")
    dp.register_message_handler(show_dates, commands=["list_dates"], state='*')
    dp.register_message_handler(add_date, lambda m: m.text.startswith('+'), state=MenuStates.DATE_EDIT)
    dp.register_message_handler(remove_date, lambda m: m.text.startswith('-'), state=MenuStates.DATE_EDIT)
    dp.register_callback_query_handler(date_callback, lambda c: True, state=MenuStates.DATE_EDIT)
