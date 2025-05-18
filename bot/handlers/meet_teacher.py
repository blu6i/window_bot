import re
from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatType

import sql
from bot import MenuStates
from bot.handlers.common import notify_mp, generate_free_windows_multi
from bot.handlers.formating import get_rus_date
from bot.keyboards import get_edit_meeting_menu, get_time_selection_keyboard, generate_meeting_keyboard
from utils import logger


# =======[Меню с выбором даты для вывода]=======
async def my_meetings_menu(call: types.CallbackQuery, state: FSMContext, sub_text: str = ""):
    """Вывод меню 'Мои встречи'"""
    try:
        u_id = call.from_user.id
        teacher_id = sql.get_teacher_id_tg(u_id)

        if not teacher_id:
            return

        # Получаем СГРУППИРОВАННЫЕ данные
        meetings_raw = sql.get_meet_teacher(teacher_id)

        if not meetings_raw:
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))
            await call.message.edit_text("У вас пока нет встреч.", reply_markup=kb)
            return

        # Форматируем в структуру
        meetings_grouped = await format_meetings_for_state(meetings_raw)

        async with state.proxy() as data:
            data['meetings'] = meetings_grouped
            data['current_date_index'] = 0
            data['current_meeting_index'] = 0
            data['teacher_id'] = teacher_id

        await show_meeting_dates(call.message, state, sub_text)
        await MenuStates.MY_MEET.set()
    except Exception as e:
        logger.warning(f'Ошибка при выводе меню "Мои встречи": {e}')
    finally:
        await call.answer()


async def show_meeting_dates(message: types.Message, state: FSMContext, sub_text: str = ""):
    """Клавиатура дат встреч"""
    try:
        async with state.proxy() as data:
            dates = list(data['meetings'].keys())

        kb = types.InlineKeyboardMarkup(row_width=2)

        # Кнопки дат
        for i, date in enumerate(dates):
            icon = "🕒" if datetime.strptime(date, "%Y-%m-%d").date() >= datetime.now().date() else "✅"
            form_date, _ = get_rus_date(date)
            kb.add(types.InlineKeyboardButton(f"{icon} {form_date}", callback_data=f"view_date_{date}"))

        kb.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))

        await message.edit_text(f"{sub_text}\n"
                                f"\n"
                                f"📅 Выберите дату:", reply_markup=kb)
    except Exception as e:
        logger.warning(f'Ошибка при построении дат в меню "Мои встречи": {e}')


# =======[Вывод встреч за отдельную дату]=======
async def view_date(call: types.CallbackQuery, state: FSMContext):
    """Вывод страниц по датам"""
    try:
        date = call.data.split('_')[-1]

        async with state.proxy() as data:
            data['current_date'] = date
            data['current_meeting_index'] = 0

        await show_meet_details(call.message, state)
        await MenuStates.MY_MEET.set()

    except Exception as e:
        logger.warning(f'Ошибка при выводе страниц с датами в меню "Мои встречи": {e}')
    finally:
        await call.answer()


async def format_meetings_for_state(meetings_raw):
    """Форматирование для состояния"""
    try:
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
    except Exception as e:
        logger.warning(f'Ошибка при форматирования строки для состояния: {e}')


