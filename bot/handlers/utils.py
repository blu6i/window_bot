from datetime import datetime

from utils import logger


async def remove_keyboard(bot, chat_id, message_id):
    """Удаляет сообщение с кнопками"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        # logger.info(f'Удалил клавиатуру')
    except Exception as e:
        logger.error(f'Ошибка при удалении сообщение с кнопками {e}')


def date_format_db(text: str) -> str:
    """Преобразование строки вида DD, DD.MM, DD.MM.YYYY в YYYY-MM-DD с учетом перехода на следующий месяц"""
    today = datetime.now()

    parts = list(map(int, text.split(".")))

    if len(parts) == 1:
        # Если только день указан
        day = parts[0]
        month = today.month
        year = today.year
        try:
            temp_date = datetime(year, month, day)
            if temp_date.date() < today.date():
                # День уже прошел в этом месяце -> следующий месяц
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
        except ValueError:
            # День не существует в этом месяце (например 31 февраля), пробуем следующий месяц
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
    elif len(parts) == 2:
        # День и месяц
        day, month = parts
        year = today.year
    else:
        # День, месяц и год
        day, month, year = parts

    date_obj = datetime(year, month, day)
    return date_obj.strftime("%Y-%m-%d")