import os
from math import ceil

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

from bot.handlers.formating import get_rus_date
from sql import get_user_groups, get_group_name, get_groups_id, get_user_dates, get_user_teachers
import sql

load_dotenv('config/.env')
TOKEN = os.getenv('ADMIN_ID')


def get_main_menu(u_id: int):
    keyboard = InlineKeyboardMarkup()

    # 1-я строка — 1 кнопка
    if sql.is_teacher_authorized(u_id):
        keyboard.row(InlineKeyboardButton("🪟 Окна в расписании", callback_data="menu_teacher_window"))
    else:
        keyboard.row(InlineKeyboardButton("🪟 Окна в расписании", callback_data="menu_windows"))

    group_button = InlineKeyboardButton(
        "👥 Группы",
        callback_data="menu_groups"
    )
    date_button = InlineKeyboardButton(
        "📅 Даты",
        callback_data="menu_dates"
    )
    keyboard.row(group_button, date_button)

    keyboard.row(InlineKeyboardButton("👨‍🏫 Преподаватели", callback_data="menu_teachers"))

    if sql.is_teacher_authorized(u_id):
        keyboard.row(InlineKeyboardButton("🪟 Мои встречи", callback_data="my_meet"))

    keyboard.row(InlineKeyboardButton("ℹ️ Помощь", url="teletype.in/@pepegeshka/sFjYdnH8AVG"))

    keyboard.row(InlineKeyboardButton("🔗 Ссылки быстрого доступа", callback_data="menu_links"))

    # Доп. строка для админа
    if u_id == int(TOKEN):
        keyboard.row(InlineKeyboardButton("🔄 Обновить расписание", callback_data="refresh_schedule"))

    return keyboard


def get_menu_link():
    """Выводит меню со ссылками (инлайн-кнопки)"""
    keyboard = InlineKeyboardMarkup()

    keyboard.row(
        InlineKeyboardButton("📅 Бот ВятГУ", url="https://t.me/Vyatsu_chatbot"),
        InlineKeyboardButton("📌 ЛК ВятГУ", url="https://new.vyatsu.ru/account/")
    )

    keyboard.row(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )

    return keyboard


def get_inline_key_list(user_id: int, data_type: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация инлайн-кнопок с постраничным выводом для пользователя"""
    if data_type == 'date':
        # Получаем дат пользователя
        data_list = get_user_dates(user_id)
    elif data_type == 'teacher':
        data_list = get_user_teachers(user_id)
    else:
        # Получаем ID всех групп пользователя
        data_list = get_user_groups(user_id)

    page_size = 12
    max_page = ceil(len(data_list) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    data_ids_on_page = data_list[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    if data_type == 'group':
        for group_id in data_ids_on_page:
            group_name = get_group_name(group_id)
            keyboard.insert(InlineKeyboardButton(
                text=group_name,
                callback_data=f'-{group_id}'  # Передаем ID
            ))
    elif data_type == 'teacher':
        for teacher in data_ids_on_page:
            teacher_name = sql.get_teacher_name(teacher)
            keyboard.insert(InlineKeyboardButton(
                text=teacher_name,
                callback_data=f'-{teacher}'  # Передаем ID
            ))
    else:
        for item in data_ids_on_page:
            date_format, _ = get_rus_date(item)
            keyboard.insert(InlineKeyboardButton(
                text=date_format,
                callback_data=f'-{item}'  # Передаем ID
            ))

    if data_list:
        keyboard.add(InlineKeyboardButton(
            "🧹 Очистить всё",
            callback_data=f"clear_all_{data_type}"
        ))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=f"prev_page_{data_type}_{page - 1}"
        ))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(
            "➡️ Вперёд",
            callback_data=f"next_page_{data_type}_{page + 1}"
        ))

    if nav_buttons:
        keyboard.row(*nav_buttons)
    keyboard.row(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    return keyboard


def get_inline_key_add_info(u_id: int, data: str, type_: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация клавиатуры выбора групп для добавления, с фильтрацией на лету."""
    if type_ == 'groups':
        # Получаем найденные группы (имена групп)
        found_info = get_groups_id(data)['groups'] or []
        found_info.sort()
        # Получаем ID групп, которые у пользователя уже есть
        add_info = get_user_groups(u_id)
    elif type_ == 'teachers':
        # Получаем найденные группы (имена групп)
        found_info = sql.get_teachers_sub_id(data)['teachers'] or []
        found_info.sort()
        # Получаем ID групп, которые у пользователя уже есть
        add_info = sql.get_user_teachers(u_id)

    # Фильтруем найденные группы — берём только те, которых нет у пользователя
    not_added_info = []
    for id_ in found_info:
        if id_ not in add_info:
            not_added_info.append(id_)

    page_size = 12
    max_page = ceil(len(found_info) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    items_on_page = found_info[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)
    if type_ == 'groups':
        for id_ in items_on_page:
            if id_ in not_added_info:
                keyboard.insert(InlineKeyboardButton(
                    text=f'{get_group_name(id_)}',
                    callback_data=f"add_{type_}_{id_}"
                ))
            else:
                keyboard.insert(InlineKeyboardButton(
                    text=f'✅ {get_group_name(id_)}',
                    callback_data=f"del_{type_}_{id_}"
                ))
    elif type_ == 'teachers':
        for id_ in items_on_page:
            if id_ in not_added_info:
                keyboard.insert(InlineKeyboardButton(
                    text=f'{sql.get_teacher_name(id_)}',
                    callback_data=f"add_{type_}_{id_}"
                ))
            else:
                keyboard.insert(InlineKeyboardButton(
                    text=f'✅ {sql.get_teacher_name(id_)}',
                    callback_data=f"del_{type_}_{id_}"
                ))

    if not_added_info:
        keyboard.add(InlineKeyboardButton("➕ Добавить всё", callback_data=f"add_all_{type_}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"prev_page_add_{page - 1}"
        ))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(
            "➡️ Вперёд", callback_data=f"next_page_add_{page + 1}"
        ))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_{type_}"))

    return keyboard


def get_edit_meeting_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✏️ Изменить дату и время", callback_data="change_date_page"),
        InlineKeyboardButton("🗺️ Изменить место", callback_data="edit_room"),
        InlineKeyboardButton("💬 Изменить комментарий", callback_data="edit_comment"),
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_changes"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_changes")
    )
    return keyboard


