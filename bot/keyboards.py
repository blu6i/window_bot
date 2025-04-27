import os

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

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


def get_inline_key_list(items: list[tuple[int, str]], data_type: str, page: int = 0) -> InlineKeyboardMarkup:
    """Генерация инлайн-кнопок с постраничным выводом"""
    from math import ceil

    page_size = 12
    max_page = ceil(len(items) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    items_on_page = items[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    for group_id, group_name in items_on_page:
        keyboard.insert(InlineKeyboardButton(
            text=group_name,
            callback_data=f'-{group_id}'  # Теперь передаём ID группы
        ))

    if items:
        keyboard.add(InlineKeyboardButton(
            "🧹 Очистить всё",
            callback_data=f"clear_all_{data_type}"
        ))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=f"prev_page_{data_type}_{page-1}"
        ))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(
            "➡️ Вперёд",
            callback_data=f"next_page_{data_type}_{page+1}"
        ))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    return keyboard


def get_inline_key_add_groups(groups: list[str], page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора групп для добавления."""
    from math import ceil

    page_size = 12
    max_page = ceil(len(groups) / page_size) - 1
    page = max(0, min(page, max_page))

    start_i = page * page_size
    end_i = start_i + page_size
    items_on_page = groups[start_i:end_i]

    keyboard = InlineKeyboardMarkup(row_width=2)

    for group in items_on_page:
        keyboard.insert(InlineKeyboardButton(text=group, callback_data=f"add_group_{group}"))

    if groups:
        keyboard.add(InlineKeyboardButton("➕ Добавить всё", callback_data="add_all_groups"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"prev_page_add_{page-1}"))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton("➡️ Вперёд", callback_data=f"next_page_add_{page+1}"))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    # Кнопка Назад
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups"))

    return keyboard



