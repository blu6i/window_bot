from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import sql


async def group_meet(message: types.Message):
    chat_id = message.chat.id
    group_id = sql.get_group_tg_id(chat_id)
    if not group_id:
        await message.reply("❗️Чат не привязан к группе. Используйте команду !код [hash].")
        return

    dates = sql.get_meet_group(group_id)
    if not dates:
        await message.reply("📭 Встреч не запланировано.")
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for date in dates:
        keyboard.add(InlineKeyboardButton(text=date, callback_data=f"group_meetings:{date}"))
    await message.reply("📅 Выберите дату:", reply_markup=keyboard)


async def show_meetings_for_date(callback: types.CallbackQuery):
    date = callback.data.split(":")[1]
    chat_id = callback.message.chat.id
    group_id = sql.get_group_tg_id(chat_id)

    meetings = sql.get_meet_date(group_id, date)
    if not meetings:
        await callback.message.edit_text(f"🔎 Нет встреч на {date}.")
        return

    text = f"📆 Встречи на {date}:\n"
    for meet in meetings:
        time, comment, cabinet = meet
        text += f"🕒 {time}\n— Кабинет: {cabinet or '-'}\n— Комментарий: {comment or '-'}\n"

    await callback.message.edit_text(text)


def register_groups_chat_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(show_meetings_for_date,
                                       lambda c: c.data.startswith("group_meetings:"),
                                       chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
                                       state="*")
    dp.register_message_handler(group_meet,
                                lambda m: m.text == "!встречи",
                                chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
                                state="*")
