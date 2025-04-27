from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list, get_inline_key_add_groups
from bot.states import MenuStates
from sql import get_all_groups, add_user_date, add_user_group, get_user_groups, get_user_dates, get_groups, \
    is_check_entity, \
    remove_user_group, remove_user_date, remove_all_user_dates, remove_all_user_groups, is_date_in_schedule, \
    find_like_groups


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
    """Обработка команды добавления группы через +название"""
    group = message.text[1:].strip()
    if not group:
        return

    user_id = message.from_user.id
    current_groups = get_user_groups(user_id)

    # 1. Проверка: пользователь ввел ПОЛНУЮ группу
    if group in get_all_groups():  # get_all_groups() — функция, возвращающая список всех групп из базы
        if group in current_groups:
            await message.answer(f"⚠️ Группа «{group}» уже добавлена.")
        else:
            add_user_group(user_id, group)
            await message.answer(f"✅ Группа «{group}» добавлена!")
        await refresh_groups_message(message, state, user_id)
        return

    # 2. Проверка: это факультет/институт/специальность?
    if is_check_entity(group):  # Эта функция должна проверить наличие сущности в отдельной таблице
        # Нашли сущность — выводим все группы по факультету/институту
        groups = get_groups(group)  # get_groups() — получить список групп по факультету/специальности

        if not groups:
            await message.answer("⚠️ Нет групп, связанных с этой сущностью.")
            return

        await state.update_data(found_groups=groups)

        keyboard = get_inline_key_add_groups(groups)  # генерация клавиатуры добавления групп
        await message.answer("📚 Выберите группы для добавления:", reply_markup=keyboard)
        return

    # 3. Если ничего не нашли — пробуем найти похожие группы
    similar_groups = find_like_groups(group)  # find_similar_groups() — искать похожие группы по подстроке

    if similar_groups:
        await state.update_data(found_groups=similar_groups)

        keyboard = get_inline_key_add_groups(similar_groups)
        await message.answer("🔍 Похожие группы найдены, выберите из списка:", reply_markup=keyboard)
    else:
        # 4. Ничего не найдено вообще
        await message.answer(f"⚠️ Неверно указана информация или её нет в базе.")


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


async def callback_remove_groups(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    data = call.data

    if data.startswith('-'):
        group_id = int(data[1:])  # Получаем ID группы из callback_data
        success = remove_user_group(user_id, group_id)

        if success:
            await call.answer(f"❌ Группа удалена")
            # Получаем обновлённый список групп
            groups = get_user_groups(user_id)
            if not groups:
                await call.message.edit_text("👥 У вас пока нет добавленных групп.")
            else:
                await call.message.edit_reply_markup(
                    reply_markup=get_inline_key_list(groups, "group")
                )
        else:
            await call.answer("⚠️ Не удалось удалить группу", show_alert=True)
        return


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


async def refresh_add_group_message(message_or_query: Union[types.Message, types.CallbackQuery], state: FSMContext,
                                    user_id: int):
    """Обновление сообщения с меню выбора групп для добавления"""
    data = await state.get_data()
    groups = data.get('found_groups', [])
    page = data.get('found_page', 0)

    if not groups:
        if isinstance(message_or_query, types.Message):
            await message_or_query.answer("❗ Нет доступных групп для добавления.")
        else:
            await message_or_query.message.edit_text("❗ Нет доступных групп для добавления.")
        return

    keyboard = get_inline_key_add_groups(groups, page=page)

    if isinstance(message_or_query, types.Message):
        await message_or_query.answer("Выберите группы для добавления:", reply_markup=keyboard)
    else:
        await message_or_query.message.edit_text("Выберите группы для добавления:", reply_markup=keyboard)


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


async def callback_add_group(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    group = callback_query.data[len("add_group_"):]

    data = await state.get_data()
    found_groups = data.get('found_groups', [])

    # Проверка, что группа доступна для добавления
    if group not in found_groups:
        await callback_query.answer("⚠️ Группа уже была добавлена или недоступна.", show_alert=True)
        return

    # Добавление группы в список пользователя
    current_groups = get_user_groups(user_id)
    if group in current_groups:
        await callback_query.answer(f"⚠️ Группа «{group}» уже добавлена.", show_alert=True)
        return

    add_user_group(user_id, group)

    # Убираем добавленную группу из списка найденных групп
    found_groups.remove(group)
    await state.update_data(found_groups=found_groups)

    await callback_query.answer(f"✅ Группа «{group}» добавлена!")

    # Обновление клавиатуры после добавления
    await refresh_add_group_message(callback_query, state, user_id)


async def callback_add_all_groups(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()
    groups = data.get('found_groups', [])

    if not groups:
        await callback_query.answer("❗ Нет доступных групп для добавления.", show_alert=True)
        return

    current_groups = get_user_groups(user_id)

    added_groups = []
    for group in groups:
        if group not in current_groups:
            add_user_group(user_id, group)
            added_groups.append(group)

    if added_groups:
        res = "\n".join(added_groups)
        await callback_query.answer(f"✅ Добавлены группы:\n{res}", show_alert=True)
    else:
        await callback_query.answer(f"⚠️ Все группы уже были добавлены.", show_alert=True)

    # Возвращаем пользователя обратно в основное меню групп
    await refresh_groups_message(callback_query.message, state, user_id)


async def callback_back_to_groups(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await refresh_groups_message(callback_query.message, state, user_id)


async def callback_change_add_page(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = data.get('found_groups', [])
    page = data.get('found_page', 0)

    # Проверка на наличие групп
    if not groups:
        await callback_query.answer("❗ Нет доступных групп для добавления.", show_alert=True)
        return

    # Обработка перехода на следующую/предыдущую страницу
    if "prev_page_add_" in callback_query.data:
        page = max(0, page - 1)
    elif "next_page_add_" in callback_query.data:
        page = min(len(groups) // 10, page + 1)  # Ограничиваем количество страниц (по 10 групп на страницу)

    # Обновление страницы в состоянии
    await state.update_data(found_page=page)

    # Обновляем клавиатуру с группами для текущей страницы
    await refresh_add_group_message(callback_query, state, callback_query.from_user.id)


def register_group_handlers(dp: Dispatcher):
    # Сначала регистрируем специфичные обработчики
    dp.register_callback_query_handler(callback_add_group, lambda c: c.data.startswith("add_group_"),
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_add_all_groups, lambda c: c.data == "add_all_groups",
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_change_add_page,
                                       lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data,
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_back_to_groups, lambda c: c.data == "back_to_groups",
                                       state=MenuStates.GROUP_EDIT)

    # Затем общие обработчики
    dp.register_callback_query_handler(callback_remove_groups, lambda c: c.data.startswith('-') or c.data == "clear_all_group",
                                       state=MenuStates.GROUP_EDIT)

    # Остальные обработчики
    dp.register_message_handler(show_groups, text="👥 Изменить группы", state="*")
    dp.register_message_handler(add_group, lambda m: m.text.startswith('+'), state=MenuStates.GROUP_EDIT)
    dp.register_message_handler(remove_group, lambda m: m.text.startswith('-'), state=MenuStates.GROUP_EDIT)
