import os
import pandas as pd
from typing import List, Set


def get_unique_subjects_from_excel(folder_path: str,
                                   output_file: str = 'subjects.txt',
                                   subject_column: str = 'subject') -> None:
    """
    Обрабатывает все Excel файлы в папке, извлекает уникальные названия предметов
    и сохраняет их в текстовый файл в формате SQL-запросов.

    Args:
        folder_path: Путь к папке с Excel файлами
        output_file: Имя выходного файла (по умолчанию 'subjects.txt')
        subject_column: Название колонки с предметами (по умолчанию 'subject')
    """
    # Поддерживаемые форматы Excel
    excel_extensions = ('.xlsx', '.xls', '.xlsm', '.xlsb')

    # Собираем все Excel файлы в папке
    excel_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(excel_extensions)
    ]

    if not excel_files:
        print(f"В папке {folder_path} не найдено Excel файлов")
        return

    unique_subjects: Set[str] = set()
    error_files: List[str] = []

    # Обрабатываем каждый Excel файл
    for excel_file in excel_files:
        file_path = os.path.join(folder_path, excel_file)
        try:
            # Читаем Excel файл (все листы)
            xls = pd.ExcelFile(file_path)

            # Обрабатываем каждый лист в файле
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

                # Проверяем наличие колонки с предметами
                if subject_column in df.columns:
                    # Удаляем NaN значения и добавляем в множество
                    subjects = df[subject_column].dropna().astype(str).unique()
                    unique_subjects.update(subjects)

        except Exception as e:
            error_files.append(excel_file)
            print(f'Ошибка при обработке файла {excel_file}: {str(e)}')

    # Выводим список файлов с ошибками
    if error_files:
        print("\nФайлы с ошибками обработки:")
        for file in error_files:
            print(f"- {file}")

    # Сортируем предметы по алфавиту
    sorted_subjects = sorted(unique_subjects, key=lambda x: x.lower())

    # Сохраняем результат в файл
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, subject in enumerate(sorted_subjects):
            # Для последней записи убираем запятую
            f.write(f"{subject.strip()}\n")