async def show_meet_details(msg: types.Message, state: FSMContext, sub_text: str = ""):
    """Детальный вывод встречи по дате и времени"""
    try:
        async with state.proxy() as data:
            date = data['current_date']
            meetings = data['meetings'][date]
            idx = data['current_meeting_index']
            teacher_id = data['teacher_id']

        meeting = meetings[idx]

        time = meeting['time']
        groups = meeting['groups']
        teachers = meeting['teachers']
        cabinet_id = meeting['cabinet_id']
        comment = meeting['comment']
        is_completed = meeting['is_completed']
        initiator_id = meeting['initiator_id']
        group_names = "-"
        if groups:
            group_names = ""
            for group in groups:
                group_names += f"{sql.get_group_name(group)}\n"

        teacher_names = "-"
        if teachers:
            teacher_names = ""
            for teacher in teachers:
                teacher_names += f"{sql.get_teacher_name(teacher)}\n"

        cabinet_info = cabinet_id or "-"
        initiator_name = "Вы" if initiator_id == teacher_id else sql.get_teacher_name(initiator_id)
        status_emoji = '🔴' if is_completed else '🟢'
        status_text = 'Завершено' if is_completed else 'Ожидается'
        form_date, day = get_rus_date(date)
        formatted_text = f"""
⚡ <b>Инициатор:</b>\n{initiator_name}\n
📅 <b>Дата:</b>\n{form_date} ({day})\n
⏰ <b>Время:</b>\n{time}\n
🗺️ <b>Место проведение:</b>\n{cabinet_info}
👥 <b>Группы:</b>\n{group_names}
🧑‍🏫 <b>Преподаватели:</b>\n{teacher_names}
💬 <b>Комментарий:</b>\n{comment or '-'}
{status_emoji} <b>Статус:</b> {status_text}
        """

        if sub_text:
            formatted_text += f"\n\n{sub_text}"

        kb = generate_meeting_keyboard(
            meeting=meeting,
            idx=idx,
            meetings_count=len(meetings),
            teacher_id=teacher_id
        )

        await msg.edit_text(formatted_text,
                            parse_mode="HTML",
                            reply_markup=kb)
    except Exception as e:
        logger.warning(f'Ошибка при выводе детальной информации об встрече: {e}')


async def navigate_meetings(call: types.CallbackQuery, state: FSMContext):
    """Кнопки навигации"""
    try:
        delta = 1 if call.data == 'next_meeting' else -1

        async with state.proxy() as data:
            data['current_meeting_index'] += delta

            # Защита от выхода за границы
            date = data['current_date']
            meetings_count = len(data['meetings'][date])
            data['current_meeting_index'] = max(0, min(meetings_count - 1, data['current_meeting_index']))

        await show_meet_details(call.message, state)
    except Exception as e:
        logger.warning(f'Ошибка при навигации встреч: {e}')
    finally:
        await call.answer()


async def delete_meeting(call: types.CallbackQuery, state: FSMContext):
    """Удаление встречи"""
    try:
        async with state.proxy() as data:
            date = data['current_date']
            meetings = data['meetings'][date]
            idx = data['current_meeting_index']
            meeting = meetings[idx]

            time = meeting['time']
            initiator_id = meeting['initiator_id']

        # 1. Удаление из БД
        sql.remove_meeting_group(date, time, initiator_id)

        async with state.proxy() as data:
            # 2. Обновляем локальные данные
            del data['meetings'][date][idx]

            # 3. Проверяем, остались ли встречи на эту дату
            if not data['meetings'][date]:
                del data['meetings'][date]

            # 4. Защита: если мы удалили последнюю встречу на странице
            if 'current_meeting_index' in data and idx >= len(data['meetings'].get(date, [])):
                data['current_meeting_index'] = max(0, idx - 1)

        # 5. Если дата всё ещё существует в словаре - показываем новую встречу
        async with state.proxy() as data:
            text = "🗑️ Встреча удалена"
            if date in data['meetings']:
                await show_meet_details(call.message, state, text)
            else:
                await show_meeting_dates(call.message, state, text)
                await MenuStates.MY_MEET.set()

    except Exception as e:
        logger.warning(f'Ошибка при удалении встречи: {e}')
    finally:
        await call.answer()


async def mark_complete(call: types.CallbackQuery, state: FSMContext):
    """Пометка как прошедшей"""
    try:
        async with state.proxy() as data:
            date = data['current_date']
            meetings = data['meetings'][date]
            idx = data['current_meeting_index']
            meeting = meetings[idx]

            # Получаем ID встречи из словаря
            initiator_id = meeting.get('initiator_id')

        # 1. Обновляем в БД
        success = sql.update_completed(date, meeting['time'], initiator_id)

        if not success:
            logger.error("Ошибка при обновлении статуса встречи")
            return

        async with state.proxy() as data:
            for i, m in enumerate(data['meetings'][date]):
                if m['time'] == meeting['time'] and m['initiator_id'] == initiator_id:
                    data['meetings'][date][i]['is_completed'] = 1

        # 3. Показываем обновлённые данные
        await show_meet_details(call.message, state)
    except Exception as e:
        logger.warning(f'Ошибка при отметке прошедшей встречи: {e}')
    finally:
        await call.answer()


