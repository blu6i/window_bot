from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

import sql
from bot import MenuStates
from bot.keyboards import get_inline_key_add_info, get_inline_key_list
from utils import logger


async def callback_add_teacher(call: types.CallbackQuery, state: FSMContext):
    """Добавление преподавателя по ID"""
    u_id = call.from_user.id
    teacher_id = call.data[len("add_teachers_"):]
    teacher_name = sql.get_teacher_name(teacher_id)
    sql.add_user_teacher(u_id, teacher_name)
    text = f"✅ Преподаватель «{teacher_name}» добавлен!"

    await state.update_data(message=text)
    await refresh_add_teacher_message(call, state, u_id)


async def callback_del_teachers(call: types.CallbackQuery, state: FSMContext):
    """Удаление преподавателя"""
    u_id = call.from_user.id
    teacher_id = call.data[len("del_teachers_"):]
    teacher_name = sql.get_teacher_name(teacher_id)

    sql.remove_user_teacher(u_id, teacher_name)
    text = f"❌ Преподаватель «{teacher_name}» удалён."

    await state.update_data(message=text)
    await refresh_add_teacher_message(call, state, u_id)


async def callback_add_all_teachers(call: types.CallbackQuery, state: FSMContext):
    """Добавление всех преподавателей из подразделения"""
    u_id = call.from_user.id
    u_teachers = sql.get_all_teachers()
    data = await state.get_data()
    teachers = data.get('found_teachers', [])
    print(teachers)
    for teacher in teachers:
        if teacher not in u_teachers:
            sql.add_user_teacher(u_id, teacher['name'])

    actual_data = data.get('actual_data')
    keyboard = get_inline_key_add_info(u_id, actual_data, 'teachers')
    await call.message.edit_reply_markup(reply_markup=keyboard)


async def callback_back_to_teachers(call: types.CallbackQuery, state: FSMContext):
    try:
        u_id = call.from_user.id
        teachers = sql.get_user_teachers(u_id)

        if not teachers:
            await call.message.edit_text(
                "🎓 У вас пока нет добавленных преподавателей.",
                reply_markup=get_inline_key_list(u_id, "teacher")
            )
        else:
            await call.message.edit_text(
                "🎓 Ваши преподаватели:\nНажмите на преподавателя для удаления",
                reply_markup=get_inline_key_list(u_id, "teacher")
            )

        await state.update_data(last_msg=call.message.message_id)
        await state.set_state(MenuStates.TEACHER_EDIT.state)
        await call.answer()

    except Exception as e:
        logger.error(f'Ошибка при возврате в меню с преподавателями: {e}')


async def callback_change_add_page(call: types.CallbackQuery, state: FSMContext):
    """Смена страниц в меню добавления преподавателей"""
    data = await state.get_data()
    teachers = data.get('found_teachers', [])
    page = data.get('found_page', 0)

    if "prev_page_add_" in call.data:
        page = max(0, page - 1)
    elif "next_page_add_" in call.data:
        page = min(len(teachers) // 10, page + 1)

    await state.update_data(found_page=page)
    await refresh_add_teacher_message(call, state, call.from_user.id)


async def refresh_add_teacher_message(message_or_query: Union[types.Message, types.CallbackQuery],
                                      state: FSMContext, user_id: int):
    """Обновляет сообщение с меню выбора преподавателей для добавления"""
    data = await state.get_data()
    page = data.get('found_page', 0)
    text = data.get('message', '🎓 Выберите преподавателя:')
    teachers = data.get('actual_data')

    keyboard = get_inline_key_add_info(user_id, teachers, "teachers", page)

    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(text, reply_markup=keyboard)
    else:
        await message_or_query.message.edit_text(text, reply_markup=keyboard)


def register_add_teachers_handlers(dp: Dispatcher):
    # Добавление одной группы
    dp.register_callback_query_handler(callback_add_teacher,
                                       lambda c: c.data.startswith("add_teachers_"),
                                       state=MenuStates.TEACHER_EDIT)
    # Добавление всех групп
    dp.register_callback_query_handler(callback_add_all_teachers,
                                       lambda c: c.data == "add_all_teachers",
                                       state=MenuStates.TEACHER_EDIT)
    # Отмена добавления
    dp.register_callback_query_handler(callback_del_teachers,
                                       lambda c: c.data.startswith('del_teachers_'),
                                       state=MenuStates.TEACHER_EDIT)
    # Навигация
    dp.register_callback_query_handler(callback_change_add_page,
                                       lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data,
                                       state=MenuStates.TEACHER_EDIT)
    # Возврат в меню групп
    dp.register_callback_query_handler(callback_back_to_teachers,
                                       lambda c: c.data == "back_to_teachers",
                                       state=MenuStates.TEACHER_EDIT)
