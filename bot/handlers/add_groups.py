from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list, get_inline_key_add_groups
from bot.states import MenuStates
from sql import add_user_group, get_user_groups, get_group_name, remove_user_group
from utils import logger


# Обработка меню с добавлением групп
async def callback_add_group(call: types.CallbackQuery, state: FSMContext):
    """Добавление групп"""
    user_id = call.from_user.id
    group_id = call.data[len("add_group_"):]
    group = get_group_name(group_id)
    # data = await state.get_data()
    # found_groups = data.get('found_groups', [])

    add_user_group(user_id, group)

    # Убираем добавленную группу из списка найденных групп
    # found_groups.remove(group)
    # await state.update_data(found_groups=found_groups)
    text = f"✅ Группа «{group}» добавлена!"
    await state.update_data(message=text)
    # Обновление клавиатуры после добавления
    await refresh_add_group_message(call, state, user_id)


async def callback_del_groups(call: types.CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопок для групп"""
    user_id = call.from_user.id

    # Получаем данные состояния
    state_data = await state.get_data()
    page = state_data.get("page_group", 0)

    # Обработка удаления группы
    group_id = call.data[len("add_group_"):]
    group_name = get_group_name(group_id)
    remove_user_group(user_id, group_id)
    text = f"❌ Группа «{group_name}» удалена."

    # Обновляем клавиатуру с группами для текущей страницы
    await state.update_data(message=text)
    await state.update_data(page_group=page)
    await refresh_add_group_message(call, state, call.from_user.id)


async def callback_add_all_groups(call: types.CallbackQuery, state: FSMContext):
    """Добавление всех групп"""
    user_id = call.from_user.id
    data = await state.get_data()
    groups = data.get('found_groups', [])

    current_groups = get_user_groups(user_id)

    for group in groups:
        if group not in current_groups:
            add_user_group(user_id, group)
    data = data.get('actual_data')
    # После добавления обновляем сообщение с новой клавиатурой
    keyboard = get_inline_key_add_groups(user_id, data)
    if len(keyboard['inline_keyboard']) == 1:  # Если осталась только кнопка "Назад"
        await call.message.edit_text("✅ Все группы успешно добавлены!", reply_markup=keyboard)
    else:
        await call.message.edit_reply_markup(reply_markup=keyboard)


async def callback_back_to_groups(call: types.CallbackQuery, state: FSMContext):
    """Возврат обратно в меню"""
    try:
        user_id = call.from_user.id
        groups = get_user_groups(user_id)

        # Вывод меню с группами
        if not groups:
            await call.message.edit_text(
                "👥 У вас пока нет добавленных групп.",
                reply_markup=None
            )
        else:
            await call.message.edit_text(
                "👥 Ваши группы:\nНажмите на них для удаления",
                reply_markup=get_inline_key_list(user_id, "group")
            )

        # Обновляем состояние
        await state.update_data(last_groups_msg=call.message.message_id)
        await state.set_state(MenuStates.GROUP_EDIT.state)

        # Подтверждаем обработку callback
        await call.answer()

    except Exception as e:
        logger.error(f'Ошибка при возврате в меню с группами {e}')


async def callback_change_add_page(call: types.CallbackQuery, state: FSMContext):
    """Смена страниц у меню с добавлением групп"""
    data = await state.get_data()
    groups = data.get('found_groups', [])
    page = data.get('found_page', 0)

    # Обработка перехода на следующую/предыдущую страницу
    if "prev_page_add_" in call.data:
        page = max(0, page - 1)
    elif "next_page_add_" in call.data:
        page = min(len(groups) // 10, page + 1)  # Ограничиваем количество страниц (по 10 групп на страницу)

    # Обновление страницы в состоянии
    await state.update_data(found_page=page)

    # Обновляем клавиатуру с группами для текущей страницы
    await refresh_add_group_message(call, state, call.from_user.id)


async def refresh_add_group_message(message_or_query: Union[types.Message, types.CallbackQuery], state: FSMContext,
                                    user_id: int):
    """Обновление сообщения с меню выбора групп для добавления"""
    data = await state.get_data()
    # groups = data.get('found_groups', [])
    page = data.get('found_page', 0)
    text = data.get('message', '📚 Выберите группы для добавления:')
    # if not groups:
    #    if isinstance(message_or_query, types.Message):
    #        await message_or_query.answer("❗ Нет доступных групп для добавления.")
    #    else:
    #        await message_or_query.message.edit_text("❗ Нет доступных групп для добавления.")
    #    return
    data = data.get('actual_data')
    keyboard = get_inline_key_add_groups(user_id, data, page=page)

    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(f"{text}", reply_markup=keyboard)
    else:
        await message_or_query.message.edit_text(f"{text}", reply_markup=keyboard)


def register_add_groups_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(callback_add_group,
                                       lambda c: c.data.startswith("add_group_"),
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_add_all_groups,
                                       lambda c: c.data == "add_all_groups",
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_del_groups,
                                       lambda c: c.data.startswith('del_group_'),
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_change_add_page,
                                       lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data,
                                       state=MenuStates.GROUP_EDIT)
    dp.register_callback_query_handler(callback_back_to_groups,
                                       lambda c: c.data == "back_to_groups",
                                       state=MenuStates.GROUP_EDIT)
