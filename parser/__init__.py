from parser.student.pdf_parser import parser_pdf as groups_pdf_parse
from parser.student.web_parser import parse_schedule as groups_web_parse

from parser.teacher.excel_parser import parse_schedule_table as teacher_excel_parse
from parser.teacher.web_parser_teacher import parse_schedule_teacher as teacher_web_parse

# Импорт утилиты
from parser.utils.formating_str import format_class
from parser.utils.init_webdriver import init_driver