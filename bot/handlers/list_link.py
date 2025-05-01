from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from bot import MenuStates, get_menu_link


async def show_links(call: types.CallbackQuery, state: FSMContext):
    """Показать меню ссылок"""
    await state.set_state(MenuStates.LINK_MENU.state)
    await call.message.edit_text("🔗 Меню ссылок:", reply_markup=get_menu_link())
    await call.answer()


def register_link_handlers(dp: Dispatcher):
    # Вывод меню со ссылками
    dp.register_callback_query_handler(show_links,
                                       lambda c: c.data == "menu_links",
                                       state="*")
