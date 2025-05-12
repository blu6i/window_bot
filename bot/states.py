from aiogram.dispatcher.filters.state import State, StatesGroup


class MenuStates(StatesGroup):
    GROUP_EDIT = State()
    DATE_EDIT = State()
    LINK_MENU = State()
    TEACHER_EDIT = State()
    EDIT_WINDOW = State()
    EDIT_COMMENT = State()
    EDIT_AUDI = State()
    MY_MEET = State()
    EDIT_MEET = State()
    EDIT_MEET_DATETIME = State()
    EDIT_MEET_ROOM = State()
    EDIT_MEET_COMMENT = State()