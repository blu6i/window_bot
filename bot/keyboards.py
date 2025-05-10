import os
from math import ceil

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from sql import get_user_groups, get_group_name, get_groups_id, get_user_dates, get_user_teachers

load_dotenv('config/.env')
TOKEN = os.getenv('ADMIN_ID')


def get_main_menu(u_id: int):
    keyboard = InlineKeyboardMarkup()

    # 1-я строка — 1 кнопка
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
    group_ids_on_page = data_list[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    if data_type == 'group':
        for group_id in group_ids_on_page:
            group_name = get_group_name(group_id)
            keyboard.insert(InlineKeyboardButton(
                text=group_name,
                callback_data=f'-{group_id}'  # Передаем ID
            ))
    else:
        for item in group_ids_on_page:
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


def get_inline_key_add_groups(user_id: int, data: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация клавиатуры выбора групп для добавления, с фильтрацией на лету."""

    # Получаем найденные группы (имена групп)
    found_groups = get_groups_id(data) or []

    # Получаем ID групп, которые у пользователя уже есть
    added_groups = get_user_groups(user_id)

    # Фильтруем найденные группы — берём только те, которых нет у пользователя
    not_added_groups = []
    for id_ in found_groups:
        if id_ not in added_groups:
            not_added_groups.append(id_)

    page_size = 12
    max_page = ceil(len(found_groups) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    items_on_page = found_groups[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    for id_ in items_on_page:
        if id_ in not_added_groups:
            keyboard.insert(InlineKeyboardButton(
                text=f'❌ {get_group_name(id_)}',
                callback_data=f"add_group_{id_}"
            ))
        else:
            keyboard.insert(InlineKeyboardButton(
                text=f'✅ {get_group_name(id_)}',
                callback_data=f"del_group_{id_}"
            ))

    if not_added_groups:
        keyboard.add(InlineKeyboardButton("➕ Добавить всё", callback_data="add_all_groups"))

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

    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups"))

    return keyboard
