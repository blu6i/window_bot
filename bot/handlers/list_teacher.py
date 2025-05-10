from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

import sql
from bot import get_inline_key_list, MenuStates
from bot.handlers.common import remove_keyboard


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
    """Добавление преподавателя по ФИО"""
    name = msg.text.strip()
    u_id = msg.from_user.id
    u_teachers = sql.get_user_teachers(u_id)
    data = await state.get_data()
    last_msg_id = data.get('last_msg')

    if name in sql.get_all_teachers():
        if name in u_teachers:
            await msg.answer(f"⚠️ Преподаватель «{name}» уже добавлен.")
        else:
            sql.add_user_teacher(u_id, name)
            await msg.answer(f"✅ Преподаватель «{name}» добавлен!")
        await remove_keyboard(msg.bot, msg.chat.id, last_msg_id)
        await show_teachers(msg, state)
    else:
        await msg.answer(f"⚠️ Преподаватель «{name}» не найден.")


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
        sql.remove_user_teacher(u_id, teacher)
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


def register_teachers_handlers(dp: Dispatcher):
    # Меню групп
    dp.register_callback_query_handler(show_teachers,
                                       lambda c: c.data == "menu_teachers",
                                       state="*")
    dp.register_message_handler(show_teachers,
                                commands=["groups"],
                                state="*")
    # Навигация
    dp.register_callback_query_handler(list_user_teachers,
                                       lambda c: 'next_page_' in c.data or 'prev_page_' in c.data,
                                       state=MenuStates.TEACHER_EDIT)
    # Удаление групп
    dp.register_callback_query_handler(list_user_teachers,
                                       lambda c: c.data.startswith('-') or c.data == "clear_all_teacher",
                                       state=MenuStates.TEACHER_EDIT)
    # Добавление групп
    dp.register_message_handler(add_teacher,
                                lambda m: not m.text.startswith('/'),
                                state=MenuStates.TEACHER_EDIT)
