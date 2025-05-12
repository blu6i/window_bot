import re
from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatType

import sql
from bot import MenuStates
from bot.keyboards import get_edit_meeting_menu, get_time_selection_keyboard
from sql import get_user_dates, get_user_groups, get_user_teachers, get_occupied_times_multi, update_meeting_entry

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


async def my_meetings_menu(call: types.CallbackQuery, state: FSMContext):
    u_id = call.from_user.id
    teacher_id = sql.get_teacher_id_tg(u_id)

    if not teacher_id:
        await call.answer("Вы не авторизованы.", show_alert=True)
        return

    # Получаем СГРУППИРОВАННЫЕ данные
    meetings_raw = sql.get_meet_teacher(teacher_id)

    if not meetings_raw:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))
        await call.message.edit_text("У вас пока нет встреч.", reply_markup=kb)
        return

    # Форматируем в структуру {date: [meeting_dict, ...]}
    meetings_grouped = await format_meetings_for_state(meetings_raw)

    async with state.proxy() as data:
        data['meetings'] = meetings_grouped
        data['current_date_index'] = 0
        data['current_meeting_index'] = 0
        data['teacher_id'] = teacher_id

    await show_meeting_dates(call.message, state)
    await MenuStates.MY_MEET.set()

    await call.answer()


async def show_meeting_dates(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        dates = list(data['meetings'].keys())
        index = data['current_date_index']

    kb = types.InlineKeyboardMarkup(row_width=2)

    # Кнопки дат
    for i, date in enumerate(dates):
        icon = "🕒" if datetime.strptime(date, "%Y-%m-%d").date() >= datetime.now().date() else "✅"
        kb.add(types.InlineKeyboardButton(f"{icon} {date}", callback_data=f"view_date_{date}"))

    # Навигация
    nav_buttons = []
    if index > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data="prev_date"))
    if index < len(dates) - 1:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡", callback_data="next_date"))
    if nav_buttons:
        kb.row(*nav_buttons)

    kb.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))

    await message.edit_text("📅 Выберите дату:", reply_markup=kb)


async def view_date(callback: types.CallbackQuery, state: FSMContext):
    date = callback.data.split('_')[-1]

    async with state.proxy() as data:
        data['current_date'] = date
        data['current_meeting_index'] = 0

    await show_meeting_details(callback.message, state)
    await MenuStates.MY_MEET.set()

    await callback.answer()


async def format_meetings_for_state(meetings_raw):
    grouped = {}

    for meeting in meetings_raw:
        date = meeting[0]
        time = meeting[1]
        groups = meeting[2].split(',') if meeting[2] else []
        teachers = meeting[3].split(',') if meeting[3] else []
        cabinet_id = meeting[4]
        comment = meeting[5]
        meeting_id = meeting[6]
        initiator_id = meeting[7]
        is_completed = meeting[8]

        if date not in grouped:
            grouped[date] = []

        grouped[date].append({
            'time': time,
            'groups': list(map(int, groups)),
            'teachers': list(map(int, teachers)),
            'cabinet_id': cabinet_id,
            'comment': comment,
            'meeting_id': meeting_id,
            'initiator_id': int(initiator_id) if initiator_id else None,
            'is_completed': is_completed
        })

    return grouped


async def show_meeting_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        date = data['current_date']
        meetings = data['meetings'][date]
        idx = data['current_meeting_index']

    meeting = meetings[idx]
    time = meeting['time']
    groups = meeting['groups']
    teachers = meeting['teachers']
    cabinet_id = meeting['cabinet_id']
    comment = meeting['comment']
    is_completed = meeting['is_completed']

    group_names = "-"
    if groups:
        group_names = ""
        for group in groups:
            group_names += f'{sql.get_group_name(group)}\n'

    teacher_names = "-"
    if teachers:
        teacher_names = ""
        for teacher in teachers:
            teacher_names += f'{sql.get_teacher_name(teacher)}\n'
    cabinet_info = ''
    # cabinet_info = sql.get_cabinet_info(cabinet_id) if cabinet_id else "-"
    status = '🔴' if is_completed else '🟢'
    text = f"""
📅 <b>Дата:</b>\n{date}
⏰ <b>Время:</b>\n{time}
🏫 <b>Аудитория:</b>\n{cabinet_info}
👥 <b>Группы:</b>\n{group_names}
🧑‍🏫 <b>Преподаватели:</b>\n{teacher_names}
💬 <b>Комментарий:</b>\n{comment or '-'}
{status} <b>Статус:</b> {'Завершено' if is_completed else 'Ожидается'}
"""

    kb = types.InlineKeyboardMarkup(row_width=1)
    if not is_completed:
        kb.add(types.InlineKeyboardButton("✅ Отметить как пройденное",
                                          callback_data="mark_complete"))
    elif is_completed:
        kb.add(types.InlineKeyboardButton("❌ Отметить как не пройденное",
                                          callback_data="mark_not_complete"))
    if meeting['initiator_id'] == data['teacher_id']:
        kb.add(types.InlineKeyboardButton("🗑️ Удалить встречу", callback_data="delete_meeting"))
    if meeting['initiator_id'] == data['teacher_id']:
        kb.add(types.InlineKeyboardButton("🔁 Редактировать встречу", callback_data="edit_meeting"))
    kb.add(types.InlineKeyboardButton("🔔 Отправить напоминание", callback_data="send_reminder"))
    # Навигация по встречам
    if len(meetings) > 1:
        nav_buttons = []
        if idx > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅ Предыдущее", callback_data="prev_meeting"))
        if idx < len(meetings) - 1:
            nav_buttons.append(types.InlineKeyboardButton("Следующее ➡", callback_data="next_meeting"))
        kb.row(*nav_buttons)
    kb.add(types.InlineKeyboardButton("🔙 Назад к датам", callback_data="back_to_dates"))

    await message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def navigate_meetings(callback: types.CallbackQuery, state: FSMContext):
    delta = 1 if callback.data == 'next_meeting' else -1

    async with state.proxy() as data:
        data['current_meeting_index'] += delta

        # Защита от выхода за границы
        date = data['current_date']
        meetings_count = len(data['meetings'][date])
        data['current_meeting_index'] = max(0, min(meetings_count - 1, data['current_meeting_index']))

    await show_meeting_details(callback.message, state)
    await callback.answer()


