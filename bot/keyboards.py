import os
from math import ceil

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from sql import get_user_groups, get_group_name, get_groups, get_groups_id, get_user_dates

load_dotenv('config/.env')
TOKEN = os.getenv('ADMIN_ID')


def get_main_menu(u_id: int):
    """ Выводит основное меню """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    buttons = [
        ['🪟 Окна в расписании'],
        ['👥 Изменить группы', '📅 Изменить даты'],
        ['ℹ️ Помощь'],
        ['🔗 Ссылки быстрого доступа']
    ]
    groups = get_user_groups(u_id)
    if not groups:
        buttons[1] = ['👥 Добавить группы', '📅 Добавить даты']
    if u_id == int(TOKEN):
        buttons.append(['🔄 Обновить расписание'])
    for row in buttons:
        keyboard.row(*[KeyboardButton(btn) for btn in row])

    return keyboard


def get_menu_link():
    """ Выводит меню со ссылками """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        ["📅 Расписание", "📝 Отметка"],
        ["📌 Личный кабинет"],
        ["🔙 Назад"]
    ]
    for row in buttons:
        keyboard.row(*[KeyboardButton(btn) for btn in row])

    return keyboard


def get_inline_key_list(user_id: int, data_type: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация инлайн-кнопок с постраничным выводом для пользователя"""
    if data_type == 'date':
        # Получаем дат пользователя
        data_list = get_user_dates(user_id)
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

    return keyboard


def get_inline_key_add_groups(user_id: int, data: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация клавиатуры выбора групп для добавления, с фильтрацией на лету."""

    # Получаем найденные группы (имена групп)
    found_groups = get_groups_id(data) or []

    # Получаем ID групп, которые у пользователя уже есть
    user_group_id = get_user_groups(user_id)

    # Фильтруем найденные группы — берём только те, которых нет у пользователя
    available_groups = []
    for id_ in found_groups:
        if id_ not in user_group_id:
            available_groups.append(id_)

    page_size = 12
    max_page = ceil(len(available_groups) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    items_on_page = available_groups[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    for id_ in items_on_page:
        keyboard.insert(InlineKeyboardButton(
            text=get_group_name(id_),
            callback_data=f"add_group_{id_}"
        ))

    if available_groups:
        keyboard.add(InlineKeyboardButton("➕ Добавить всё", callback_data="add_all_groups"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"prev_page_add_{page-1}"
        ))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(
            "➡️ Вперёд", callback_data=f"next_page_add_{page+1}"
        ))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups"))

    return keyboard


