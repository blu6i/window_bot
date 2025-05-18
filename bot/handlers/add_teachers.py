from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ChatType

import sql
from bot import MenuStates
from bot.keyboards import get_inline_key_add_info, get_inline_key_list
from utils import logger


async def callback_add_teacher(call: types.CallbackQuery, state: FSMContext):
    """Добавление преподавателя по ID"""
    try:
        u_id = call.from_user.id
        teacher_id = call.data[len("add_teachers_"):]
        teacher_name = sql.get_teacher_name(teacher_id)
        sql.add_user_teacher(u_id, teacher_name)
        text = f"✅ Преподаватель «{teacher_name}» добавлен!"

        await state.update_data(message=text)
        await refresh_add_teacher_message(call, state, u_id)
    except Exception as e:
        logger.warning(f'Ошибка при добавлении преподавателя по кнопке: {e}')
    finally:
        await call.answer()


async def callback_del_teachers(call: types.CallbackQuery, state: FSMContext):
    """Удаление преподавателя"""
    try:
        u_id = call.from_user.id
        teacher_id = call.data[len("del_teachers_"):]
        teacher_name = sql.get_teacher_name(teacher_id)

        sql.remove_user_teacher(u_id, teacher_name)
        text = f"❌ Преподаватель «{teacher_name}» удалён."

        await state.update_data(message=text)
        await refresh_add_teacher_message(call, state, u_id)
    except Exception as e:
        logger.warning(f'Проблема при отмене добавленного преподавателя: {e}')
    finally:
        await call.answer()


async def callback_add_all_teachers(call: types.CallbackQuery, state: FSMContext):
    """Добавление всех преподавателей из подразделения"""
    try:
        u_id = call.from_user.id
        u_teachers = sql.get_user_teachers(u_id)
        data = await state.get_data()
        teachers = data.get('found_teachers', [])
        for teacher in teachers:
            if teacher['id'] not in u_teachers:
                sql.add_user_teacher(u_id, teacher['name'])

        actual_data = data.get('actual_data')
        keyboard = get_inline_key_add_info(u_id, actual_data, 'teachers')
        await call.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logger.warning(f'Проблема при добавлении всех групп из подразделения: {e}')
    finally:
        await call.answer()


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
    finally:
        await call.answer()


async def callback_change_add_page(call: types.CallbackQuery, state: FSMContext):
    """Смена страниц в меню добавления преподавателей"""
    try:
        data = await state.get_data()
        teachers = data.get('found_teachers', [])
        page = data.get('found_page', 0)

        if "prev_page_add_" in call.data:
            page = max(0, page - 1)
        elif "next_page_add_" in call.data:
            page = min(len(teachers) // 10, page + 1)

        await state.update_data(found_page=page)
        await refresh_add_teacher_message(call, state, call.from_user.id)
    except Exception as e:
        logger.warning(f'Проблема со сменной страницы в меню преподавателями: {e}')
    finally:
        await call.answer()


async def refresh_add_teacher_message(event: Union[types.Message, types.CallbackQuery],
                                      state: FSMContext, user_id: int):
    """Обновляет сообщение с меню выбора преподавателей для добавления"""
    try:
        data = await state.get_data()
        page = data.get('found_page', 0)
        text = data.get('message', '🎓 Выберите преподавателя:')
        sub_text = data.get('sub_message', '')
        teachers = data.get('actual_data')

        keyboard = get_inline_key_add_info(user_id, teachers, "teachers", page)

        if isinstance(event, types.Message):
            await event.answer(f"{sub_text}\n"
                               f"\n"
                               f"{text}", reply_markup=keyboard)
        else:
            await event.message.edit_text(f"{sub_text}\n"
                                          f"\n"
                                          f"{text}", reply_markup=keyboard)
    except Exception as e:
        logger.warning(f'Проблема с обновлениями меню с преподавателями: {e}')
    finally:
        if isinstance(event, types.CallbackQuery):
            await event.answer()


def register_add_teachers_handlers(dp: Dispatcher):
    # Добавление одной группы
    dp.register_callback_query_handler(
        callback_add_teacher,
        lambda c: c.data.startswith("add_teachers_") and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Добавление всех групп
    dp.register_callback_query_handler(
        callback_add_all_teachers,
        lambda c: c.data == "add_all_teachers" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Отмена добавления
    dp.register_callback_query_handler(
        callback_del_teachers,
        lambda c: c.data.startswith('del_teachers_') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Навигация
    dp.register_callback_query_handler(
        callback_change_add_page,
        lambda c: "prev_page_add_" in c.data or "next_page_add_" in c.data and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Возврат в меню групп
    dp.register_callback_query_handler(
        callback_back_to_teachers,
        lambda c: c.data == "back_to_teachers" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
