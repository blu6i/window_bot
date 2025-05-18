from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType

import sql
from bot import get_inline_key_list, MenuStates
from bot.handlers.add_teachers import refresh_add_teacher_message
from bot.keyboards import get_inline_key_add_info
from utils import logger

NULL_LIST = ("👨‍🏫 Список преподавателей пуст\n"
             "\n"
             "ℹ️ Введите ФИО преподавателя (Формат: Фамилия И.О.) или название подразделения университета")

NO_NULL_LIST = ("ℹ️ Нажмите на преподавателя, если нужно удалить\n"
                "\n"
                "👨‍🏫 Ваши группы:")


# =======[Меню с добавлением преподавателей]=======
async def show_teachers(event: Union[CallbackQuery, Message], state: FSMContext):
    """Вывод преподавателей пользователя"""
    try:
        u_id = event.from_user.id
        u_teachers = sql.get_user_teachers(u_id)

        text = NULL_LIST if not u_teachers else NO_NULL_LIST
        keyboard = get_inline_key_list(u_id, "teacher")

        if isinstance(event, CallbackQuery):
            sent = await event.message.edit_text(text, reply_markup=keyboard)
            await event.answer()
        else:
            sent = await event.answer(text, reply_markup=keyboard)
        await state.update_data(last_msg=sent.message_id)
        await state.set_state(MenuStates.TEACHER_EDIT.state)
    except Exception as e:
        logger.warning(f'Ошибка при выводе меню с преподавателями: {e}')
    finally:
        if isinstance(event, CallbackQuery):
            await event.answer()


async def add_teacher(msg: types.Message, state: FSMContext):
    """Обработка команды добавления преподавателя через ФИО"""
    try:
        teacher = msg.text.strip()
        u_id = msg.from_user.id
        u_teachers = sql.get_user_teachers(u_id)

        # 1. Точный поиск
        """if teacher.lower() in sql.get_all_teachers():
            if sql.get_teacher_id(teacher) in u_teachers:
                text = f"⚠️ Преподаватель «{teacher}» уже добавлен."
            else:
                sql.add_user_teacher(u_id, teacher)
                text = f"✅ Преподаватель «{teacher}» добавлен!"

            await refresh_teachers_message(msg, state, u_id, text)
            return"""

        """# 2. Поиск по подразделению (институт, факультет, кафедра)
        if sql.is_check_sub(teacher):
            teachers = sql.get_teachers_sub(teacher)
            if not teachers:
                return

            await state.update_data(found_teachers=teachers)
            await state.update_data(actual_data=teacher)
            keyboard = get_inline_key_add_info(u_id, teacher, 'teachers')
            await msg.answer("🎓 Выберите преподавателя для добавления:", reply_markup=keyboard)
            return"""
        teachers = sql.get_teachers_sub(teacher)
        teachers_name = teachers['teachers']
        teachers_name.sort()
        if teacher:
            await state.update_data(found_teachers=teachers_name)
            await state.update_data(actual_data=teacher)
            if teachers['code'] == 3:
                if len(teachers_name) == 1:
                    res = sql.add_user_teacher(u_id, teachers_name[0])
                    if res['flag']:
                        text = f"✅ Преподаватель «{sql.get_teacher_name(res['teacher_id'])}» добавлен!"
                    else:
                        text = f"⚠️ Преподаватель «{sql.get_teacher_name(res['teacher_id'])}» уже добавлен."
                    await refresh_teachers_message(msg, state, u_id, text)
                else:
                    await refresh_add_teacher_message(msg, state, u_id)
            elif teachers['code'] == 0:
                await state.update_data(sub_message=f'ℹ️ Преподаватели института:\n'
                                                    f'{teachers["related"]}')
                await refresh_add_teacher_message(msg, state, u_id)
            elif teachers['code'] == 1:
                try:
                    clean_related = teachers['related'].replace("(ОРУ)", "").strip()
                except:
                    clean_related = teachers['related']
                await state.update_data(sub_message=f'ℹ️ Преподаватели факультета:\n'
                                                    f'{clean_related}')
                await refresh_add_teacher_message(msg, state, u_id)
            elif teachers['code'] == 2:
                try:
                    clean_related = teachers['related'].replace("(ОРУ)", "").strip()
                except:
                    clean_related = teachers['related']
                await state.update_data(sub_message=f'ℹ️ Преподаватели кафедры:\n'
                                                    f'{clean_related}')
                await refresh_add_teacher_message(msg, state, u_id)
        else:
            # 3. Ничего не найдено
            text = f"⚠️ Преподавателя или подразделения «{teacher}» нет."
            await refresh_teachers_message(msg, state, u_id, text)
    except Exception as e:
        logger.warning(f'Ошибка при добавлении преподавателя: {e}')


async def list_user_teachers(call: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн-кнопок преподавателей"""
    try:
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
    except Exception as e:
        logger.warning(f'Ошибка при выводе кнопок с преподавателями: {e}')
    finally:
        await call.answer()


async def refresh_teachers_message(msg: types.Message, state: FSMContext, user_id: int, text: str = ""):
    """
    Обновить сообщение со списком преподавателей
    Args:
        msg: входящее сообщение от пользователя
        state: состояние FSM
        user_id: ID пользователя
        text: текст для саб строки
    """
    try:
        u_teachers = sql.get_user_teachers(user_id)

        if not u_teachers:
            sent = await msg.answer("🎓 У вас пока нет добавленных преподавателей.\n"
                                    "\n"
                                    f"{text}",
                                    reply_markup=get_inline_key_list(user_id, "teacher"))
        else:
            sent = await msg.answer("🎓 Ваши преподаватели:\nНажмите на преподавателя для удаления\n"
                                    "\n"
                                    f"{text}",
                                    reply_markup=get_inline_key_list(user_id, "teacher"))

        # Сохраняем ID последнего сообщения
        await state.update_data(last_msg=sent.message_id)
    except Exception as e:
        logger.warning(f'Ошибка при обновлении сообщения с добавлением преподавателей: {e}')


def register_teachers_handlers(dp: Dispatcher):
    # Меню групп
    dp.register_callback_query_handler(
        show_teachers,
        lambda c: c.data == "menu_teachers" and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_message_handler(
        show_teachers,
        commands=["groups"],
        content_types=types.ContentTypes.TEXT,
        state="*"
    )
    # Навигация
    dp.register_callback_query_handler(
        list_user_teachers,
        lambda c: ('next_page_' in c.data or 'prev_page_' in c.data) and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Удаление групп
    dp.register_callback_query_handler(
        list_user_teachers,
        lambda c: (c.data.startswith(
            '-') or c.data == "clear_all_teacher") and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.TEACHER_EDIT
    )
    # Добавление групп
    dp.register_message_handler(
        add_teacher,
        lambda m: not m.text.startswith('/'),
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state=MenuStates.TEACHER_EDIT
    )
