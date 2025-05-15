import re
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ChatType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import MessageNotModified

import sql
from bot import MenuStates, get_main_menu
from bot.handlers.common import notify_mp, back_to_main, generate_free_windows_multi
from bot.keyboards import get_free_windows_keyboard, generate_edit_menu_keyboard


# =======[Выбор свободного времени]=======
async def show_current_page(message: types.Message, state: FSMContext, text: str = ''):
    """Вывод свободных окон"""
    async with state.proxy() as data:
        dates = data['dates']
        free_windows = data['free_windows']
        selected = data.get('selected', {})
        page = data['current_page']

    if page < 0 or page >= len(dates):
        return

    current_date = dates[page]
    free_times = free_windows.get(current_date, [])

    kb = get_free_windows_keyboard(current_date=current_date, free_times=free_times, selected=selected, page=page,
                                   total_pages=len(dates))

    msg_text = (f"📅 Выберите свободное время для {current_date}:\n"
                f"\n"
                f"{'Свободного времени нет' if not free_times else ''}\n"
                f"\n"
                f"{text}")

    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(msg_text, reply_markup=kb)
    else:
        await message.edit_text(msg_text, reply_markup=kb)


async def send_free_windows_menu(call: types.CallbackQuery, state: FSMContext, page=0):
    """Инициализация меню со свободными окнами"""
    try:
        u_id = call.from_user.id
        dates = sql.get_user_dates(u_id)
        group_ids = sql.get_user_groups(u_id)
        teacher_ids = sql.get_user_teachers(u_id)
        if not dates:
            await back_to_main(
                call=call,
                state=state,
                text="⚠️ Вы не указали дату!"
            )
            return
        elif not group_ids:
            await back_to_main(
                call=call,
                state=state,
                text="⚠️ Вы не указали группы!"
            )
            return

        free_windows = generate_free_windows_multi(group_ids, teacher_ids, dates)

        async with state.proxy() as data:
            data['group_ids'] = group_ids
            data['teacher_ids'] = teacher_ids
            data['dates'] = dates
            data['free_windows'] = free_windows
            data['current_page'] = page

            if 'selected' not in data:
                data['selected'] = {}

        await show_current_page(call.message, state)
        await MenuStates.EDIT_WINDOW.set()
    finally:
        await call.answer()


async def handle_add_time(call: types.CallbackQuery, state: FSMContext):
    """
    Добавление время в список выбранных, если время выбрана за др дату, то обнуляем предыдущие
    """
    try:
        _, key = call.data.split('_', 1)
        new_date, new_time = key.split('_', 1)

        async with state.proxy() as data:
            current_page = data['current_page']
            current_date = data['dates'][current_page]

            if new_date != current_date:
                return

            selected = data.get('selected', {})

            # Удаляем все старые записи, если это новая дата или новая пара
            if new_date not in selected or not selected[new_date]:
                selected = {new_date: {}}

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
    """
    Подтверждение выбора времени.
    Проверяет, выбрано ли время на любой из страниц (дат).
    """
    try:
        async with state.proxy() as data:
            selected = data.get('selected', {})
            has_any_selection = any(times for times in selected.values())

        if not has_any_selection:
            text = "⚠️ Вы не выбрали ни одного времени для встречи."
            await show_current_page(call.message, state, text)
            return

        await show_edit_menu(call, state)
    finally:
        await call.answer()


# =======[Меню для ввода доп. информации]=======
async def show_edit_menu(event: Union[types.CallbackQuery, types.Message], state: FSMContext, text: str = ""):
    """Вывод пунктов меню для редакции"""
    async with state.proxy() as data:
        cabinet = data.get('cabinet')
        comment = data.get('comment')

    # Формируем текст
    cabinet_display = cabinet if cabinet else "Не указана"
    comment_display = comment if comment else "Не указан"

    text = (
        "🏫 Выбранная аудитория:\n"
        f"{cabinet_display}\n"
        "📢 Ваш комментарий:\n"
        f"{comment_display}\n"
        "\n"
        "📝 Заполните или измените данные:\n"
        "\n"
        f"{text}"
    )

    # Формируем клавиатуру
    kb = generate_edit_menu_keyboard(
        cabinet=cabinet,
        comment=comment)

    # Логика отправки или редактирования сообщения
    if isinstance(event, types.CallbackQuery):
        message = event.message
        try:
            await message.edit_text(text, reply_markup=kb)
        except MessageNotModified:
            pass
    elif isinstance(event, types.Message):
        await event.answer(text, reply_markup=kb)


# ======[Ввод аудитории]======
async def edit_cabinet(callback_query: types.CallbackQuery, state: FSMContext):
    """Меню с вводом аудитории"""
    try:
        data = await state.get_data()
        current_room = data.get("cabinet", "Не указана")

        await MenuStates.EDIT_AUDI.set()
        await callback_query.message.edit_text(
            f"Текущая аудитория: {current_room}\n"
            "\n"
            "Введите новую аудиторию:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_edit_menu")
            )
        )
    finally:
        await callback_query.answer()


async def process_edit_cabinet(message: types.Message, state: FSMContext):
    """Проверка ввода аудитории"""
    cabinet = message.text.strip()
    if not re.match(r"^\d{1,2}-\d{3}[а-яa-z_]?$", cabinet, re.IGNORECASE):
        await message.answer("❌ Неверный формат аудитории. Пример: 11-213, 1-003_, 5-312а")
        return

    await state.update_data(cabinet=cabinet)

    await message.answer(
        f"✅ Аудитория изменена на: {cabinet}\n"
        "\n"
        "Введите другую или нажмите 'Назад' для возврата:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_edit_menu")
        )
    )


