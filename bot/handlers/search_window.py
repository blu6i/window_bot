from typing import Union

from aiogram import Dispatcher, types
from aiogram.types import ChatType, InlineKeyboardMarkup, InlineKeyboardButton

import sql
from bot.handlers.common import generate_free_windows_multi, send_result_text
from utils import logger

# Предопределённые временные интервалы
PAIR_TIMES = [
    "08:20-09:50",
    "10:00-11:30",
    "11:45-13:15",
    "14:00-15:30",
    "15:45-17:15",
    "17:20-18:50",
    "18:55-20:25"
]


# =======[Вывод свободных окон для дефолт пользователя]=======
async def search_window_user_handler(event: Union[types.CallbackQuery, types.Message]):
    """Вывод окон для простых смертных"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    try:
        u_id = event.from_user.id
        dates = sql.get_user_dates(u_id)
        group_ids = sql.get_user_groups(u_id)
        teacher_ids = sql.get_user_teachers(u_id)
        # Проверка данных пользователя
        if not dates:
            await send_result_text(event,
                                   "⚠️ Вы не указали дату!",
                                   reply_markup=markup)
            return
        elif not group_ids:
            await send_result_text(event,
                                   "⚠️ Вы не указали группы!",
                                   reply_markup=markup)
            return

        # Генерация свободных окон
        free_windows = generate_free_windows_multi(group_ids, teacher_ids, dates)

        # Формируем текст результата
        if not free_windows:
            result_text = "❌ Свободных окон не найдено."
        else:
            result_lines = ["🪟 <b>Свободные окна:</b>"]
            for date, times in free_windows.items():
                result_lines.append(f"\n📅 <b>{date}</b>")
                for time in times:
                    result_lines.append(f"🕒 {time}")
            result_text = "\n".join(result_lines)

        # Отправка сообщения
        await send_result_text(event, result_text, reply_markup=markup)

    except Exception as e:
        logger.warning(f"Произошла ошибка при выводе окон обычному пользователю: {e}")


def register_search_handlers(dp: Dispatcher):
    # Вывод окон
    dp.register_callback_query_handler(
        search_window_user_handler,
        lambda c: c.data == "menu_windows" and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_message_handler(
        search_window_user_handler,
        chat_type=ChatType.PRIVATE,
        commands=["windows"],
        state="*"
    )
