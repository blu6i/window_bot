import re
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ChatType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import MessageNotModified

import sql
from bot import MenuStates, get_main_menu
from bot.handlers.common import notify_mp

# Предопределённые временные интервалы
PAIR_TIMES = [
    "08:20-09:50",
    "10:00-11:30",
    "11:45-13:15",
    "14:00-15:30",
    "15:45-17:15",
    "17:20-18:50",
    "18:55-20:25"
]


def generate_free_windows_multi(occupied: dict) -> dict:
    free_windows = {}
    for date, busy_times in occupied.items():
        free = [pair for pair in PAIR_TIMES if pair not in busy_times]
        free_windows[date] = free
    return free_windows


async def show_current_page(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        dates = data['dates']
        free_windows = data['free_windows']
        selected = data.get('selected', {})
        page = data['current_page']

    if page < 0 or page >= len(dates):
        return

    current_date = dates[page]
    free_times = free_windows.get(current_date, [])

    kb = types.InlineKeyboardMarkup(row_width=2)

    if not free_times:
        kb.add(types.InlineKeyboardButton("Свободного времени нет", callback_data="none"))
    else:
        for time in free_times:
            text = f"{time} ✅" if selected.get(current_date, {}).get(time) else time
            button_key = f"{current_date}_{time}"
            callback_data = f"del_{button_key}" if selected.get(current_date, {}).get(time) else f"add_{button_key}"
            kb.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data="prev_page"))
    if page < len(dates) - 1:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡", callback_data="next_page"))
    if nav_buttons:
        kb.row(*nav_buttons)

    kb.add(types.InlineKeyboardButton("Подтвердить время", callback_data="confirm_time"))
    kb.add(types.InlineKeyboardButton("Назад в меню", callback_data="back_to_menu"))

    msg_text = f"📅 Выберите свободное время для {current_date}:"

    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(msg_text, reply_markup=kb)
    else:
        await message.edit_text(msg_text, reply_markup=kb)


async def send_free_windows_menu(call: types.CallbackQuery, state: FSMContext, page=0):
    """Меню со свободным временем"""
    try:
        u_id = call.from_user.id
        dates = sql.get_user_dates(u_id)
        if not dates:
            await call.message.answer("Нет доступных дат.")
            return

        group_ids = sql.get_user_groups(u_id)
        teacher_ids = sql.get_user_teachers(u_id)

        occupied = sql.get_occupied_times_multi(group_ids, teacher_ids, dates)
        free_windows = generate_free_windows_multi(occupied)

        async with state.proxy() as data:
            data['group_ids'] = group_ids
            data['teacher_ids'] = teacher_ids
            data['dates'] = dates
            data['free_windows'] = free_windows
            data['current_page'] = page

            # 🟢 Не очищаем 'selected', если оно было
            if 'selected' not in data:
                data['selected'] = {}

        await show_current_page(call.message, state)
        await MenuStates.EDIT_WINDOW.set()
    finally:
        await call.answer()


async def handle_add_time(call: types.CallbackQuery, state: FSMContext):
    try:
        _, key = call.data.split('_', 1)
        new_date, new_time = key.split('_', 1)

        async with state.proxy() as data:
            current_page = data['current_page']
            current_date = data['dates'][current_page]

            if new_date != current_date:
                return

            selected = data.get('selected', {})

            # ❌ Удаляем все старые записи, если это новая дата или новая пара
            if new_date not in selected or not selected[new_date]:
                selected = {new_date: {}}  # Очищаем всё, если это первая пара для этой даты

            selected[new_date][new_time] = True
            data['selected'] = selected

        await show_current_page(call.message, state)
    finally:
        await call.answer()


