from parser import groups_web_parse, groups_pdf_parse, teacher_web_parse, teacher_excel_parse
from utils import logger, import_excel_subjects
import os
import pandas as pd
import sql
import sqlite3

LINK_TEACHER = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/teacher.html"
LINK = 'https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html'


def get_unique_subjects_from_csvs(folder_path: str, output_file: str = 'subjects.txt') -> None:
    """
    Обрабатывает все CSV файлы в папке, извлекает уникальные названия предметов
    и сохраняет их в текстовый файл.

    Args:
        folder_path: Путь к папке с CSV файлами
        output_file: Имя выходного файла (по умолчанию 'subjects.txt')
    """

    # Собираем все CSV файлы в папке
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

    unique_subjects = set()

    # Обрабатываем каждый CSV файл
    for csv_file in csv_files:
        file_path = os.path.join(folder_path, csv_file)
        try:
            # Читаем CSV файл
            df = pd.read_csv(file_path)
            unique_subjects.update(df['subject'].unique())
            for i in df['subject'].unique():
                if i == 'nan': print(file_path)

        except Exception as e:
            print(f'Ошибка при обработке файла {csv_file}: {str(e)}')
    sorted_unique_subjects = unique_subjects
    # Сохраняем результат в файл
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('INSERT INTO Subjects(SubjectName) VALUES\n')
        for subject in sorted_unique_subjects:
            f.write(f'(\'{subject}\'),\n')
    print(f'Уникальные предметы сохранены в файл {output_file}')


PATH_SUBJECTS = 'info_for_db/subjects.txt'
PATH_INST = 'info_for_db/institute.txt'
PATH_FAC = 'info_for_db/faculties.txt'
PATH_SPEC = 'info_for_db/spec.txt'
PATH_EXCEL = 'data'


def main():
    database = "window_bot.db"
    conn = sql.create_connection(database)

    if conn is not None:
        # Создание таблиц
        sql.build_sql(conn, path_subjects=PATH_SUBJECTS,
                      path_institutes=PATH_INST,
                      path_faculties=PATH_FAC,
                      path_spec=PATH_SPEC,
                      path_excel=PATH_EXCEL)

    '''groups = groups_web_parse(LINK)
    for group_data in groups:
        try:
            group = groups_pdf_parse(group_data)
            # file_name = f'data/{group_data['group']}.xlsx'
            # group.to_excel(file_name, index=False)
            # logger.info(f'Данные сохранены в {file_name}')
        except Exception as e:
            logger.info(f'Ошибка обработки {group_data['group']}\n{str(e)}')'''


if __name__ == '__main__':
    main()
