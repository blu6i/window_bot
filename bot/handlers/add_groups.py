from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot.keyboards import get_inline_key_list, get_inline_key_add_info
from bot.states import MenuStates
from sql import add_user_group, get_user_groups, get_group_name, remove_user_group
from utils import logger


# Обработка меню с добавлением групп
async def callback_add_group(call: types.CallbackQuery, state: FSMContext):
    """Добавление групп"""
    u_id = call.from_user.id
    group_id = call.data[len("add_groups_"):]
    group = get_group_name(group_id)

    add_user_group(u_id, group)

    text = f"✅ Группа «{group}» добавлена!"
    await state.update_data(message=text)

    # Обновление клавиатуры после добавления
    await refresh_add_group_message(call, state, u_id)


async def callback_del_groups(call: types.CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопок для групп"""
    u_id = call.from_user.id

    # Получаем данные состояния
    state_data = await state.get_data()
    page = state_data.get("page_group", 0)

    # Обработка удаления группы
    group_id = call.data[len("add_groups_"):]
    group_name = get_group_name(group_id)
    remove_user_group(u_id, group_id)
    text = f"❌ Группа «{group_name}» удалена."

    # Обновляем клавиатуру с группами для текущей страницы
    await state.update_data(message=text)
    await state.update_data(page_group=page)
    await refresh_add_group_message(call, state, call.from_user.id)


async def callback_add_all_groups(call: types.CallbackQuery, state: FSMContext):
    """Добавление всех групп"""
    u_id = call.from_user.id
    data = await state.get_data()
    groups = data.get('found_groups', [])

    u_groups = get_user_groups(u_id)

    for group in groups:
        if group not in u_groups:
            add_user_group(u_id, group)
    data = data.get('actual_data')
    # После добавления обновляем сообщение с новой клавиатурой
    keyboard = get_inline_key_add_info(u_id, data, 'groups')
    await call.message.edit_reply_markup(reply_markup=keyboard)


async def callback_back_to_groups(call: types.CallbackQuery, state: FSMContext):
    """Возврат обратно в меню"""
    try:
        u_id = call.from_user.id
        u_groups = get_user_groups(u_id)
        # Редактирование меню с группами
        if not u_groups:
            await call.message.edit_text(
                "👥 У вас пока нет добавленных групп.",
                reply_markup=get_inline_key_list(u_id, "group")
            )
        else:
            await call.message.edit_text(
                "👥 Ваши группы:\nНажмите на группу для удаления",
                reply_markup=get_inline_key_list(u_id, "group")
            )

        # Обновляем состояние
        await state.update_data(last_msg=call.message.message_id)
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
    page = data.get('found_page', 0)
    text = data.get('message', '📚 Выберите группы для добавления:')
    data = data.get('actual_data')
    keyboard = get_inline_key_add_info(user_id, data, "groups", page)
    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(f"{text}", reply_markup=keyboard)
    else:
        await message_or_query.message.edit_text(f"{text}", reply_markup=keyboard)


def register_add_groups_handlers(dp: Dispatcher):
    # Добавление одной группы
    dp.register_callback_query_handler(callback_add_group,
                                       lambda c: c.data.startswith("add_groups_"),
                                       state=MenuStates.GROUP_EDIT)
    # Добавление всех групп
    dp.register_callback_query_handler(callback_add_all_groups,
                                       lambda c: c.data == "add_all_groups",
                                       state=MenuStates.GROUP_EDIT)
    # Отмена добавления
    dp.register_callback_query_handler(callback_del_groups,
                                       lambda c: c.data.startswith('del_groups_'),
                                       state=MenuStates.GROUP_EDIT)
    # Навигация
    dp.register_callback_query_handler(callback_change_add_page,
                                       lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data,
                                       state=MenuStates.GROUP_EDIT)
    # Возврат в меню групп
    dp.register_callback_query_handler(callback_back_to_groups,
                                       lambda c: c.data == "back_to_groups",
                                       state=MenuStates.GROUP_EDIT)
