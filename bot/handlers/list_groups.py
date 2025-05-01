from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

import sql
from bot.handlers.common import remove_keyboard
from bot.keyboards import get_inline_key_list, get_inline_key_add_groups
from bot.states import MenuStates


async def show_groups(call: types.CallbackQuery, state: FSMContext):
    """Вывод групп пользователя"""
    u_id = call.from_user.id
    u_groups = sql.get_user_groups(u_id)

    if not u_groups:
        sent = await call.message.edit_text("👥 У вас пока нет добавленных групп.",
                                            reply_markup=get_inline_key_list(u_id, "group"))
    else:
        sent = await call.message.edit_text("👥 Ваши группы:\nНажмите на них для удаления",
                                            reply_markup=get_inline_key_list(u_id, "group"))

    await state.update_data(last_msg=sent.message_id)
    await state.set_state(MenuStates.GROUP_EDIT.state)
    await call.answer()


async def add_group(msg: types.Message, state: FSMContext):
    """Обработка команды добавления группы через название"""
    group = msg.text.strip()
    u_id = msg.from_user.id
    u_groups = sql.get_user_groups(u_id)
    # Получение ИД последнего сообщения с кнопками
    data = await state.get_data()
    last_msg_id = data.get('last_msg')
    # 1. Проверка: пользователь ввел ПОЛНУЮ группу
    if group in sql.get_all_groups():
        if group in u_groups:
            await msg.answer(f"⚠️ Группа «{group}» уже добавлена.")
        else:
            sql.add_user_group(u_id, group)
            await msg.answer(f"✅ Группа «{group}» добавлена!")
        await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
        await refresh_groups_message(msg, state, u_id)

    # 2. Проверка: это факультет/институт/специальность?
    elif sql.is_check_entity(group):
        # Нашли сущность — выводим все группы по факультету/институту
        groups = sql.get_groups(group)
        await state.update_data(found_groups=groups)
        await state.update_data(actual_data=group)
        # Генерация клавиатуры добавления групп
        keyboard = get_inline_key_add_groups(u_id, group)
        await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
        await msg.answer("📚 Выберите группы для добавления:", reply_markup=keyboard)
    else:
        # 3. Ничего не найдено вообще
        await msg.answer(f"⚠️ Неверно указана информация или её нет в базе.")


async def refresh_groups_message(msg, state, user_id):
    """Обновить сообщение со списком групп"""
    u_groups = sql.get_user_groups(user_id)
    if not u_groups:
        sent = await msg.answer("👥 У вас пока нет добавленных групп.",
                                reply_markup=get_inline_key_list(user_id, "group"))
    else:
        sent = await msg.answer("👥 Ваши группы:\nНажмите на них для удаления",
                                reply_markup=get_inline_key_list(user_id, "group"))

    await state.update_data(last_msg=sent.message_id)


async def list_user_groups(call: types.CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопок для групп"""
    u_id = call.from_user.id
    data = call.data

    # Получаем данные состояния
    state_data = await state.get_data()
    page = state_data.get("page_group", 0)
    text = "👥 У вас пока нет добавленных групп."

    # Обработка удаления группы
    if data.startswith("-"):
        group = data[1:]
        group_name = sql.get_group_name(group)
        sql.remove_user_group(u_id, group)
        text = f"❌ Группа «{group_name}» удалена."

    # Обработка удаления всех групп
    elif data == "clear_all_group":
        sql.remove_all_user_groups(u_id)
        page = 0  # Сброс на первую страницу
        text = "🧹 Все группы удалены."

    # Обработка переключения страниц
    elif data.startswith("next_page_group_"):
        page = int(data.split("_")[-1])
    elif data.startswith("prev_page_group_"):
        page = int(data.split("_")[-1])

    # Обновление сообщения
    await call.message.edit_text(text,
                                 reply_markup=get_inline_key_list(u_id, "group", page))

    await state.update_data(page_group=page)
    await call.answer()


def register_groups_handlers(dp: Dispatcher):
    # Навигация
    dp.register_callback_query_handler(list_user_groups,
                                       lambda c: 'next_page_' in c.data or 'prev_page_' in c.data,
                                       state=MenuStates.GROUP_EDIT)
    # Удаление групп
    dp.register_callback_query_handler(list_user_groups,
                                       lambda c: c.data.startswith('-') or c.data == "clear_all_group",
                                       state=MenuStates.GROUP_EDIT)
    # Вывод меню
    dp.register_callback_query_handler(show_groups,
                                       lambda c: c.data == "menu_groups",
                                       state="*")
    # Вывод меню через команду (!Переделать)
    dp.register_message_handler(show_groups,
                                commands=["list_groups"],
                                state="*")
    # Добавление групп
    dp.register_message_handler(add_group,
                                lambda m: not m.text.startswith('/'),
                                state=MenuStates.GROUP_EDIT)
