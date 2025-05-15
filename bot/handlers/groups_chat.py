from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import sql
from utils import logger


async def group_meet(msg: types.Message):
    """Вывод запланированных встреч"""
    try:
        chat_id = msg.chat.id
        group_id = sql.get_group_tg_id(chat_id)
        if not group_id:
            await msg.reply("❗️Чат не привязан к группе. Используйте команду !код [hash].")
            return

        dates = sql.get_meet_group(group_id)
        if not dates:
            await msg.reply("📭 Встреч не запланировано.")
            return

        keyboard = InlineKeyboardMarkup(row_width=1)
        for date in dates:
            keyboard.add(InlineKeyboardButton(text=date,
                                              callback_data=f"group_meetings:{date}"))
        await msg.reply("📅 Выберите дату:",
                        reply_markup=keyboard)
    except Exception as e:
        logger.warning(f'Проблема с выводом встреч в группе: {e}')


async def show_meetings_for_date(call: types.CallbackQuery):
    """Подробный вывод об встрече"""
    try:
        date = call.data.split(":")[1]
        chat_id = call.message.chat.id
        group_id = sql.get_group_tg_id(chat_id)

        meetings = sql.get_meet_date(group_id, date)
        if not meetings:
            await call.message.edit_text(f"🔎 Нет встреч на {date}.")
            return

        text = f"📆 Встречи на {date}:\n"
        for meet in meetings:
            time, comment, cabinet = meet
            text += f"🕒 {time}\n— Кабинет: {cabinet or '-'}\n— Комментарий: {comment or '-'}\n"

        await call.message.edit_text(text)
    except Exception as e:
        logger.warning(f'Проблема с подробным выводом об встрече: {e}')
    finally:
        await call.answer()


def register_groups_chat_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        show_meetings_for_date,
        lambda c: c.data.startswith("group_meetings:"),
        chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
        state="*"
    )
    dp.register_message_handler(
        group_meet,
        lambda m: m.text == "!встречи",
        chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
        state="*"
    )
