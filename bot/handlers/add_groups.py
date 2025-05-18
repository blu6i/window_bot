from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ChatType

from bot.keyboards import get_inline_key_list, get_inline_key_add_info
from bot.states import MenuStates
from utils import logger
import sql

NULL_LIST = ("👥 Список групп пуст\n"
             "\n"
             "ℹ️ Введите шифр группы или название подразделения университета")

NO_NULL_LIST = ("ℹ️ Нажмите на группу, если нужно удалить\n"
                "\n"
                "👥 Ваши группы:")


# Обработка меню с добавлением групп
async def callback_add_group(call: types.CallbackQuery, state: FSMContext):
    """Добавление групп"""
    try:
        u_id = call.from_user.id
        group_id = call.data[len("add_groups_"):]
        group = sql.get_group_name(group_id)

        sql.add_user_group(u_id, group)

        text = f"✅ Группа «{group}» добавлена!"
        await state.update_data(message=text)

        # Обновление клавиатуры после добавления
        await refresh_add_group_message(call, state, u_id)
    except Exception as e:
        logger.warning(f'Проблема при добавлении групп с помощью кнопки: {e}')
    finally:
        await call.answer()


async def callback_del_groups(call: types.CallbackQuery, state: FSMContext):
    """Обработка отмены добавления для групп"""
    try:
        u_id = call.from_user.id

        # Получаем данные состояния
        state_data = await state.get_data()
        page = state_data.get("page_group", 0)

        # Обработка удаления группы
        group_id = call.data[len("add_groups_"):]
        group_name = sql.get_group_name(group_id)
        sql.remove_user_group(u_id, group_id)
        text = f"❌ Группа «{group_name}» удалена."

        # Обновляем клавиатуру с группами для текущей страницы
        await state.update_data(message=text)
        await state.update_data(page_group=page)
        await refresh_add_group_message(call, state, call.from_user.id)
    except Exception as e:
        logger.warning(f'Проблема при отмене добавленной группы: {e}')
    finally:
        await call.answer()


async def callback_add_all_groups(call: types.CallbackQuery, state: FSMContext):
    """Добавление всех групп"""
    try:
        u_id = call.from_user.id
        data = await state.get_data()
        groups = data.get('found_groups', [])

        u_groups = sql.get_user_groups(u_id)

        for group in groups:
            if group not in u_groups:
                sql.add_user_group(u_id, group)
        data = data.get('actual_data')
        # После добавления обновляем сообщение с новой клавиатурой
        keyboard = get_inline_key_add_info(u_id, data, 'groups')
        await call.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logger.warning(f'Проблема при добавлении всех групп: {e}')
    finally:
        await call.answer()


async def callback_back_to_groups(call: types.CallbackQuery, state: FSMContext):
    """Возврат обратно в меню"""
    try:
        u_id = call.from_user.id
        u_groups = sql.get_user_groups(u_id)
        # Редактирование меню с группами
        sub_text = NULL_LIST if not u_groups else NO_NULL_LIST
        await call.message.edit_text(f"{sub_text}\n",
                                     reply_markup=get_inline_key_list(u_id, "group"))

        # Обновляем состояние
        await state.update_data(last_msg=call.message.message_id)
        await state.set_state(MenuStates.GROUP_EDIT.state)
    except Exception as e:
        logger.error(f'Ошибка при возврате в меню с группами {e}')
    finally:
        await call.answer()


async def callback_change_add_page(call: types.CallbackQuery, state: FSMContext):
    """Смена страниц у меню с добавлением групп"""
    try:
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
    except Exception as e:
        logger.warning(f'Ошибка при смене страниц с группами: {e}')
    finally:
        await call.answer()


async def refresh_add_group_message(event: Union[types.Message, types.CallbackQuery], state: FSMContext,
                                    user_id: int):
    """Обновление сообщения с меню выбора групп для добавления"""
    try:
        data = await state.get_data()
        page = data.get('found_page', 0)
        text = data.get('message', '📚 Выберите группы для добавления:')
        sub_text = data.get('sub_message', '')
        data = data.get('actual_data')
        keyboard = get_inline_key_add_info(user_id, data, "groups", page)
        if isinstance(event, types.Message):
            await event.answer(f"{sub_text}\n"
                               f"\n"
                               f"{text}", reply_markup=keyboard)
        else:
            await event.message.edit_text(f"{sub_text}\n"
                                          f"\n"
                                          f"{text}", reply_markup=keyboard)
    except Exception as e:
        logger.warning(f'Проблема при обновлении сообщения с группами: {e}')
    finally:
        if isinstance(event, types.CallbackQuery):
            await event.answer()


def register_add_groups_handlers(dp: Dispatcher):
    # Добавление одной группы
    dp.register_callback_query_handler(
        callback_add_group,
        lambda c: c.data.startswith("add_groups_") and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Добавление всех групп
    dp.register_callback_query_handler(
        callback_add_all_groups,
        lambda c: c.data == "add_all_groups" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Отмена добавления
    dp.register_callback_query_handler(
        callback_del_groups,
        lambda c: c.data.startswith('del_groups_') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Навигация
    dp.register_callback_query_handler(
        callback_change_add_page,
        lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Возврат в меню групп
    dp.register_callback_query_handler(
        callback_back_to_groups,
        lambda c: c.data == "back_to_groups" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
