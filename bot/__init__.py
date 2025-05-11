from .keyboards import get_menu_link, get_main_menu, get_inline_key_list
from .states import MenuStates
from .handlers.list_help import register_help_handlers
from .handlers.search_window import register_search_handlers
from .handlers.list_link import register_link_handlers
from .handlers.add_groups import register_add_groups_handlers
from .handlers.list_groups import register_groups_handlers
from .handlers.list_date import register_date_handlers
from .handlers.common import register_common_handlers
from .handlers.list_teacher import register_teachers_handlers
from .handlers.add_teachers import register_add_teachers_handlers
from .handlers.autorization import register_authorization_handlers
from .handlers.search_window_teacher import register_windows_list_handlers
from .handlers.meet_teacher import register_link_handlers
