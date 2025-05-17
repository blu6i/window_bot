from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType

import sql
from bot.keyboards import get_inline_key_list, get_inline_key_add_info
from bot.states import MenuStates


async def show_groups(event: Union[CallbackQuery, Message], state: FSMContext):
    """Вывод групп пользователя"""
    u_id = event.from_user.id
    u_groups = sql.get_user_groups(u_id)

    text = "👥 У вас пока нет добавленных групп." if not u_groups else "👥 Ваши группы:\nНажмите на группу для удаления"
    keyboard = get_inline_key_list(u_id, "group")

    # Обработка отправки в зависимости от типа события
    if isinstance(event, CallbackQuery):
        sent = await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        sent = await event.answer(text, reply_markup=keyboard)

    await state.update_data(last_msg=sent.message_id)
    await state.set_state(MenuStates.GROUP_EDIT.state)


async def add_group(msg: types.Message, state: FSMContext):
    """Обработка команды добавления группы через название"""
    group = msg.text.strip()
    u_id = msg.from_user.id
    u_groups = sql.get_user_groups(u_id)
    # Получение ИД последнего сообщения с кнопками
    data = await state.get_data()
    # 1. Проверка: пользователь ввел ПОЛНУЮ группу
    """if group.lower() in sql.get_all_groups():
        if group in u_groups:
            await msg.answer(f"⚠️ Группа «{group}» уже добавлена.")
        else:
            sql.add_user_group(u_id, group)
            await msg.answer(f"✅ Группа «{group}» добавлена!")
        await refresh_groups_message(msg, state, u_id)"""

    # 2. Проверка: это факультет/институт/специальность?
    if sql.is_check_entity(group):
        # Нашли сущность — выводим все группы по факультету/институту
        groups = sql.get_groups(group)
        await state.update_data(found_groups=groups)
        await state.update_data(actual_data=group)
        # Генерация клавиатуры добавления групп
        keyboard = get_inline_key_add_info(u_id, group, 'groups')
        await msg.answer("📚 Выберите группы для добавления:", reply_markup=keyboard)
    else:
        # 3. Ничего не найдено вообще
        text = f"⚠️ Неверно указана информация или её нет в базе."
        await refresh_groups_message(msg, state, u_id, text)


async def refresh_groups_message(msg, state, user_id, text: str = ""):
    """Обновить сообщение со списком групп"""
    u_groups = sql.get_user_groups(user_id)
    if not u_groups:
        sent = await msg.answer("👥 У вас пока нет добавленных групп.\n"
                                "\n"
                                f"{text}",
                                reply_markup=get_inline_key_list(user_id, "group"))
    else:
        sent = await msg.answer("👥 Ваши группы:\nНажмите на них для удаления\n"
                                "\n"
                                f"{text}",
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
        text = "👥 Ваши группы:\nНажмите на группу для удаления"
    elif data.startswith("prev_page_group_"):
        page = int(data.split("_")[-1])
        text = "👥 Ваши группы:\nНажмите на группу для удаления"

    # Обновление сообщения
    await call.message.edit_text(text,
                                 reply_markup=get_inline_key_list(u_id, "group", page))

    await state.update_data(page_group=page)
    await call.answer()


def register_groups_handlers(dp: Dispatcher):
    # Меню групп
    dp.register_callback_query_handler(
        show_groups,
        lambda c: c.data == "menu_groups" and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_message_handler(
        show_groups,
        commands=["groups"],
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state="*"
    )
    # Навигация
    dp.register_callback_query_handler(
        list_user_groups,
        lambda c: ('next_page_' in c.data or 'prev_page_' in c.data) and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Удаление групп
    dp.register_callback_query_handler(
        list_user_groups,
        lambda c: (c.data.startswith('-') or c.data == "clear_all_group") and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.GROUP_EDIT
    )
    # Добавление групп
    dp.register_message_handler(
        add_group,
        lambda m: not m.text.startswith('/'),
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state=MenuStates.GROUP_EDIT
    )
