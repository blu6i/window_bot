from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType

import sql
from bot import get_inline_key_list, MenuStates
from bot.handlers.common import remove_keyboard
from bot.keyboards import get_inline_key_add_info


async def show_teachers(event: Union[CallbackQuery, Message], state: FSMContext):
    """Вывод преподавателей пользователя"""
    u_id = event.from_user.id
    u_teachers = sql.get_user_teachers(u_id)

    text = "👨‍🏫 У вас пока нет добавленных преподавателей." if not u_teachers else ("👨‍🏫 Ваши "
                                                                                    "преподаватели:\nНажмите на "
                                                                                    "преподавателя для удаления")
    keyboard = get_inline_key_list(u_id, "teacher")

    if isinstance(event, CallbackQuery):
        sent = await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        sent = await event.answer(text, reply_markup=keyboard)

    await state.update_data(last_msg=sent.message_id)
    await state.set_state(MenuStates.TEACHER_EDIT.state)


async def add_teacher(msg: types.Message, state: FSMContext):
    """Обработка команды добавления преподавателя через ФИО"""
    teacher = msg.text.strip()
    u_id = msg.from_user.id
    u_teachers = sql.get_user_teachers(u_id)
    last_msg_id = (await state.get_data()).get('last_msg')

    # 1. Точный поиск
    if teacher in sql.get_all_teachers():
        if teacher in u_teachers:
            await msg.answer(f"⚠️ Преподаватель «{teacher}» уже добавлен.")
        else:
            sql.add_user_teacher(u_id, teacher)
            await msg.answer(f"✅ Преподаватель «{teacher}» добавлен!")

        await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
        await refresh_teachers_message(msg, state, u_id)
        return

    # 2. Поиск по подразделению (институт, факультет, кафедра)
    if sql.is_check_sub(teacher):
        teachers = sql.get_teachers_sub(teacher)
        if not teachers:
            await msg.answer(f"⚠️ Нет преподавателей в '{teacher}'")
            return

        await state.update_data(found_teachers=teachers)
        await state.update_data(actual_data=teacher)
        keyboard = get_inline_key_add_info(u_id, teacher, 'teachers')
        await msg.answer("🎓 Выберите преподавателя для добавления:", reply_markup=keyboard)
        return

    # 3. Частичный поиск
    partial_matches = sql.find_teachers_part(teacher.lower())
    if partial_matches:
        await state.update_data(found_teachers=partial_matches)
        await state.update_data(actual_data=teacher)
        keyboard = get_inline_key_add_info(u_id, teacher, 'teachers')
        await msg.answer("🎓 Найдены похожие преподаватели:", reply_markup=keyboard)
        return

    # 4. Ничего не найдено
    await msg.answer(f"⚠️ Преподаватель «{teacher}» не найден.")


async def list_user_teachers(call: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн-кнопок преподавателей"""
    u_id = call.from_user.id
    data = call.data
    state_data = await state.get_data()
    page = state_data.get("page_teacher", 0)
    text = "👨‍🏫 У вас пока нет добавленных преподавателей."

    if data.startswith("-"):
        teacher = data[1:]
        name = sql.get_teacher_name(teacher)
        sql.remove_user_teacher(u_id, name)
        text = f"❌ Преподаватель «{name}» удалён."

    elif data == "clear_all_teacher":
        sql.remove_all_user_teachers(u_id)
        page = 0
        text = "🧹 Все преподаватели удалены."

    elif data.startswith("next_page_teacher_"):
        page = int(data.split("_")[-1])
        text = "👨‍🏫 Ваши преподаватели:\nНажмите на преподавателя для удаления"
    elif data.startswith("prev_page_teacher_"):
        page = int(data.split("_")[-1])
        text = "👨‍🏫 Ваши преподаватели:\nНажмите на преподавателя для удаления"

    await call.message.edit_text(text,
                                 reply_markup=get_inline_key_list(u_id, "teacher", page))

    await state.update_data(page_teacher=page)
    await call.answer()


async def refresh_teachers_message(msg: types.Message, state: FSMContext, user_id: int):
    """
    Обновить сообщение со списком преподавателей
    Args:
        msg: входящее сообщение от пользователя
        state: состояние FSM
        user_id: ID пользователя
    """
    u_teachers = sql.get_user_teachers(user_id)

    if not u_teachers:
        sent = await msg.answer("🎓 У вас пока нет добавленных преподавателей.",
                                reply_markup=get_inline_key_list(user_id, "teacher"))
    else:
        sent = await msg.answer("🎓 Ваши преподаватели:\nНажмите на преподавателя для удаления",
                                reply_markup=get_inline_key_list(user_id, "teacher"))

    # Сохраняем ID последнего сообщения
    await state.update_data(last_msg=sent.message_id)


def register_teachers_handlers(dp: Dispatcher):
    # Меню групп
    dp.register_callback_query_handler(show_teachers,
                                       lambda c: c.data == "menu_teachers" and c.message.chat.type == ChatType.PRIVATE,
                                       state="*")
    dp.register_message_handler(show_teachers,
                                commands=["groups"],
                                state="*")
    # Навигация
    dp.register_callback_query_handler(list_user_teachers,
                                       lambda c: ('next_page_' in c.data or 'prev_page_' in c.data) and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.TEACHER_EDIT)
    # Удаление групп
    dp.register_callback_query_handler(list_user_teachers,
                                       lambda c: (c.data.startswith('-') or c.data == "clear_all_teacher") and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.TEACHER_EDIT)
    # Добавление групп
    dp.register_message_handler(add_teacher,
                                lambda m: not m.text.startswith('/'),
                                chat_type=ChatType.PRIVATE,
                                state=MenuStates.TEACHER_EDIT)