async def mark_not_complete(call: types.CallbackQuery, state: FSMContext):
    """Пометка как не прошедшей"""
    try:
        async with state.proxy() as data:
            date = data['current_date']
            meetings = data['meetings'][date]
            idx = data['current_meeting_index']
            meeting = meetings[idx]

            time = meeting.get('time')
            initiator_id = meeting.get('initiator_id')

        # 1. Обновляем в БД
        success = sql.update_not_completed(date, time, initiator_id)

        if not success:
            logger.error("Ошибка при обновлении статуса встречи")
            return

        # 2. Обновляем все локально
        async with state.proxy() as data:
            for i, m in enumerate(data['meetings'][date]):
                if m['time'] == time and m['initiator_id'] == initiator_id:
                    data['meetings'][date][i]['is_completed'] = 0

        # 3. Показываем обновлённые данные
        await show_meet_details(call.message, state)
    except Exception as e:
        logger.warning(f"Ошибка при отметке не прошедшей встречи: {e}")
    finally:
        await call.answer()


async def send_reminder(call: types.CallbackQuery, state: FSMContext):
    """Напоминание о встрече"""
    not_notified_message = ''
    try:
        async with state.proxy() as data:
            date = data.get("current_date")
            index = data.get("current_meeting_index")
            meetings = data.get("meetings", {})
            if not date or date not in meetings or index >= len(meetings[date]):
                await call.answer("❌ Невозможно найти данные встречи.")
                return

            meeting = meetings[date][index]
            time = meeting.get("time")
            comment = meeting.get("comment", "")
            cabinet = meeting.get("cabinet_id", "")
            group_id = meeting.get("groups")
            group_name = ""
            if group_id:
                for group in group_id:
                    group_name += f"\n• {sql.get_group_name(group)}"
            teacher_id = meeting.get("teachers")
            teacher_name = ""
            if teacher_id:
                for teacher in teacher_id:
                    teacher_name += f"\n• {sql.get_teacher_name(teacher)}"
            # Текст оповещения
            form_date, day = get_rus_date(date)
            text = (
                f"🔔 Напоминание о встрече:\n"
                f"📅 Дата:\n{form_date} ({day})\n"
                f"⏰ Время:\n{time}\n"
                f"\n"
                f"🗺️ Место проведение:\n{cabinet or 'Не указана'}\n"
                f"\n"
                f"👥 Группа:{group_name}\n"
                f"👩🏻‍🏫 Преподаватель:{teacher_name}\n"
                f"\n"
                f"💬 Комментарий:\n{comment or 'Не указан'}"
            )
            # Отправляем уведомление
            unnotified_groups, unnotified_teachers = await notify_mp(
                group_ids=group_id if group_id else [],
                teacher_ids=teacher_id if teacher_id else [],
                message=text
            )

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
    except Exception as e:
        logger.warning(f'Ошибка при отправке напоминания: {e}')
    finally:
        await show_meet_details(call.message, state, not_notified_message)
        await call.answer()


# =======[Редактор встречи]=======
async def start_edit_meeting(call: types.CallbackQuery, state: FSMContext):
    """Меню редактора"""
    try:
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
                data['old_dates_times'] = [(date, meeting['time'])]

        # Ожидаем, что теперь можно выбрать, что редактировать
        await call.message.edit_text("🔁 Выберите, что редактировать:", reply_markup=get_edit_meeting_menu())
        await MenuStates.EDIT_MEET.set()
    except Exception as e:
        logger.warning(f'Ошибка при выводе меню редактирования: {e}')
    finally:
        await call.answer()