def get_time_selection_keyboard(
        date: str,
        times: list,
        selected_times: list,
        page: int,
        total_pages: int
):
    keyboard = InlineKeyboardMarkup(row_width=2)

    for time in times:
        is_selected = (date, time) in selected_times
        text = f"{'✅' if is_selected else ''}{time}"
        callback_data = f"toggle_time|{date}|{time}"
        keyboard.insert(InlineKeyboardButton(text=text, callback_data=callback_data))

    # Кнопки листания страниц
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅", callback_data="change_date_page|prev"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("➡", callback_data="change_date_page|next"))

    if navigation_buttons:
        keyboard.row(*navigation_buttons)

    # Кнопки управления
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_editor"),
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")
    )
    return keyboard


def get_free_windows_keyboard(
        current_date: str,
        free_times: list,
        selected: dict,
        page: int,
        total_pages: int
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)

    # Добавляем кнопки времени
    for time in free_times:
        is_selected = selected.get(current_date, {}).get(time, False)
        text = f"{time} ✅" if is_selected else time
        button_key = f"{current_date}_{time}"
        callback_data = f"del_{button_key}" if is_selected else f"add_{button_key}"
        kb.add(InlineKeyboardButton(text=text, callback_data=callback_data))

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Назад", callback_data="prev_page"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡", callback_data="next_page"))
    if nav_buttons:
        kb.row(*nav_buttons)

    # Подтверждение и возврат
    kb.add(InlineKeyboardButton("Подтвердить время", callback_data="confirm_time"))
    kb.add(InlineKeyboardButton("Назад в меню", callback_data="back_to_menu"))

    return kb


def generate_edit_menu_keyboard(cabinet: str = None, comment: str = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()

    audi_text = "🗺️ Место проведение"
    if cabinet:
        audi_text += " ✅"

    kb.add(InlineKeyboardButton(audi_text, callback_data="edit_audi"))

    comment_text = "📢 Комментарий"
    if comment:
        comment_text += " ✅"

    kb.add(InlineKeyboardButton(comment_text, callback_data="edit_comment"))

    kb.add(InlineKeyboardButton("✉️ Подтвердить", callback_data="finalize"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_window"))

    return kb


def generate_meeting_keyboard(meeting: dict,
                              idx: int,
                              meetings_count: int,
                              teacher_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)

    is_completed = meeting["is_completed"]
    initiator_id = meeting["initiator_id"]
    # Кнопка завершения
    if not is_completed:
        kb.add(InlineKeyboardButton("✅ Отметить как пройденное", callback_data="mark_complete"))
    else:
        kb.add(InlineKeyboardButton("❌ Отметить как не пройденное", callback_data="mark_not_complete"))

    # Кнопки редактирования/удаления
    if initiator_id == teacher_id:
        kb.add(InlineKeyboardButton("🗑️ Удалить встречу", callback_data="delete_meeting"))
        kb.add(InlineKeyboardButton("🔁 Редактировать встречу", callback_data="edit_meeting"))

    kb.add(InlineKeyboardButton("🔔 Отправить напоминание", callback_data="send_reminder"))

    # Навигация
    if meetings_count > 1:
        nav_buttons = []
        if idx > 0:
            nav_buttons.append(InlineKeyboardButton("⬅ Предыдущее", callback_data="prev_meeting"))
        if idx < meetings_count - 1:
            nav_buttons.append(InlineKeyboardButton("Следующее ➡", callback_data="next_meeting"))
        kb.row(*nav_buttons)

    kb.add(InlineKeyboardButton("🔙 Назад к датам", callback_data="back_to_dates"))

    return kb
