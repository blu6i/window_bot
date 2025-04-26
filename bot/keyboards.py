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


def get_inline_key_list(items: list[str], data_type) -> InlineKeyboardMarkup:
    """Генерация инлайн-кнопок из списка значений и кнопки 'Назад'"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    for item in items:
        keyboard.insert(InlineKeyboardButton(text=item, callback_data=f'-{item}'))
    if len(items) > 2:
        keyboard.add(InlineKeyboardButton("🧹 Очистить всё", callback_data=f"clear_all_{data_type}"))
    return keyboard