async def cancel_edit_meeting(call: types.CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    try:
        async with state.proxy() as data:
            if 'original_meeting' in data:
                date = data['current_date']
                idx = data['current_meeting_index']
                data['meetings'][date][idx] = data['original_meeting']
                del data['original_meeting']
        await MenuStates.MY_MEET.set()
        await call.message.answer("❌ Изменения отменены.")
        await show_meet_details(call.message, state)
    except Exception as e:
        logger.warning(f'Ошибка при отмене изменения редактирования: {e}')
    finally:
        await call.answer()


# =======[Редактирование даты и времени]=======
async def change_date_page(call: types.CallbackQuery, state: FSMContext):
    """Вывод страниц и свап страниц у дат"""
    try:
        parts = call.data.split("|")
        direction = parts[1] if len(parts) > 1 else None  # None значит "первое открытие"

        data = await state.get_data()

        page = data.get("page", 0)
        dates = data.get("dates", [])
        free_times_map = data.get("free_times_map", {})
        selected_times = data.get("selected_times", [])
        await MenuStates.EDIT_MEET_DATETIME.set()
        if not dates or not free_times_map:
            # Первое открытие — инициализируем
            user_id = call.from_user.id
            dates = sql.get_user_dates(user_id)
            groups = sql.get_user_groups(user_id)
            teachers = sql.get_user_teachers(user_id)
            free_times_map = generate_free_windows_multi(groups, teachers, dates)

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

        await call.message.edit_text(
            f"Выберите время и дату {current_date}:", reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f'Ошибка при выводе или свапе страниц даты и времени при редактировании их: {e}')
    finally:
        await call.answer()


async def toggle_time(call: types.CallbackQuery, state: FSMContext):
    """Выбор даты"""
    try:
        _, date, time = call.data.split("|")

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

        await call.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Ошибка выбора нового времени при редактировании: {e}")
    finally:
        await call.answer()


async def confirm_time_selection(call: CallbackQuery, state: FSMContext):
    """Принять изменения"""
    try:
        data = await state.get_data()
        selected_times = data["selected_times"]
        await MenuStates.EDIT_MEET.set()
        await state.update_data(final_times=selected_times)
        await call.message.answer("✅ Время успешно выбрано.")
        await start_edit_meeting(call, state)
    except Exception as e:
        logger.warning(f'Ошибка при принятии изменений во время редактирования времени: {e}')
    finally:
        await call.answer()


# =======[Ввод новой аудитории]=======
async def change_room(call: types.CallbackQuery, state: FSMContext):
    """Изменение аудитории"""
    try:
        data = await state.get_data()
        current_room = data.get("room", "не указана")

        await MenuStates.EDIT_MEET_ROOM.set()
        await call.message.edit_text(
            f"Текущее место проведение: {current_room}\n"
            f"\n"
            f"Введите новое место проведение:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
            )
        )
    except Exception as e:
        logger.warning(f'Ошибка при переходе в смену аудитории во время редактирования: {e}')
    finally:
        await call.answer()


async def process_room_input(msg: types.Message, state: FSMContext):
    """Проверка ввода"""
    try:
        room = msg.text.strip()
        """if not re.match(r"^\d{1,2}-\d{3}[а-яa-z_]?$", room, re.IGNORECASE):
            await msg.answer("❌ Неверный формат аудитории. Пример: 11-213, 1-003_, 5-312а")
            return"""

        await state.update_data(room=room)

        await msg.answer(
            f"✅ Место проведение изменено на: {room}\n"
            f"\n"
            f"Введите другое или нажмите 'Назад' для возврата:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
            )
        )
    except Exception as e:
        logger.warning(f"Ошибка при проверке нового комментария во время редактирования: {e}")


async def back_to_editor(call: types.CallbackQuery, state: FSMContext):
    try:
        await MenuStates.EDIT_MEET.set()
        await start_edit_meeting(call, state)
    except Exception as e:
        logger.warning(f"Ошибка при возврате в меню редактирования: {e}")
    finally:
        await call.answer()


# =======[Комментарий]=======
async def enter_edit_comment(call: types.CallbackQuery, state: FSMContext):
    """Редактор комментария"""
    try:
        data = await state.get_data()
        current_comment = data.get("comment", "-")

        await MenuStates.EDIT_MEET_COMMENT.set()
        await call.message.edit_text(
            f"💬 Текущий комментарий: {current_comment}\n\nВведите новый комментарий (до 256 символов):",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
            )
        )
    except Exception as e:
        logger.warning(f'Ошибка при переходе в редактор комментария: {e}')
    finally:
        await call.answer()


async def process_comment_input(msg: types.Message, state: FSMContext):
    """Проверка вводимого комментария"""
    try:
        comment = msg.text.strip()

        if len(comment) > 256:
            await msg.answer("❌ Комментарий слишком длинный. Максимум 256 символов.")
            return

        await state.update_data(comment=comment)

        await msg.answer(
            f"✅ Комментарий обновлён:\n<i>{comment}</i>\n\nВведите другой или нажмите 'Назад' для возврата:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor")
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f'Ошибка при проверке комментария во время редактирования: {e}')