# ======[Ввод комментария]======
async def edit_comment(call: types.CallbackQuery, state: FSMContext):
    """Ввод комментария"""
    try:
        data = await state.get_data()
        comment = data.get("comment", "не указана")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("Назад", callback_data="back_to_edit_menu"))
        if comment:
            await call.message.edit_text(f"Ваш комментарий:\n{comment}\n"
                                         "\n"
                                         "Введите новый комментарий:",
                                         reply_markup=kb)
        else:
            await call.message.edit_text("Введите комментарий:",
                                         reply_markup=kb)
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


# ======[Финальный предпросмотр]======
async def finalize_selection(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение информации"""
    u_id = call.from_user.id
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
                text = "⚠️ Выбранное время было занято другим пользователем."
                await show_edit_menu(call, state, text)
                return
    finally:
        await call.answer()
    initiator_teacher_name = sql.get_teacher_name(sql.get_teacher_id_tg(u_id))
    # Отправляем на подтверждение
    summary = generate_summary(data, initiator_teacher_name)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Подтвердить", callback_data="save_final"))
    kb.add(types.InlineKeyboardButton("Редактировать", callback_data="back_to_edit_menu"))

    await call.message.edit_text(summary, reply_markup=kb)


def generate_summary(data: dict, initiator_teacher_name: str) -> str:
    """Генератор текста для просмотра"""
    current_date = data['dates'][data['current_page']]
    times = list(data['selected'][current_date].keys())

    cabinet = data.get('cabinet', 'Не указана')
    comment = data.get('comment', 'Не указан')
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
        f"⚡ Инициатор:\n{initiator_teacher_name}\n\n"
        f"📅 Дата:\n{current_date}\n"
        f"⏰ Время:\n{times_str}\n\n"
        f"🏫 Аудитория:\n{cabinet}\n\n"
        f"👥 Группы:\n{groups_str}\n"
        f"🧑‍🏫 Преподаватели:\n{teachers_str}\n"
        f"💬 Комментарий:\n{comment}"
    )

    return summary


# ======[Подтверждение]======
async def save_final_data(call: types.CallbackQuery, state: FSMContext):
    try:
        u_id = call.from_user.id
        initiator_teacher_id = sql.get_teacher_id_tg(u_id)

        async with state.proxy() as data:
            current_date = data['dates'][data['current_page']]
            times = list(data['selected'][current_date].keys())
            group_ids = data.get('group_ids', [])
            teacher_ids = data.get('teacher_ids', [])
            cabinet = data.get('cabinet')
            #cabinet_id = cabinet.get('id') if cabinet and 'id' in cabinet else None
            comment = data.get('comment')

            groups = group_ids if group_ids else None
            teachers = teacher_ids if teacher_ids else None

        # Добавление записи в таблицу
        for group_id in groups:
            if teachers:
                for teacher_id in teachers:
                    sql.add_busy_window(
                        current_date=current_date,
                        times=times,
                        group_id=group_id,
                        teacher_id=teacher_id,
                        cabinet_id=cabinet,
                        comment=comment,
                        initiator_teacher_id=initiator_teacher_id
                    )
            else:
                sql.add_busy_window(
                    current_date=current_date,
                    times=times,
                    group_id=group_id,
                    teacher_id=None,
                    cabinet_id=cabinet,
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
            f"⚡ Инициатор:\n{sql.get_teacher_name(initiator_teacher_id)}\n\n"
            f"📅 Дата:\n{current_date}\n"
            f"⏰ Время:\n{', '.join(times)}\n\n"
            f"🏫 Аудитория:\n{cabinet or 'Не указана'}\n\n"
            f"👥 Группы:{group_name}\n"
            f"👩🏻‍🏫 Преподаватели:{teacher_name}\n\n"
            f"💬 Комментарий:\n{comment or 'Не указан'}"
        )

        # Оповещение участников
        unnotified_groups, unnotified_teachers = await notify_mp(group_ids, teacher_ids, text)

        # Сообщение об успешном сохранении
        await call.message.edit_text("✅ Мероприятие успешно запланировано! Участники оповещены.")

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
    dp.register_message_handler(
        process_edit_cabinet,
        state=MenuStates.EDIT_AUDI,
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT
    )
    dp.register_callback_query_handler(
        send_free_windows_menu,
        lambda c: c.data == 'menu_teacher_window' and c.message.chat.type == ChatType.PRIVATE,
        state='*'
    )

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

    dp.register_callback_query_handler(
        confirm_selected_time,
        lambda c: c.data == 'confirm_time' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(
        edit_cabinet,
        lambda c: c.data == 'edit_audi' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )
    dp.register_callback_query_handler(
        edit_comment,
        lambda c: c.data == 'edit_comment' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_message_handler(
        save_comment,
        chat_type=ChatType.PRIVATE,
        state=MenuStates.EDIT_COMMENT
    )

    dp.register_callback_query_handler(
        finalize_selection,
        lambda c: c.data == 'finalize' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(
        save_final_data,
        lambda c: c.data == 'save_final' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )

    dp.register_callback_query_handler(
        back_to_edit_menu,
        lambda c: c.data == 'back_to_edit_menu' and c.message.chat.type == ChatType.PRIVATE,
        state=[MenuStates.EDIT_AUDI, MenuStates.EDIT_COMMENT, MenuStates.EDIT_WINDOW]
    )

    dp.register_callback_query_handler(
        send_free_windows_menu,
        lambda c: c.data == 'back_to_window' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_WINDOW
    )