async def handle_remove_time(call: types.CallbackQuery, state: FSMContext):
    """Отмена выбора"""
    try:
        _, key = call.data.split('_', 1)
        date, time = key.split('_', 1)

        async with state.proxy() as data:
            current_date = data['dates'][data['current_page']]
            if date != current_date:
                return

            selected = data.get('selected', {}).get(date, {})
            if time in selected:
                selected.pop(time)
                if not selected:
                    data['selected'].pop(date)
                else:
                    data['selected'][date] = selected

        await show_current_page(call.message, state)

    finally:
        await call.answer()


async def handle_pagination(call: types.CallbackQuery, state: FSMContext):
    """Навигация"""
    try:
        async with state.proxy() as data:
            current_page = data['current_page']
        # Определяем сдвиг страницы
        if call.data == 'prev_page':
            new_page = max(0, current_page - 1)
        else:  # next_page
            new_page = min(len(data['dates']) - 1, current_page + 1)

        async with state.proxy() as data:
            data['current_page'] = new_page

        await show_current_page(call.message, state)
    finally:
        await call.answer()


async def confirm_selected_time(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение выбора времени"""
    try:
        async with state.proxy() as data:
            current_date = data['dates'][data['current_page']]
            selected_times = data['selected'].get(current_date, {})

        if not selected_times:
            await call.answer("Вы не выбрали ни одно время.", show_alert=True)
            return

        await show_edit_menu(call, state)
    finally:
        await call.answer()


async def show_edit_menu(event: Union[CallbackQuery, Message], state: FSMContext):
    async with state.proxy() as data:
        cabinet = data.get('cabinet')
        comment = data.get('comment')

    kb = types.InlineKeyboardMarkup()

    audi_text = "🏫 Аудитория"
    if cabinet:
        audi_text += " ✅"
    kb.add(types.InlineKeyboardButton(audi_text, callback_data="edit_audi"))

    comment_text = "📢 Комментарий"
    if comment:
        comment_text += " ✅"
    kb.add(types.InlineKeyboardButton(comment_text, callback_data="edit_comment"))

    kb.add(types.InlineKeyboardButton("✉️ Подтвердить", callback_data="finalize"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_window"))

    text = "📝 Заполните данные:"

    # Логика отправки или редактирования сообщения
    if isinstance(event, CallbackQuery):
        message = event.message
        try:
            await message.edit_text(text, reply_markup=kb)
        except MessageNotModified:
            pass
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=kb)


async def edit_cabinet(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        current_room = data.get("cabinet", "не указана")

        await MenuStates.EDIT_AUDI.set()
        await callback_query.message.edit_text(
            f"Текущая аудитория: {current_room}\n\nВведите новую аудиторию:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_edit_menu")
            )
        )
    finally:
        await callback_query.answer()


async def process_edit_cabinet(message: types.Message, state: FSMContext):
    cabinet = message.text.strip()
    if not re.match(r"^\d{1,2}-\d{3}[а-яa-z_]?$", cabinet, re.IGNORECASE):
        await message.answer("❌ Неверный формат аудитории. Пример: 11-213, 1-003_, 5-312а")
        return

    await state.update_data(cabinet=cabinet)

    await message.answer(
        f"✅ Аудитория изменена на: {cabinet}\n\nВведите другую или нажмите 'Назад' для возврата:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_edit_menu")
        )
    )


async def edit_comment(call: types.CallbackQuery, state: FSMContext):
    """Выбор комментария"""
    try:
        data = await state.get_data()
        comment = data.get("comment", "не указана")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("Назад", callback_data="back_to_edit_menu"))
        if comment:
            await call.message.edit_text(f"Ваш комментарий:\n{comment}\n\nВведите новый комментарий:", reply_markup=kb)
        else:
            await call.message.edit_text("Введите комментарий:", reply_markup=kb)
        await MenuStates.EDIT_COMMENT.set()
    finally:
        await call.answer()


async def save_comment(message: types.Message, state: FSMContext):
    """Сохранение комментария"""
    comment = message.text.strip()
    async with state.proxy() as data:
        data['comment'] = comment
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Назад", callback_data="back_to_edit_menu"))
    await message.answer(
        f"✅ Комментарий изменен\n\nВведите другой комментарий или нажмите 'Назад' для возврата:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_edit_menu")
        )
    )


async def finalize_selection(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение информации"""
    try:
        async with state.proxy() as data:
            current_date = data['dates'][data['current_page']]
            selected_times = list(data['selected'][current_date].keys())

            group_id = data['group_ids'][0] if data['group_ids'] else None
            teacher_id = data['teacher_ids'][0] if data['teacher_ids'] else None
            cabinet = data.get('cabinet')
            cabinet_id = cabinet.get('id') if cabinet and 'id' in cabinet else None

        # Проверяем, не занято ли время за время заполнения формы
        for time in selected_times:
            if not sql.is_time_still_free(group_id, teacher_id, cabinet_id, current_date, time):
                await call.answer("⚠️ Выбранное время было занято другим пользователем.", show_alert=True)
                await show_edit_menu(call, state)
                return
    finally:
        await call.answer()

    # Отправляем на подтверждение
    summary = generate_summary(data)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Подтвердить", callback_data="save_final"))
    kb.add(types.InlineKeyboardButton("Редактировать", callback_data="back_to_edit_menu"))

    await call.message.edit_text(summary, reply_markup=kb)


def generate_summary(data: dict) -> str:
    current_date = data['dates'][data['current_page']]
    times = list(data['selected'][current_date].keys())

    cabinet = data.get('cabinet', '-')
    comment = data.get('comment', '-')
    group_ids = data.get('group_ids', [])
    teacher_ids = data.get('teacher_ids', [])

    # Формируем строку с группами и преподавателями
    groups_str = '-'
    if group_ids:
        groups_str = ''
        for group in group_ids:
            groups_str += f'• {sql.get_group_name(group)}\n'
    teachers_str = '-'
    if teacher_ids:
        teachers_str = ''
        for teacher in teacher_ids:
            teachers_str += f'• {sql.get_teacher_name(teacher)}\n'
    # Формируем время
    times_str = '\n'.join(f"• {time}" for time in times)

    # Собираем итоговое сообщение
    summary = (
        "📌 Предварительный просмотр:\n\n"
        f"📅 Дата:\n{current_date}\n"
        f"⏰ Время:\n{times_str}\n"
        f"🏫 Аудитория:\n{cabinet}\n"
        f"🧑‍🏫 Преподаватель(и):\n{teachers_str}\n"
        f"👥 Группа(ы):\n{groups_str}\n"
        f"💬 Комментарий:\n{comment}"
    )

    return summary


async def save_final_data(call: types.CallbackQuery, state: FSMContext):
    try:
        u_id = call.from_user.id
        initiator_teacher_id = sql.get_user_id(u_id)

        async with state.proxy() as data:
            current_date = data['dates'][data['current_page']]
            times = list(data['selected'][current_date].keys())
            group_ids = data.get('group_ids', [])
            teacher_ids = data.get('teacher_ids', [])
            cabinet = data.get('cabinet')
            cabinet_id = cabinet.get('id') if cabinet and 'id' in cabinet else None
            comment = data.get('comment')

            groups = group_ids if group_ids else [None]
            teachers = teacher_ids if teacher_ids else [None]

        # Добавление записи в таблицу
        for group_id in groups:
            for teacher_id in teachers:
                sql.add_busy_window(
                    current_date=current_date,
                    times=times,
                    group_id=group_id,
                    teacher_id=teacher_id,
                    cabinet_id=cabinet_id,
                    comment=comment,
                    initiator_teacher_id=initiator_teacher_id
                )

        group_name = ""
        if groups:
            for group in groups:
                group_name += f"\n• {sql.get_group_name(group)}"
        teacher_name = ""
        if teachers:
            for teacher in teachers:
                teacher_name += f"\n• {sql.get_teacher_name(teacher)}"

        text = (
            f"🔔 Запланирована новая встреча:\n"
            f"📅 Дата:\n{current_date}\n"
            f"⏰ Время:\n{', '.join(times)}\n\n"
            f"🏫 Аудитория:\n{cabinet_id or 'Не указана'}\n\n"
            f"👥 Группы:{group_name}\n"
            f"👩🏻‍🏫 Преподаватели:{teacher_name}\n\n"
            f"💬 Комментарий:\n{comment or 'Не указан'}"
        )

        # Оповещение участников
        unnotified_groups, unnotified_teachers = await notify_mp(group_ids, teacher_ids, text)

        # Сообщение об успешном сохранении
        await call.message.edit_text("✅ Мероприятие(я) успешно запланировано(ы)! Участники оповещены.")

        # Обратная связь пользователю
        if not unnotified_groups and not unnotified_teachers:
            await call.message.answer("📬 Уведомление успешно отправлено.")
        else:
            # Формируем сообщение о тех, кто не был уведомлен
            not_notified_message = "❗️ Не удалось отправить уведомления следующим участникам:\n"
            if unnotified_groups:
                not_notified_message += f"Группы без чатов:"
                for group in unnotified_groups:
                    not_notified_message += f"\n• {sql.get_group_name(group)}"
            if unnotified_teachers:
                not_notified_message += f"\nПреподаватели без TG ID:"
                for teacher in unnotified_teachers:
                    not_notified_message += f"\n• {sql.get_teacher_name(teacher)}"

            await call.message.answer(not_notified_message)

        await state.finish()
        sent = await call.message.answer("🏠 Главное меню\n\nВыберите нужный раздел",
                                         reply_markup=get_main_menu(call.from_user.id))
        await state.update_data(last_msg=sent.message_id)
    finally:
        await call.answer()


async def back_to_edit_menu(call: types.CallbackQuery, state: FSMContext):
    """В меню навигации"""
    try:
        await MenuStates.EDIT_WINDOW.set()
        await show_edit_menu(call, state)
    finally:
        await call.answer()


def register_windows_list_handlers(dp: Dispatcher):
    dp.register_message_handler(process_edit_cabinet,
                                state=MenuStates.EDIT_AUDI,
                                chat_type=ChatType.PRIVATE,
                                content_types=types.ContentTypes.TEXT)
    dp.register_callback_query_handler(send_free_windows_menu,
                                       lambda c: c.data == 'menu_teacher_window' and c.message.chat.type == ChatType.PRIVATE,
                                       state='*')

    dp.register_callback_query_handler(
        handle_add_time,
        lambda c: c.data.startswith('add_') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(
        handle_remove_time,
        lambda c: c.data.startswith('del_') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(
        handle_pagination,
        lambda c: c.data in ['prev_page', 'next_page'] and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(confirm_selected_time,
                                       lambda c: c.data == 'confirm_time' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)

    dp.register_callback_query_handler(edit_cabinet,
                                       lambda c: c.data == 'edit_audi' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)
    dp.register_callback_query_handler(edit_comment,
                                       lambda c: c.data == 'edit_comment' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)

    dp.register_message_handler(save_comment,
                                chat_type=ChatType.PRIVATE,
                                state=MenuStates.EDIT_COMMENT)

    dp.register_callback_query_handler(finalize_selection,
                                       lambda c: c.data == 'finalize' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)

    dp.register_callback_query_handler(save_final_data,
                                       lambda c: c.data == 'save_final' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)

    dp.register_callback_query_handler(back_to_edit_menu,
                                       lambda
                                           c: c.data == 'back_to_edit_menu' and c.message.chat.type == ChatType.PRIVATE,
                                       state=[MenuStates.EDIT_AUDI, MenuStates.EDIT_COMMENT, MenuStates.EDIT_WINDOW])

    dp.register_callback_query_handler(send_free_windows_menu,
                                       lambda c: c.data == 'back_to_window' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_WINDOW)
