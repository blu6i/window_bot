import os

import pandas as pd


def get_unique_objects(folder_path: str, output_file: str = 'subjects.txt') -> None:
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