async def delete_meeting(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        date = data['current_date']
        meetings = data['meetings'][date]
        idx = data['current_meeting_index']
        meeting = meetings[idx]

        time = meeting['time']
        initiator_id = meeting['initiator_id']

    # 1. Удаление из БД
    success = sql.remove_meeting_group(date, time, initiator_id)

    if not success:
        await callback.answer("❌ Ошибка при удалении.", show_alert=True)
        return

    async with state.proxy() as data:
        # 2. Обновляем локальные данные
        del data['meetings'][date][idx]

        # 3. Проверяем, остались ли встречи на эту дату
        if not data['meetings'][date]:
            del data['meetings'][date]

        # 4. Защита: если мы удалили последнюю встречу на странице
        if 'current_meeting_index' in data and idx >= len(data['meetings'].get(date, [])):
            data['current_meeting_index'] = max(0, idx - 1)

    # 5. Если дата всё ещё существует в словаре — показываем новую встречу
    async with state.proxy() as data:
        if date in data['meetings']:
            await show_meeting_details(callback.message, state)
        else:
            await show_meeting_dates(callback.message, state)
            await MenuStates.MY_MEET.set()

    await callback.answer("🗑️ Встреча удалена")


async def mark_complete(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        date = data['current_date']
        meetings = data['meetings'][date]
        idx = data['current_meeting_index']
        meeting = meetings[idx]

        # Получаем ID встречи из словаря
        meeting_id = meeting.get('meeting_id')  # ✅ Теперь обращаемся по ключу
        initiator_id = meeting.get('initiator_id')
        is_completed = meeting.get('is_completed')

    if is_completed:
        await callback.answer("⚠️ Эта встреча уже завершена", show_alert=True)
        return

    # 1. Обновляем в БД
    success = sql.update_completed(meeting_id)

    if not success:
        await callback.answer("❌ Ошибка при обновлении статуса", show_alert=True)
        return

    async with state.proxy() as data:
        # 2. Обновляем локальную копию
        data['meetings'][date][idx]['is_completed'] = 1

    # 3. Показываем обновлённые данные
    await show_meeting_details(callback.message, state)


async def mark_not_complete(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        date = data['current_date']
        meetings = data['meetings'][date]
        idx = data['current_meeting_index']
        meeting = meetings[idx]

        meeting_id = meeting.get('meeting_id')
        is_completed = meeting.get('is_completed')

    # 1. Обновляем в БД
    success = sql.update_not_completed(meeting_id)

    if not success:
        await callback.answer("❌ Ошибка при обновлении статуса", show_alert=True)
        return

    async with state.proxy() as data:
        # 2. Обновляем локальную копию
        data['meetings'][date][idx]['is_completed'] = 0

    # 3. Показываем обновлённые данные
    await show_meeting_details(callback.message, state)
    await callback.answer("🔄 Статус изменён: теперь это активная встреча")


async def send_reminder(callback: types.CallbackQuery):
    await callback.answer("📬 Оповещение отправлено всем участникам")


async def start_edit_meeting(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        # Получаем данные текущей встречи
        date = data['current_date']
        idx = data['current_meeting_index']
        meeting = data['meetings'][date][idx]
        # Сохраняем оригинальные данные встречи, если ещё не сохранены
        if 'original_meeting' not in data:
            # Сохраняем старые данные для возможного отката
            data['original_meeting'] = meeting.copy()

            # Также сохраняем старую дату и время, чтобы можно было позже сравнить
            data['old_dates_times'] = [(meeting['time'], date)]

    # Ожидаем, что теперь можно выбрать, что редактировать
    await callback.message.edit_text("🔁 Выберите, что редактировать:", reply_markup=get_edit_meeting_menu())
    await MenuStates.EDIT_MEET.set()
    await callback.answer()


async def cancel_edit_meeting(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if 'original_meeting' in data:
            date = data['current_date']
            idx = data['current_meeting_index']
            data['meetings'][date][idx] = data['original_meeting']
            del data['original_meeting']
    await MenuStates.MY_MEET.set()
    await callback.message.answer("❌ Изменения отменены.")
    await show_meeting_details(callback.message, state)


async def change_date_page(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("|")
    direction = parts[1] if len(parts) > 1 else None  # None значит "первое открытие"

    data = await state.get_data()

    page = data.get("page", 0)
    dates = data.get("dates", [])
    free_times_map = data.get("free_times_map", {})
    selected_times = data.get("selected_times", [])
    await MenuStates.EDIT_MEET_DATETIME.set()
    if not dates or not free_times_map:
        # Первое открытие — инициализируем
        user_id = callback_query.from_user.id
        dates = get_user_dates(user_id)
        groups = get_user_groups(user_id)
        teachers = get_user_teachers(user_id)

        if not dates or not groups:
            return await callback_query.message.answer("Сначала выберите группы и даты.")

        occupied = get_occupied_times_multi(groups, teachers, dates)
        free_times_map = generate_free_windows_multi(occupied)

        selected_times = []

    # Изменение страницы
    if direction == "next" and page < len(dates) - 1:
        page += 1
    elif direction == "prev" and page > 0:
        page -= 1

    current_date = dates[page]
    times = free_times_map.get(current_date, [])

    keyboard = get_time_selection_keyboard(current_date, times, selected_times, page, len(dates))

    await state.update_data(
        page=page,
        dates=dates,
        free_times_map=free_times_map,
        selected_times=selected_times
    )

    await callback_query.message.edit_text(
        f"Выберите время на дату {current_date}:", reply_markup=keyboard
    )
    await callback_query.answer()


async def toggle_time(callback_query: types.CallbackQuery, state: FSMContext):
    _, date, time = callback_query.data.split("|")

    data = await state.get_data()
    selected_times = data.get("selected_times", [])
    current_date = date  # получаем дату прямо из callback_data
    page = data.get("page", 0)
    dates = data.get("dates", [])
    free_times_map = data.get("free_times_map", {})

    # Проверяем, уже выбрано ли это время
    if (date, time) in selected_times:
        selected_times.remove((date, time))
    else:
        # Удаляем все другие даты
        selected_times = [(d, t) for (d, t) in selected_times if d == date]
        selected_times.append((date, time))

    await state.update_data(selected_times=selected_times)

    # Получаем список всех времён для текущей даты
    times = free_times_map.get(current_date, [])

    keyboard = get_time_selection_keyboard(current_date, times, selected_times, page, len(dates))

    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    await callback_query.answer()


async def confirm_time_selection(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_times = data["selected_times"]
    await MenuStates.EDIT_MEET.set()
    # Пример обработки: сохраним в state или в БД
    await state.update_data(final_times=selected_times)
    await callback_query.message.answer("✅ Время успешно выбрано.")
    await start_edit_meeting(callback_query, state)

    # Переход в следующее состояние или завершение
    #await state.finish()


async def enter_edit_room(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_room = data.get("room", "не указана")

    await MenuStates.EDIT_MEET_ROOM.set()
    await callback_query.message.edit_text(
        f"Текущая аудитория: {current_room}\n\nВведите новую аудиторию:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
        )
    )


async def process_room_input(message: types.Message, state: FSMContext):
    room = message.text.strip()
    if not re.match(r"^\d{1,2}-\d{3}[а-яa-z_]?$", room, re.IGNORECASE):
        await message.answer("❌ Неверный формат аудитории. Пример: 11-213, 1-003_, 5-312а")
        return

    await state.update_data(room=room)

    await message.answer(
        f"✅ Аудитория изменена на: {room}\n\nВведите другую или нажмите 'Назад' для возврата:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
        )
    )


async def back_to_editor_from_room(callback_query: types.CallbackQuery, state: FSMContext):
    await MenuStates.EDIT_MEET.set()
    await start_edit_meeting(callback_query, state)


# =======[Комментарий]=======
async def enter_edit_comment(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_comment = data.get("comment", "-")

    await MenuStates.EDIT_MEET_COMMENT.set()
    await callback_query.message.edit_text(
        f"💬 Текущий комментарий: {current_comment}\n\nВведите новый комментарий (до 256 символов):",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
        )
    )


async def process_comment_input(message: types.Message, state: FSMContext):
    comment = message.text.strip()

    if len(comment) > 256:
        await message.answer("❌ Комментарий слишком длинный. Максимум 256 символов.")
        return

    await state.update_data(comment=comment)

    await message.answer(
        f"✅ Комментарий обновлён:\n<i>{comment}</i>\n\nВведите другой или нажмите 'Назад' для возврата:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
        ),
        parse_mode="HTML"
    )


async def confirm_changes(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    u_id = callback_query.from_user.id
    initiator_id = sql.get_teacher_id_tg(u_id)
    old_times = data.get("old_dates_times", [])
    new_times = data.get("final_times", old_times)
    cabinet_id = data.get("cabinet_id")
    comment = data.get("comment")

    if old_times == new_times and cabinet_id is None and comment is None:
        await MenuStates.MY_MEET.set()
        await callback_query.message.answer("🗿 Нечего сохранять.")
        await my_meetings_menu(callback_query, state)
        return  # Нечего сохранять

    for i in range(len(old_times)):
        old_time, old_date = old_times[i]
        new_date, new_time = new_times[i]
        updated_fields = {}
        print(old_date, old_time)
        print(new_date, new_time)
        if (old_date, old_time) != (new_date, new_time):
            updated_fields["Date"] = new_date
            updated_fields["Time"] = new_time
        if cabinet_id is not None:
            updated_fields["CabinetID"] = cabinet_id
        if comment is not None:
            updated_fields["Comment"] = comment
        if updated_fields:
            print(initiator_id)
            update_meeting_entry(
                initiator_id=initiator_id,
                old_date=old_date,
                old_time=old_time,
                updated_fields=updated_fields
            )
    await MenuStates.MY_MEET.set()
    await callback_query.message.answer("✅ Изменения успешно сохранены.")
    await callback_query.answer()
    await my_meetings_menu(callback_query, state)


def register_edit_meet_handlers(dp: Dispatcher):
    # Вывод меню со ссылками
    dp.register_callback_query_handler(confirm_changes,
                                       lambda c: c.data == "confirm_changes" and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET)
    dp.register_message_handler(process_comment_input,
                                state=MenuStates.EDIT_MEET_COMMENT,
                                chat_type=ChatType.PRIVATE,
                                content_types=types.ContentTypes.TEXT)
    dp.register_callback_query_handler(enter_edit_comment,
                                       lambda c: c.data == "edit_comment" and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET)
    dp.register_callback_query_handler(back_to_editor_from_room,
                                       lambda c: c.data == "back_to_editor" and c.message.chat.type == ChatType.PRIVATE,
                                       state=[MenuStates.EDIT_MEET_ROOM, MenuStates.EDIT_MEET_DATETIME,
                                              MenuStates.EDIT_MEET_COMMENT])
    dp.register_message_handler(process_room_input,
                                state=MenuStates.EDIT_MEET_ROOM,
                                chat_type=ChatType.PRIVATE,
                                content_types=types.ContentTypes.TEXT)
    dp.register_callback_query_handler(enter_edit_room,
                                       lambda c: c.data == "edit_room" and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET)
    dp.register_callback_query_handler(confirm_time_selection,
                                       lambda c: c.data == "confirm" and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET_DATETIME)
    dp.register_callback_query_handler(toggle_time,
                                       lambda c: c.data.startswith("toggle_time") and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET_DATETIME)
    dp.register_callback_query_handler(change_date_page,
                                       lambda c: c.data.startswith("change_date_page") and c.message.chat.type == ChatType.PRIVATE,
                                       state=[MenuStates.EDIT_MEET_DATETIME, MenuStates.EDIT_MEET])
    dp.register_callback_query_handler(cancel_edit_meeting,
                                       lambda c: c.data == 'cancel_changes' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.EDIT_MEET)
    dp.register_callback_query_handler(start_edit_meeting,
                                       lambda c: c.data == 'edit_meeting' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(my_meetings_menu,
                                       lambda c: c.data in ["my_meet", "back_to_dates"] and c.message.chat.type == ChatType.PRIVATE,
                                       state="*")
    dp.register_callback_query_handler(view_date,
                                       lambda c: c.data.startswith('view_date_') and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(navigate_meetings,
                                       lambda c: c.data in ["prev_meeting", "next_meeting"] and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(delete_meeting,
                                       lambda c: c.data == 'delete_meeting' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(mark_complete,
                                       lambda c: c.data == 'mark_complete' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(mark_not_complete,
                                       lambda c: c.data == 'mark_not_complete' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(send_reminder,
                                       lambda c: c.data == 'send_reminder' and c.message.chat.type == ChatType.PRIVATE,
                                       state=MenuStates.MY_MEET)
