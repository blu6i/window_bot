from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatType
from random import choice

import sql
from bot.handlers.common import out_main_menu


async def send_test_auth_message(msg: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Группа для теста", url="https://t.me/+YgiaNeL19443MWNi")
    )
    kb.add(
        InlineKeyboardButton("Рандомный вход", callback_data="test_auth_random_login"),
        InlineKeyboardButton("Выйти", callback_data="test_auth_logout")
    )

    text = (
        "*Тестирование бота*\n"
        "\n"
        "Меню призвано для облегчения теста.\n"
        "- Вы можете посетить группу для тестирования уведомлений\n"
        "\n"
        "- Вы можете временно войти под случайным преподавателем, или выйти, если вы уже авторизованы."
    )

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


async def handle_random_login(call: types.CallbackQuery, state: FSMContext):
    u_id = call.from_user.id
    if sql.is_teacher_authorized(u_id):
        text = '❌ Вы уже авторизованы'
    else:
        # Получаем всех преподавателей без UserID
        conn = sql.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TeacherID, FullName FROM Teachers WHERE UserID IS NULL")
        available = cursor.fetchall()

        if not available:
            return

        selected = choice(available)
        teacher_id, full_name = selected

        # Привязываем Telegram UserID
        cursor.execute("UPDATE Teachers SET UserID = ? WHERE TeacherID = ?", (sql.get_user_id(u_id), teacher_id))
        conn.commit()

        await call.answer()
        text = f"✅ Вы вошли как преподаватель: *{full_name}*"
    await out_main_menu(call, state, text, is_new_msg=True)


async def handle_logout(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if not sql.is_teacher_authorized(user_id):
        text = '❌ Вы еще не авторизовались'
    else:
        conn = sql.get_connection()
        cursor = conn.cursor()
        # Отвязываем Telegram ID
        cursor.execute("UPDATE Teachers SET UserID = NULL WHERE UserID = ?", (sql.get_user_id(user_id),))
        conn.commit()

        await call.answer()
        text = "🚪 Вы вышли из системы преподавателя."
    await out_main_menu(call, state, text, is_new_msg=True)


async def user_joined(event: types.ChatMemberUpdated):
    chat_id = event.chat.id
    group_name = sql.get_group_name(sql.get_group_tg_id(chat_id))
    text = (
        f"Вы присоединились в тестовую группу\n"
        f"\n"
        f"Группа авторизована как: <code>{group_name}</code>\n"
        f"\n"
        f"Основная команда:\n"
        f"- !встречи – вывод встреч для текущей группы\n"
    )

    await event.bot.send_message(chat_id=chat_id, parse_mode="HTML", text=text)


def register_testing_handlers(dp: Dispatcher):
    dp.register_message_handler(
        user_joined,
        content_types=types.ContentType.NEW_CHAT_MEMBERS,
        chat_type=[ChatType.SUPERGROUP, ChatType.GROUP],
        state='*'
    )
    dp.register_callback_query_handler(
        handle_logout,
        lambda c: c.data == "test_auth_logout",
        chat_type=ChatType.PRIVATE,
        state='*'
    )
    dp.register_callback_query_handler(
        handle_random_login,
        lambda c: c.data == "test_auth_random_login",
        chat_type=ChatType.PRIVATE,
        state='*'
    )
