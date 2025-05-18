from datetime import datetime
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ChatType

import sql
from bot.keyboards import get_inline_key_list
from bot.states import MenuStates
from utils import logger


async def show_dates(event: Union[types.CallbackQuery, types.Message], state: FSMContext):
    """Вывод дат пользователя"""
    try:
        u_id = event.from_user.id
        u_dates = sql.get_user_dates(u_id)

        if not u_dates:
            text = ("📅 У вас пока нет добавленных дат.\n"
                    "\n"
                    "Введите дату формата: *DD*, *DD.\u200BMM* или *DD.MM.YYYY*\n"
                    "Например: `16.\u200B05`")
        else:
            text = ("📅 Ваши даты:\n"
                    "\n"
                    "Введите дату формата: *DD*, *DD.\u200BMM* или *DD.MM.YYYY*\n"
                    "Например: `16.\u200B05`")

        keyboard = get_inline_key_list(u_id, "date")

        if isinstance(event, types.CallbackQuery):
            sent = await event.message.edit_text(text,
                                                 reply_markup=keyboard,
                                                 parse_mode="Markdown")
            await event.answer()
        else:
            sent = await event.answer(text, reply_markup=keyboard)

        await state.update_data(last_msg=sent.message_id)
        await state.set_state(MenuStates.DATE_EDIT.state)
    except Exception as e:
        logger.warning(f'Ошибка при выводе меню с добавлением дат: {e}')
    finally:
        if isinstance(event, types.CallbackQuery):
            await event.answer()


async def add_date(msg: types.Message, state: FSMContext):
    """Добавление даты с проверкой наличия даты в расписании"""
    try:
        u_id = msg.from_user.id
        text = msg.text.strip()
        data = await state.get_data()
        last_msg_id = data.get('last_msg')
        # Преобразование в формат для БД
        try:
            date = date_format_db(text)
        except ValueError:
            await msg.answer("⚠️ Некорректный формат даты или такой даты не существует в календаре. "
                             "\n"
                             "\nФормат даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                             reply_markup=get_inline_key_list(u_id, "date")
                             )
            return
        except Exception:
            await msg.answer('⚠️ Некорректный формат даты',
                             reply_markup=get_inline_key_list(u_id, "date")
                             )
            return

        # Проверка: есть ли вообще такая дата в БД расписания
        if not sql.is_date_in_schedule(date):
            await msg.answer(f"⚠️ На {date} нет расписания.",
                             reply_markup=get_inline_key_list(u_id, "date")
                             )
            return

        u_id = msg.from_user.id
        u_dates = sql.get_user_dates(u_id)

        if date in u_dates:
            await msg.answer(f"⚠️ Дата {date} уже добавлена.",
                             reply_markup=get_inline_key_list(u_id, "date")
                             )
            return

        sql.add_user_date(u_id, date)
        await msg.answer(f"✅ Дата {date} добавлена.",
                         reply_markup=get_inline_key_list(u_id, "date")
                         )
        await state.update_data(last_msg=last_msg_id)
    except Exception as e:
        logger.warning(f'Ошибка при добавлении даты: {e}')


async def del_date(call: types.CallbackQuery):
    """Инлайн-кнопки для дат"""
    try:
        u_id = call.from_user.id
        data = call.data
        text = "📅 У вас пока нет добавленных дат."
        # Удаление
        if data.startswith("-"):
            date_str = data[1:]
            sql.remove_user_date(u_id, date_str)
            text = f"❌ Дата {date_str} удалена."

        # Очистка
        elif data == "clear_all_date":
            sql.remove_all_user_dates(u_id)
            text = "🧹 Все даты удалены."

        # Вывод
        u_dates = sql.get_user_dates(u_id)
        if not u_dates:
            await call.message.edit_text(f"{text}\n\nФормат для добавления дат: DD, DD.\u200BMM или DD.MM.YYYY",
                                         reply_markup=get_inline_key_list(u_id, "date"))
        else:
            await call.message.edit_reply_markup(reply_markup=get_inline_key_list(u_id, "date"))
    except Exception as e:
        logger.warning(f'Ошибка при удалении даты: {e}')
    finally:
        await call.answer()


async def refresh_dates_message(msg, state, user_id):
    """Обновить сообщение со списком дат"""
    try:
        u_dates = sql.get_user_dates(user_id)
        if not u_dates:
            sent = await msg.answer("📅 У вас пока нет добавленных дат.",
                                    reply_markup=get_inline_key_list(user_id, "date"))
        else:
            sent = await msg.answer("📅 Ваши даты:"
                                    "\n\nФормат ввода даты должен быть: DD, DD.\u200BMM или DD.MM.YYYY",
                                    reply_markup=get_inline_key_list(user_id, "date"))

        await state.update_data(last_dates_msg=sent.message_id)
    except Exception as e:
        logger.warning(f'Проблема при обновлении сообщения со списком дат: {e}')


def date_format_db(text: str) -> str:
    """Преобразование строки вида DD, DD.MM, DD.MM.YYYY в YYYY-MM-DD с учетом перехода на следующий месяц"""
    try:
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
    except Exception as e:
        logger.warning(f'Проблема при работе с форматированием даты: {e}')
        raise


def register_date_handlers(dp: Dispatcher):
    # Меню с датами
    dp.register_callback_query_handler(
        show_dates,
        lambda c: c.data == 'menu_dates' and c.message.chat.type == ChatType.PRIVATE,
        state="*"
    )
    dp.register_message_handler(
        show_dates,
        commands=['dates'],
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state="*"
    )
    # Добавление даты
    dp.register_message_handler(
        add_date,
        lambda m: not m.text.startswith('/'),
        chat_type=ChatType.PRIVATE,
        content_types=types.ContentTypes.TEXT,
        state=MenuStates.DATE_EDIT
    )
    # Удаление даты
    dp.register_callback_query_handler(
        del_date,
        lambda c: (c.data.startswith("-") or c.data == 'clear_all_date') and c.message.chat.type == ChatType.PRIVATE,
        state=MenuStates.DATE_EDIT
    )
