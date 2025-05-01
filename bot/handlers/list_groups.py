from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.handlers.utils import remove_keyboard
from bot.keyboards import get_inline_key_list, get_inline_key_add_groups
from bot.states import MenuStates
from sql import get_all_groups, add_user_group, get_user_groups, get_groups, \
    is_check_entity, \
    remove_user_group, remove_all_user_groups, get_group_name, get_group_id


async def show_groups(message: types.Message, state: FSMContext):
    """Вывод групп пользователя"""
    user_id = message.from_user.id
    groups = get_user_groups(user_id)

    # Удаляем старое сообщение
    data = await state.get_data()
    last_msg_id = data.get("last_dates_msg")
    if last_msg_id:
        # logger.info(last_msg_id)
        await remove_keyboard(message.bot, message.chat.id, last_msg_id)
        await state.update_data(last_dates_msg=None)
    last_msg_id = data.get("last_groups_msg")
    if last_msg_id:
        # logger.info(last_msg_id)
        await remove_keyboard(message.bot, message.chat.id, last_msg_id)
        await state.update_data(last_groups_msg=None)

    if not groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:\nНажмите на них для удаления",
                                    reply_markup=get_inline_key_list(user_id, "group"))

    await state.update_data(last_groups_msg=sent.message_id)
    await state.set_state(MenuStates.GROUP_EDIT.state)


async def add_group(message: types.Message, state: FSMContext):
    """Обработка команды добавления группы через название"""
    group = message.text.strip()
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
    if is_check_entity(group):
        # Нашли сущность — выводим все группы по факультету/институту
        groups = get_groups(group)

        if not groups:
            await message.answer("⚠️ Oops..\nКажется, такого нет")
            return

        await state.update_data(found_groups=groups)
        await state.update_data(actual_data=group)

        keyboard = get_inline_key_add_groups(user_id, group)  # генерация клавиатуры добавления групп
        if len(keyboard['inline_keyboard']) == 1:
            await message.answer("❗ Нет доступных групп для добавления.", reply_markup=keyboard)
        else:
            await message.answer("📚 Выберите группы для добавления:", reply_markup=keyboard)
        return

    else:
        # 3. Ничего не найдено вообще
        await message.answer(f"⚠️ Неверно указана информация или её нет в базе.")


async def refresh_groups_message(message, state, user_id):
    """Обновить сообщение со списком групп"""
    groups = get_user_groups(user_id)
    if not groups:
        sent = await message.answer("👥 У вас пока нет добавленных групп.")
    else:
        sent = await message.answer("👥 Ваши группы:\nНажмите на них для удаления",
                                    reply_markup=get_inline_key_list(user_id, "group"))

    await state.update_data(last_groups_msg=sent.message_id)


async def callback_remove_groups(call: types.CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопок для групп"""
    user_id = call.from_user.id
    data = call.data

    # Получаем текущие группы и данные состояния
    groups = get_user_groups(user_id)
    state_data = await state.get_data()
    page = state_data.get("page_group", 0)

    # Обработка удаления группы
    if data.startswith("-"):
        group = data[1:]
        group_name = get_group_name(group)
        if int(group) in groups:
            remove_user_group(user_id, group)
            await call.answer(f"❌ Группа «{group_name}» удалена.")
        else:
            await call.answer(f"⚠️ Группа «{group_name}» не найдена.", show_alert=True)

    # Обработка удаления всех групп
    elif data == "clear_all_group":
        remove_all_user_groups(user_id)
        await call.answer("🧹 Все группы удалены.")
        page = 0  # Сброс на первую страницу

    # Обработка переключения страниц
    elif data.startswith("next_page_group_"):
        page = int(data.split("_")[-1])
    elif data.startswith("prev_page_group_"):
        page = int(data.split("_")[-1])

    # Проверка наличия групп у пользователя
    groups = get_user_groups(user_id)
    if not groups:
        await call.message.edit_text("👥 У вас пока нет добавленных групп.")
    else:
        await call.message.edit_reply_markup(reply_markup=get_inline_key_list(user_id, "group", page))

    await state.update_data(page_group=page)


def register_groups_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(callback_remove_groups,
                                       lambda m: 'next_page_' in m.data or 'prev_page_' in m.data,
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_remove_groups,
                                       lambda c: c.data.startswith('-') or c.data == "clear_all_group",
                                       state=MenuStates.GROUP_EDIT)
    dp.register_message_handler(show_groups,
                                text="👥 Изменить группы",
                                state="*")
    dp.register_message_handler(show_groups,
                                text="👥 Добавить группы",
                                state="*")
    dp.register_message_handler(show_groups,
                                commands=["list_groups"],
                                state="*")

    #dp.register_message_handler(add_group,
    #                            lambda m: m.text.startswith('+'),
    #                            state=MenuStates.GROUP_EDIT)

    dp.register_message_handler(add_group,
                                state=MenuStates.GROUP_EDIT)
