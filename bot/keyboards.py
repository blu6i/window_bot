import os
from math import ceil

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

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
        keyboard.row(InlineKeyboardButton("🪟 Мои встречи", callback_data="list_meet"))

    keyboard.row(InlineKeyboardButton("ℹ️ Помощь", callback_data="help"))

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
            keyboard.insert(InlineKeyboardButton(
                text=item,
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
        found_info = get_groups_id(data) or []
        # Получаем ID групп, которые у пользователя уже есть
        add_info = get_user_groups(u_id)
    elif type_ == 'teachers':
        # Получаем найденные группы (имена групп)
        found_info = []
        for teacher in sql.get_teachers_sub(data):
            found_info.append(teacher['id'])
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
                    text=f'❌ {get_group_name(id_)}',
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
                    text=f'❌ {sql.get_teacher_name(id_)}',
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