# =======[Принятия всех настроек]=======
async def confirm_changes(call: types.CallbackQuery, state: FSMContext):
    """Принятие всех настрое"""
    text = ''
    try:
        data = await state.get_data()
        u_id = call.from_user.id
        initiator_id = sql.get_teacher_id_tg(u_id)
        old_times = data.get("old_dates_times", [])
        new_times = data.get("final_times", old_times)
        cabinet_id = data.get("room")
        comment = data.get("comment")

        if old_times == new_times and cabinet_id is None and comment is None:
            await MenuStates.MY_MEET.set()
            text = "🗿 Нечего сохранять."
            return  # Нечего сохранять

        for i in range(len(old_times)):
            old_date, old_time = old_times[i]
            new_date, new_time = new_times[i]
            updated_fields = {}
            if (old_date, old_time) != (new_date, new_time):
                updated_fields["Date"] = new_date
                updated_fields["Time"] = new_time
            if cabinet_id is not None:
                updated_fields["CabinetID"] = cabinet_id
            if comment is not None:
                updated_fields["Comment"] = comment
            if updated_fields:
                sql.update_meeting_entry(
                    initiator_id=initiator_id,
                    old_date=old_date,
                    old_time=old_time,
                    updated_fields=updated_fields
                )
        await MenuStates.MY_MEET.set()
        text = "✅ Изменения успешно сохранены."
    except Exception as e:
        logger.warning(f'Ошибка во время принятия редактирования: {e}')
    finally:
        await call.answer()
        await my_meetings_menu(call, state, text)


def register_edit_meet_handlers(dp: Dispatcher):
    # Вывод меню со ссылками
    dp.register_callback_query_handler(
        confirm_changes,
        lambda c: c.data == "confirm_changes" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET
    )
    dp.register_message_handler(
        process_comment_input,
        state=MenuStates.EDIT_MEET_COMMENT,
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT
    )
    dp.register_callback_query_handler(
        enter_edit_comment,
        lambda c: c.data == "edit_comment" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET
    )
    dp.register_callback_query_handler(
        back_to_editor,
        lambda c: c.data == "back_to_editor" and c.message.chat.type == ChatType.PRIVATE,
        state=[MenuStates.EDIT_MEET_ROOM, MenuStates.EDIT_MEET_DATETIME,
               MenuStates.EDIT_MEET_COMMENT]
    )
    dp.register_message_handler(
        process_room_input,
        state=MenuStates.EDIT_MEET_ROOM,
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT
    )
    dp.register_callback_query_handler(
        change_room,
        lambda c: c.data == "edit_room" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET
    )
    dp.register_callback_query_handler(
        confirm_time_selection,
        lambda c: c.data == "confirm" and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET_DATETIME
    )
    dp.register_callback_query_handler(
        toggle_time,
        lambda c: c.data.startswith("toggle_time") and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET_DATETIME
    )
    dp.register_callback_query_handler(
        change_date_page,
        lambda c: c.data.startswith("change_date_page") and c.message.chat.type == ChatType.PRIVATE,
        state=[MenuStates.EDIT_MEET_DATETIME, MenuStates.EDIT_MEET]
    )
    dp.register_callback_query_handler(
        cancel_edit_meeting,
        lambda c: c.data == 'cancel_changes' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.EDIT_MEET
    )
    dp.register_callback_query_handler(
        start_edit_meeting,
        lambda c: c.data == 'edit_meeting' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        my_meetings_menu,
        lambda c: c.data in ["my_meet", "back_to_dates"] and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_callback_query_handler(
        view_date,
        lambda c: c.data.startswith('view_date_') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        navigate_meetings,
        lambda c: c.data in ["prev_meeting", "next_meeting"] and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        delete_meeting,
        lambda c: c.data == 'delete_meeting' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        mark_complete,
        lambda c: c.data == 'mark_complete' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        mark_not_complete,
        lambda c: c.data == 'mark_not_complete' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
    dp.register_callback_query_handler(
        send_reminder,
        lambda c: c.data == 'send_reminder' and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.MY_MEET
    )
