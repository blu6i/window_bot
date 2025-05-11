from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

import sql
from bot import MenuStates


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


async def format_meetings_for_state(meetings):
    grouped = {}

    for meeting in meetings:
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
            'initiator_id': initiator_id,
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

    kb.add(types.InlineKeyboardButton("🔁 Редактировать встречу", callback_data="edit_meeting"))
    kb.add(types.InlineKeyboardButton("🔔 Отправить напоминание", callback_data="send_reminder"))
    kb.add(types.InlineKeyboardButton("🔙 Назад к датам", callback_data="back_to_dates"))

    # Навигация по встречам
    if len(meetings) > 1:
        nav_buttons = []
        if idx > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅ Предыдущее", callback_data="prev_meeting"))
        if idx < len(meetings) - 1:
            nav_buttons.append(types.InlineKeyboardButton("Следующее ➡", callback_data="next_meeting"))
        kb.row(*nav_buttons)

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


async def edit_meeting(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        date = data['current_date']
        meetings = data['meetings'][date]
        idx = data['current_meeting_index']
        meeting = meetings[idx]

        # Сохраняем ID встречи и дату для последующего обновления
        data['edit_meeting_id'] = meeting['meeting_id']
        data['edit_date'] = meeting['date']
        data['edit_time'] = meeting['time']
        data['edit_groups'] = meeting['groups']
        data['edit_teachers'] = meeting['teachers']
        data['edit_cabinet'] = meeting['cabinet_id']
        data['edit_comment'] = meeting['comment']

    # Отображаем меню редактирования
    await show_edit_meeting_menu(callback.message, state)
    await MenuStates.EDIT_MEET.set()
    await callback.answer()


async def show_edit_meeting_menu(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        date = data['edit_date']
        time = data['edit_time']
        cabinet = data.get('edit_cabinet')
        comment = data.get('edit_comment', '')

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(types.InlineKeyboardButton("⏰ Изменить время", callback_data="edit_change_time"))
    kb.add(types.InlineKeyboardButton("🏫 Аудитория", callback_data="edit_change_cabinet"))
    kb.add(types.InlineKeyboardButton("📢 Комментарий", callback_data="edit_change_comment"))
    kb.add(types.InlineKeyboardButton("✉️ Подтвердить изменения", callback_data="edit_save"))
    kb.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="edit_cancel"))

    text = f"""
    ✏️ <b>Редактирование встречи</b>
    
    📅 Дата: {date}
    ⏰ Время: {time}
    🏫 Аудитория: {cabinet or 'Не указана'}
    📢 Комментарий: {comment or 'Нет'}
    """

    try:
        await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def edit_save(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        meeting_id = data['edit_meeting_id']
        new_cabinet = data.get('edit_cabinet')
        new_comment = data.get('edit_comment')

    success = sql.update_meeting_in_db(meeting_id, new_cabinet, new_comment)

    if success:
        # Обновляем данные в состоянии "мои встречи"
        async with state.proxy() as data:
            date = data['edit_date']
            old_idx = data.get('current_meeting_index', 0)
            meetings_list = data['meetings'].get(date, [])

            for i, m in enumerate(meetings_list):
                if m['meeting_id'] == meeting_id:
                    m['cabinet_id'] = new_cabinet
                    m['comment'] = new_comment
                    break

        await callback.message.edit_text("✅ Встреча успешно обновлена")
        await show_meeting_details(callback.message, state)
        await MenuStates.MY_MEET.set()
    else:
        await callback.answer("❌ Ошибка при сохранении изменений", show_alert=True)


async def edit_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔄 Редактирование отменено")
    await show_meeting_details(callback.message, state)
    await MenuStates.MY_MEET.set()
    await callback.answer()


def register_link_handlers(dp: Dispatcher):
    # Вывод меню со ссылками
    dp.register_callback_query_handler(my_meetings_menu,
                                       lambda c: c.data in ["my_meet", "back_to_dates"],
                                       state="*")
    dp.register_callback_query_handler(view_date,
                                       lambda c: c.data.startswith('view_date_'),
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(navigate_meetings,
                                       lambda c: c.data in ["prev_meeting", "next_meeting"],
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(delete_meeting,
                                       lambda c: c.data == 'delete_meeting',
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(mark_complete,
                                       lambda c: c.data == 'mark_complete',
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(mark_not_complete,
                                       lambda c: c.data == 'mark_not_complete',
                                       state=MenuStates.MY_MEET)
    dp.register_callback_query_handler(edit_meeting,
                                       lambda c: c.data == 'edit_meeting',
                                       state=MenuStates.MY_MEET)

    dp.register_callback_query_handler(send_reminder,
                                       lambda c: c.data == 'send_reminder',
                                       state=MenuStates.MY_MEET)

    dp.register_callback_query_handler(edit_save,
                                       lambda c: c.data == 'edit_save',
                                       state=MenuStates.EDIT_MEET)

    dp.register_callback_query_handler(edit_cancel,
                                       lambda c: c.data == 'edit_cancel',
                                       state=MenuStates.EDIT_MEET)
