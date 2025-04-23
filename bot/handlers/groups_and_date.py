from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list
from bot.states import MenuStates
from sql import get_user_values, add_value, remove_value, is_check_entity, get_groups


async def show_groups(message: types.Message, state: FSMContext):
    """Вывод групп"""
    user_id = message.from_user.id
    # Получение групп из бд юзера
    groups = get_user_values(user_id, "group")
    # Удаляем предыдущее сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass
    # Проверка что список не пуст
    if not groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:",
                                    reply_markup=get_inline_key_list(groups, "group"))
    # Сохраняем ласт сообщение
    await state.update_data(last_groups_msg=sent.message_id)
    await state.set_state(MenuStates.GROUP_EDIT.state)


async def add_group(message: types.Message, state: FSMContext):
    """Обработка добавления группы"""
    group = message.text[1:].strip()
    if not group:
        return
    user_id = message.from_user.id
    # Получаем группы из бд
    current_groups = get_user_values(user_id, "group")
    # Проверка на дубликаты
    if group in current_groups:
        await message.answer(f"⚠️ Группа «{group}» уже добавлена.")
        return
    if not is_check_entity(group):
        await message.answer(f"⚠️ Неверно указана информация или её нет в базе")
        return
    groups = get_groups(group)
    list_group = []
    for g in groups:
        # Запись в бд
        add_value(user_id, "group", g)
        list_group.append(g)
    res = '\n'.join(list_group)
    await message.answer(f"✅ Список пополнен\n: {res}")
    # Удаляем предыдущее сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass
    # Обновляем сообщение и отправляем
    updated_groups = get_user_values(user_id, "group")
    sent = await message.answer("👥 Ваши группы:",
                                reply_markup=get_inline_key_list(updated_groups, "group"))
    await state.update_data(last_groups_msg=sent.message_id)


async def remove_group(message: types.Message, state: FSMContext):
    """Обработка удаления группы"""
    group = message.text[1:].strip()
    if not group:
        return
    user_id = message.from_user.id
    current_groups = get_user_values(user_id, "group")
    # Проверка группы в списке
    if group not in current_groups:
        await message.answer(f"⚠️ Группа «{group}» не найдена в списке.")
        return
    # Удаляем из бд
    remove_value(user_id, "group", group)
    await message.answer(f"❌ Группа «{group}» удалена.")
    # Удаляем предыдущее сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass
    # Выводим сообщение с новой информацией
    updated_groups = get_user_values(user_id, "group")
    if not updated_groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:",
                                    reply_markup=get_inline_key_list(updated_groups, "group"))
    await state.update_data(last_groups_msg=sent.message_id)


async def group_callback(call: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн кнопки для группы"""
    user_id = call.from_user.id
    data = call.data
    # Удаление группы
    if data.startswith("-"):
        group = data[1:]
        current_groups = get_user_values(user_id, "group")
        if group in current_groups:
            remove_value(user_id, "group", group)
            await call.answer(f"❌ Группа «{group}» удалена.")
        else:
            await call.answer(f"⚠️ Группа «{group}» не найдена.",
                              show_alert=True)
    # Очистка групп
    elif data == "clear_all_group":
        for group in get_user_values(user_id, "group"):
            remove_value(user_id, "group", group)
        await call.answer("🧹 Все группы удалены.")
    # Обновление сообщения с группами
    groups = get_user_values(user_id, "group")
    if not groups:
        await call.message.edit_text("👥 У вас пока нет добавленных групп.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(groups, "group"))


async def show_dates(message: types.Message, state: FSMContext):
    """Вывод дат"""
    user_id = message.from_user.id
    dates = get_user_values(user_id, "date")
    # Удаляем предыдущее сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass
    # Проверка на пустой список
    if not dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:",
                                    reply_markup=get_inline_key_list(dates, "date"))
    # Сохраняем ласт сообщение
    await state.update_data(last_dates_msg=sent.message_id)
    await state.set_state(MenuStates.DATE_EDIT.state)


async def add_date(message: types.Message, state: FSMContext):
    text = message.text[1:].strip()
    if not text:
        return
    # Преобразование даты
    try:
        if len(text.split(".")) == 1:
            day = int(text)
            month = datetime.now().month
            year = datetime.now().year
        elif len(text.split(".")) == 2:
            day, month = map(int, text.split("."))
            year = datetime.now().year
        else:
            day, month, year = map(int, text.split("."))
        date_obj = datetime(year, month, day)
        date_str = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        await message.answer("⚠️ Некорректный формат даты. Используйте DD.MM или DD.MM.YYYY")
        return

    user_id = message.from_user.id
    current_dates = get_user_values(user_id, "date")
    # Проверка на дубликаты
    if date_str in current_dates:
        await message.answer(f"⚠️ Дата {date_str} уже добавлена.")
        return
    # Запись в Бд
    add_value(user_id, "date", date_str)
    await message.answer(f"✅ Дата {date_str} добавлена.")
    # Удаляем предыдущее сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass

    updated_dates = get_user_values(user_id, "date")
    sent = await message.answer("📅 Ваши даты:",
                                reply_markup=get_inline_key_list(updated_dates, "date"))
    await state.update_data(last_dates_msg=sent.message_id)


async def remove_date(message: types.Message, state: FSMContext):
    """Обработка удаления даты"""
    date_input = message.text[1:].strip()
    if not date_input:
        return
    # Трансформация даты
    try:
        if len(date_input.split(".")) == 1:
            day = int(date_input)
            month = datetime.now().month
            year = datetime.now().year
        elif len(date_input.split(".")) == 2:
            day, month = map(int, date_input.split("."))
            year = datetime.now().year
        else:
            day, month, year = map(int, date_input.split("."))
        date_obj = datetime(year, month, day)
        date_str = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        await message.answer("⚠️ Некорректный формат даты. Используйте DD.MM или DD.MM.YYYY")
        return

    user_id = message.from_user.id
    current_dates = get_user_values(user_id, "date")
    # Проверка на присутствие даты
    if date_str not in current_dates:
        await message.answer(f"⚠️ Дата {date_str} не найдена в списке.")
        return
    remove_value(user_id, "date", date_str)
    await message.answer(f"❌ Дата {date_str} удалена.")
    # Удаление предыдущего сообщения
    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        try:
            await message.bot.edit_message_reply_markup(chat_id=message.chat.id,
                                                        message_id=last_msg_id,
                                                        reply_markup=None)
        except:
            pass
    # Вывод сообщения
    updated_dates = get_user_values(user_id, "date")
    if not updated_dates:
        sent = await message.answer("📅 У вас пока нет добавленных дат.")
    else:
        sent = await message.answer("📅 Ваши даты:",
                                    reply_markup=get_inline_key_list(updated_dates, "date"))
    await state.update_data(last_dates_msg=sent.message_id)


async def date_callback(call: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн кнопок с датами"""
    user_id = call.from_user.id
    data = call.data

    if data.startswith("-"):
        date_str = data[1:]
        current_dates = get_user_values(user_id, "date")
        if date_str in current_dates:
            remove_value(user_id, "date", date_str)
            await call.answer(f"❌ Дата {date_str} удалена.")
        else:
            await call.answer(f"⚠️ Дата {date_str} не найдена.", show_alert=True)

    elif data == "clear_all_date":
        for date in get_user_values(user_id, "date"):
            remove_value(user_id, "date", date)
        await call.answer("🧹 Все даты удалены.")

    dates = get_user_values(user_id, "date")
    if not dates:
        await call.message.edit_text("📅 У вас пока нет добавленных дат.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(dates, "date"))


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
