import re
import pdfplumber
import pandas as pd
import requests
from io import BytesIO

'''
| Parser PDF
| Файл загружается в временную память
| Программа открывает временный файл
| Программа считывает все таблицы из файла
| Программа удаляет первый столбец (Там день недели и дата)
| Программа преобразовывает таблицу в нужный вид (Дополняет днями, удаляет старую шапку)
| Программа копирует данные из таблицы в CSV (Временное решение)
'''


def clean_filename(filename):
    filename = filename.strip()  # Убираем лишние пробелы
    filename = re.sub(r'[\\/:*?"<>|]', '', filename)  # Удаляем запрещенные символы для имен файлов
    return filename


# Добавление дня в расписание
'''
| Следует также сделать добавление даты
| Скорее всего берем последние цифры в название файла
| Преобразуем в дни и с помощью библиотеки time преобразуем все в дни
'''


def add_day_of_week(df, time_column_index=0):
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_index = -1  # Начинаем с понедельника
    day_column = []  # Список для хранения дней недели

    for i in range(len(df)):
        current_time = df.iloc[i, time_column_index]  # Время из текущей строки
        # Если текущее время меньше предыдущего, начинается новый день
        if current_time == "08:20-09:50":
            day_index = (day_index + 1) % 7  # Переходим к следующему дню недели

        # Добавляем текущий день недели
        day_column.append(days_of_week[day_index])

    # Вставляем столбец "День недели" в нулевой индекс
    df.insert(0, "День недели", day_column)

    return df


def save_to_csv(df, csv_path):
    # Сохранение DataFrame в CSV-файл
    df.to_csv(csv_path, index=False, encoding='utf-8')


def pdf_to_csv(pdf_url: str, name_file: str):
    # Скачивание PDF в память
    try:
        response = requests.get(pdf_url, timeout=10)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
    except requests.RequestException as e:
        raise ValueError(f"Ошибка загрузки PDF: {str(e)}")

    # Извлечение таблиц
    with pdfplumber.open(pdf_file) as pdf:
        # Собираем все таблицы из всех страниц
        tables = []
        for page in pdf.pages:
            tables.extend(page.extract_tables())
        if not tables:
            raise ValueError("В PDF не найдено таблиц")

        # Все данные (пропускаем заголовки)
        data = []
        # Получаем кортеж таблиц и отслеживаем 0 индекс, чтобы пропустить заголовок
        for i, table in enumerate(tables):
            data.extend(table[1:] if i == 0 else table)

    # Создание таблицы
    custom_headers = ["День недели", "Время", "Пара"]
    df = pd.DataFrame(data, columns=custom_headers)

    # Удаляем первый столбец
    df = df.drop(columns=df.columns[[0]])

    # Обработка данных
    df = add_day_of_week(df)

    # Сохранение
    csv_filename = f"{name_file}.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8')

    print(f"Данные сохранены в {csv_filename}")


def main():
    test_pdf = 'test.pdf'
    pdf_to_csv(test_pdf, 'test')


if __name__ == "__main__":
    main()
