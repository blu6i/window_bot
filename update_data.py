import sql
from parser import groups_web_parse, groups_pdf_parse
from utils import logger

# LINK_TEACHER = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/teacher.html"
LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'


def update_schedule():
    groups = groups_web_parse(LINK)
    for group_data in groups:
        try:
            group = groups_pdf_parse(group_data)
            file_name = f'data/{group_data["group"]}.xlsx'
            group.to_excel(file_name, index=False)
            logger.info(f'Данные сохранены в {file_name}')
        except Exception as e:
            logger.info(f'Ошибка обработки {group_data["group"]}\n{str(e)}')


PATH_SUBJECTS = 'info_for_db/subjects.txt'
PATH_INST = 'info_for_db/institute.txt'
PATH_FAC = 'info_for_db/faculties.txt'
PATH_SPEC = 'info_for_db/spec.txt'
PATH_EXCEL = 'data'


def main():
    # Парсинг расписания студентов
    update_schedule()

    # Работа с БД
    try:
        database = "db/data-groups.db"
        conn = sql.create_connection(database)
        if conn is not None:
            # Создание таблиц
            sql.build_sql(conn,
                          path_institutes=PATH_INST,
                          path_faculties=PATH_FAC,
                          path_spec=PATH_SPEC,
                          path_excel=PATH_EXCEL)
        else:
            logger.warning('Таблицы нет')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
