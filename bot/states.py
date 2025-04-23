from aiogram.dispatcher.filters.state import State, StatesGroup


class MenuStates(StatesGroup):
    GROUP_EDIT = State()
    DATE_EDIT = State()
    LINK_MENU = State()
