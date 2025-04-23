from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import MenuStates, get_main_menu, get_menu_link


async def show_schedule(message: types.Message):
    await message.answer(
        "📅 <b>Официальный бот с расписанием:</b>",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("Перейти в бот", url="https://t.me/Vyatsu_chatbot")
        ),
        parse_mode='HTML'
    )


async def show_attendance(message: types.Message):
    await message.answer(
        "📝 <b>Бот для отметки посещений:</b>",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("Перейти в бот", url="https://t.me/all_my_attendance_bot")
        ),
        parse_mode='HTML'
    )


async def personal_account(message: types.Message):
    await message.answer(
        "🔐 <b>Личный кабинет ВятГУ:</b>",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("Перейти в ЛК", url="https://new.vyatsu.ru/account/")
        ),
        parse_mode='HTML'
    )


async def show_links(message: types.Message, state: FSMContext):
    """Показать меню ссылок"""
    await state.set_state(MenuStates.LINK_MENU.state)
    await message.answer("🔗 Меню ссылок:", reply_markup=get_menu_link())


async def back_to_main(event, state: FSMContext):
    """Вернуться в главное меню (универсально для сообщения и callback)"""
    await state.finish()
    if isinstance(event, types.CallbackQuery):
        await event.message.answer("🔙 Возврат в главное меню", reply_markup=get_main_menu(event.from_user.id))
    else:
        await event.answer("🔙 Возврат в главное меню", reply_markup=get_main_menu(event.from_user.id))


def register_link_handlers(dp: Dispatcher):
    dp.register_message_handler(show_links, text="🔗 Ссылки быстрого доступа", state="*")
    dp.register_message_handler(back_to_main, text="🔙 Назад", state=MenuStates.LINK_MENU)

    dp.register_message_handler(show_schedule, text="📅 Расписание", state="*")
    dp.register_message_handler(show_attendance, text="📝 Отметка", state="*")
    dp.register_message_handler(personal_account, text="📌 Личный кабинет", state="*")
