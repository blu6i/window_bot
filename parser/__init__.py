from parser.student.web_parser import parse_schedule as groups_web_parse
from .teacher.web_parser_teacher import parse_schedule_teacher

# Импорт утилиты
from parser.utils.formating_str import format_class
from parser.utils.init_webdriver import init_driver